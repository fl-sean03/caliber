# Smoke task — the stranger test

**Purpose.** The release gate for this environment is: *a fresh machine, operated by
someone who is not us, reproduces one full benchmark task run + grade from the public
docs alone.* This document is that end-to-end protocol, written against the actual
harness entry points (`benchmark/harnesses/native-claude/asw_native.py`,
`benchmark/suite/grade_fable5.py`) — only paths are adjusted to the container's
conventions.

Because the real Caliber tasks are graded against **sealed keys** that live off-repo
(public methodology, private answers), the stranger test uses a self-contained smoke
task (`SMOKE-C-000`, Si lattice constant + bulk modulus) with a **public** key in the
same file format. It exercises every layer the real benchmark uses — container, QE,
the session-holder harness, the transcript/evidence contract, mechanical anchors, and
the frozen judge — without touching sealed content.

---

## 0. Prerequisites (host machine)

| Requirement | Why |
|-------------|-----|
| Docker with BuildKit | multi-stage build; unreferenced stages skipped |
| ~40 GB free disk, ~1 h build wall | QE + LAMMPS compile from source |
| NVIDIA GPU + `nvidia-container-toolkit`, driver supporting CUDA 12.8 | LAMMPS GPU + MLIP inference (CPU-only fallback: skip `--gpus`; the smoke task's QE path is CPU) |
| `ANTHROPIC_API_KEY` | the Claude Code CLI inside the container (agent under test) |
| `OPENAI_API_KEY` | the frozen judge (`gpt-5.5-2026-04-23`) at grade time |

**Secrets are injected as environment variables at `docker run`, never baked into the
image or written into any repo file.** The judge client also accepts an off-repo key
file (`~/.config/asw/openai_judge.key`, perms 600) if you prefer a mounted secret file
over an env var.

## 1. Build the container

From the repository root:

```bash
docker build -f benchmark/environment/Dockerfile -t caliber:v0 .
# non-Blackwell GPU (e.g. A100):
#   docker build --build-arg GPU_ARCH=sm_80 -f benchmark/environment/Dockerfile -t caliber:v0 .
```

Sanity-check the toolchain (each command must show the pinned version from
[`TOOLCHAIN.md`](TOOLCHAIN.md)):

```bash
docker run --rm caliber:v0 bash -lc '
  echo | pw.x 2>/dev/null | grep -m1 "Program PWSCF"        # PWSCF v.7.5
  lmp -h | head -2                                          # 22 Jul 2025 - Update 4
  lmp -h | grep -A2 "Installed packages"                    # GPU KSPACE MANYBODY MOLECULE RIGID
  python --version                                          # Python 3.11.x
  python -c "import ase, pymatgen, torch; print(ase.__version__, torch.__version__)"
  xtb --version | head -1
  python -m pytest /opt/caliber/benchmark/scoring -q        # scoring self-tests green
'
```

## 2. Prepare the smoke task (host side)

The grading script (`grade_fable5.py`) reads runs and keys from the private-root
layout given by the `CALIBER_PRIVATE` env var (default `~/.caliber-private`). Create a
local stand-in and mount it — this is exactly how sealed grading works, with a public
key substituted:

```bash
mkdir -p smoke-private/tasks/bandC smoke-private/keys/bandC \
         smoke-private/pilot-loop/native-smoke/SMOKE-C-000/rep1/ws
```

`smoke-private/tasks/bandC/SMOKE-C-000.json`:

```json
{
  "id": "SMOKE-C-000",
  "band": "C",
  "prompt": "Determine the equilibrium lattice constant and bulk modulus of diamond-cubic SILICON from first principles (DFT-PBE), with a converged plane-wave setup and an equation-of-state fit. Report both values.",
  "reporting_keys": ["a0_si_angstrom", "B0_si_gpa"],
  "compute_budget": {"spend_ceiling_usd": 15.0},
  "version": "smoke-1-0"
}
```

`smoke-private/keys/bandC/SMOKE-C-000.json` (public key — DFT-PBE for Si is
textbook: a0 ≈ 5.47 Å, B0 ≈ 83–89 GPa):

```json
{
  "anchors": [
    {"name": "a0_si_angstrom", "lo": 5.40, "hi": 5.52, "weight": 1.0, "unit": "angstrom"},
    {"name": "B0_si_gpa",      "lo": 75.0, "hi": 100.0, "weight": 1.0, "unit": "GPa"}
  ],
  "pass_policy": {"pass_mechanical_min": 1.0, "pass_judge_min": 0.6},
  "judge_rubric": {"criteria": [
    {"name": "convergence_evidence", "description": "Cutoff and k-mesh convergence are demonstrated, not asserted."},
    {"name": "method_provenance", "description": "Pseudopotential and EOS fit are identified with sources."}
  ]}
}
```

`smoke-private/pilot-loop/native-smoke/SMOKE-C-000/rep1/goal.txt` — the goal is the
task prompt wrapped in the same operating contract the sweep driver
(`benchmark/suite/native_sweep.py`) generates, with container paths:

```text
You are an autonomous computational-materials researcher inside a container
(QE 7.5 at $QE_CPU, LAMMPS at $LMP, python env `science-tools` on PATH with
ASE/pymatgen/MACE/CHGNet/M3GNet). You run in a PERSISTENT Claude Code session:
for any compute expected to take more than ~2 minutes, launch it with the Bash
tool's run_in_background option and END YOUR TURN — the harness wakes you
automatically when the job completes; then harvest and continue. Never
busy-wait, poll, or sleep in the foreground for long jobs.

WORKSPACE (absolute; read/write ALL artifacts here): /workspace/SMOKE-C-000/rep1/ws

Maintain /workspace/SMOKE-C-000/rep1/ws/WORKFLOW.md as durable state (method
chosen, jobs launched with handles and expected outputs, what is harvested,
what remains). Update it as you go.

## Commission
Determine the equilibrium lattice constant and bulk modulus of diamond-cubic
SILICON from first principles (DFT-PBE), with a converged plane-wave setup and
an equation-of-state fit. Report both values.

## Completion (do these as the LAST steps, only when the ENTIRE commission is
complete and verified)
1. Write /workspace/SMOKE-C-000/rep1/ws/report.md (method + justification,
   values with uncertainty, convergence evidence, provenance/citations,
   limitations).
2. Write /workspace/SMOKE-C-000/rep1/ws/reported_values.json =
   {"reported_values": {...}} — one numeric entry per requested key.
   Required keys: a0_si_angstrom, B0_si_gpa.
3. Run: touch /workspace/SMOKE-C-000/rep1/ws/TASK_DONE
Do the real computation — do not guess.
```

## 3. Run the task (the agent under test)

Launch the container with the smoke tree mounted at the private-root path the
tooling expects, and `/workspace` bound to the run directory so the transcript and
artifacts land where the grader will read them:

```bash
docker run --rm --gpus all \
  -e ANTHROPIC_API_KEY \
  -e CALIBER_PRIVATE=/home/caliber/.caliber-private \
  -v "$PWD/smoke-private:/home/caliber/.caliber-private" \
  -v "$PWD/smoke-private/pilot-loop/native-smoke/SMOKE-C-000/rep1:/workspace/SMOKE-C-000/rep1" \
  caliber:v0 \
  python3 /opt/caliber/benchmark/harnesses/native-claude/asw_native.py \
    --goal-file /workspace/SMOKE-C-000/rep1/goal.txt \
    --workspace /workspace/SMOKE-C-000/rep1/ws \
    --worker-cwd /workspace/SMOKE-C-000/rep1/ws \
    --model claude-fable-5 \
    --max-wall-s 7200
```

Notes on what's real here:

- `asw_native.py` holds ONE `claude -p --input-format stream-json` session with stdin
  open; background-job completion re-wakes the agent natively. The full event stream
  is captured to `ws/loop_transcript.jsonl` (the evidence contract the grader reads).
- `--config-dir` (an account pin used on the reference machine) is omitted — the CLI
  authenticates from `ANTHROPIC_API_KEY`.
- The run ends when the agent writes `ws/TASK_DONE`, or at the wall cap. The runner
  prints a JSON outcome record (`status`, `wakes`, `wall_s`, `total_cost_usd`) to
  stdout.
- The run tree deliberately sits under `pilot-loop/native-smoke/...`: the grader's
  cost accounting branches on `native` appearing in the workspace path (cumulative
  per-process cost vs per-tick summing — see `harnesses/native-claude/RUNNER.md`).
- Expected agent wall for this smoke: minutes-scale QE (a small EOS scan), well under
  the 2 h cap.

## 4. Grade the run

```bash
docker run --rm \
  -e OPENAI_API_KEY \
  -e CALIBER_PRIVATE=/home/caliber/.caliber-private \
  -v "$PWD/smoke-private:/home/caliber/.caliber-private" \
  caliber:v0 \
  python3 /opt/caliber/benchmark/suite/grade_fable5.py SMOKE-C-000 \
    --rep 1 --tree native-smoke
```

This harvests `ws/loop_transcript.jsonl` + `ws/reported_values.json` + `ws/report.md`,
checks the mechanical anchors from the key (conjunctive — every anchor must land),
calls the frozen judge on the rubric (process floor only; the judge can never
overturn a failed anchor), and writes `rep1/score.json`.

**Pass criteria for the stranger test:**

```
verdict = PASS, anchors_passed = 2/2, judge_score >= 0.6
```

plus a non-empty `loop_transcript.jsonl` and a `cost_usd` that is plausible
(single-digit dollars) — a zero cost means the transcript wasn't captured.

## 5. What this proves / doesn't prove

**Proves:** the container's engines produce correct physics; the native harness's
launch→yield→wake→harvest loop works outside the reference machine; the
transcript→anchors→judge grading path runs end-to-end from public materials.

**Doesn't prove:** sealed-task grading logistics (key escrow / grade-service),
multi-rep sweeps (`native_sweep.py` currently reads goals from the private root —
see GAPS.md G4), non-Claude harnesses, or cloud-image deployment. Those are tracked
in [`GAPS.md`](GAPS.md).
