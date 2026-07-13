# Contributing to Caliber

Caliber grades autonomous hard-science research agents on three axes (correctness gate ×
pass^k reliability × cost per correct solution). **Public methodology, private answers:**
task prompts and reporting keys are public (`benchmark/suite/<name>/MANIFEST.json`); the
sealed reference values, tolerances, and grading keys live in a separate private store and
are never committed here.

## Table of contents
- [Development setup](#development-setup)
- [Repo layout](#repo-layout)
- [Proposing a task](#proposing-a-task)
- [Task design principles](#task-design-principles)
- [Contributing a harness](#contributing-a-harness)
- [Testing your changes](#testing-your-changes)
- [Hygiene rules](#hygiene-rules)

---

## Development setup

```bash
git clone https://github.com/fl-sean03/caliber.git
cd caliber
pip install pytest requests

# Verify the scoring engine
python -m pytest benchmark/scoring -q
```

That is the whole footprint for benchmark development. Running actual research tasks
additionally requires the compute stack the task specifies (LAMMPS, Quantum ESPRESSO,
ML interatomic potentials) — each task's environment contract states what it needs.

## Repo layout

| Path | Purpose | When to edit |
|------|---------|--------------|
| `benchmark/METHODOLOGY.md` | Three axes, oracle-escrow grading, difficulty horizon, release gate | Changing how grading is defined |
| `benchmark/suite/<name>/MANIFEST.json` | Public task manifests (prompts + reporting keys, no answers) | Proposing tasks |
| `benchmark/suite/` tooling | Sweep runner, run audit, trajectory audit | Improving measurement/audit machinery |
| `benchmark/scoring/` | Mechanical anchors ⊕ frozen judge, evidence store, provenance graph | Changing scoring |
| `benchmark/harnesses/<name>/` | Per-model native runners | Adding a model/vendor harness |

Sealed answer keys live **outside** this repo (private store), injected only at grade time.

## Proposing a task

Open an issue with:

- the **physical quantity** (or bounded-discovery objective) to be graded,
- the difficulty **horizon** it targets (H1 trivial → H6+ frontier reproduction/discovery;
  see `benchmark/METHODOLOGY.md`),
- the **reporting keys** the agent must surface, and
- how **ground truth** is obtained — the grader computes a high-compute reference
  (oracle-escrow), never the agent's own numbers and never an unverified literature value.

Accepted tasks are sealed by a maintainer: the prompt + keys land in a public MANIFEST; the
answer and tolerance go to the private store. Every candidate is screened against a frontier
panel at maximum effort before it can enter the suite — tasks the panel aces are discarded.

## Task design principles

1. **One horizon, cleanly.** A task's difficulty comes from its coupled-stage count, not
   from combining unrelated physics.
2. **Oracle-gradeable.** There must be a defensible high-compute reference and a tolerance
   set to that reference's own uncertainty (never a global epsilon).
3. **Grade observable outcomes, not methods.** Multiple valid approaches should pass.
4. **Contamination-aware.** Prefer parameterized families instantiated fresh per instance;
   never leak the answer through the prompt, reporting keys, or provided files.
5. **Sealable environment.** State what lookups are blocked (the exact target quantity) so
   the trajectory audit has a contract to enforce.

## Contributing a harness

Each model is benchmarked through its **own native harness** (no custom orchestration in the
measurement path). To add one:

- add `benchmark/harnesses/<name>/` with the runner and a `RUNNER.md` describing the exact
  invocation;
- every run must record `harness:{name,version,config_hash}` provenance and capture the full
  trajectory (tool calls, per-turn cost);
- smoke-verify the adapter end-to-end before opening the PR.

## Testing your changes

```bash
# scoring / evidence / provenance tests
python -m pytest benchmark/scoring -q

# trajectory-audit tests
python -m pytest benchmark/suite -q

# sweep a model across the benchmark on its native harness
python benchmark/suite/native_sweep.py --reps 3 --lanes 3

# audit a completed run (wake pattern, cost anatomy, artifact integrity)
python benchmark/suite/native_audit.py <run_dir> --brief
```

Before submitting a PR: run the tests, update `ROADMAP.md` if you completed a roadmap item,
and check the hygiene rules below.

## Hygiene rules

- **No sealed content.** Answers, tolerances, canary tokens, and oracle data never enter
  this repo — not in code, tests, fixtures, or issue text.
- **No secrets.** API keys and credentials stay out; CI scans for key-shaped strings.
- **No machine-specific paths.** Use environment variables or relative paths.
- **Full provenance.** Anything presented as a result must be traceable to the run that
  produced it.

## Questions?

See `ROADMAP.md` for what we're building toward, or open an issue.

Welcome to the project!
