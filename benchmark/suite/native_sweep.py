#!/usr/bin/env python3
"""
native_sweep.py — Fable-5 full re-sweep on the NATIVE session-holder runner
(asw_native.py). All 17 tasks (Band-C 9 + Band-B 8) x k reps, clean tree,
capped concurrency (calibration policy: contention pollutes cost/wall).

- Goals are built from the sealed task JSONs with the NATIVE preamble
  (persistent session + background-wake contract), not the tick-loop preamble.
- Band-C goals name the exact reporting_keys from the task spec; Band-B goals
  ask for self-descriptive keys (anchor names are sealed — they leak answers).
- Account = fleet-active (~/.agents/accounts/.active) read AT EACH SPAWN
  (owner rule 2026-07-10: deploys follow the fleet).
- No spend ceilings (owner rule: record actual cost, never cap mid-science).
- rate_limited runs are requeued (max 3 attempts).

Usage: python3 native_sweep.py [--reps 3] [--lanes 3] [--tree native-fable5]
                               [--tasks BENCH-C-009,...] [--dry]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HARNESS = Path(__file__).resolve().parents[1] / "harnesses" / "native-claude"
# Private store (sealed tasks/keys) — override with CALIBER_PRIVATE.
PRIVATE = Path(os.environ.get("CALIBER_PRIVATE", str(Path.home() / ".caliber-private")))
ACTIVE = Path.home() / ".agents" / "accounts" / ".active"

# Fallback per-run wall when neither --max-wall-s nor the task manifest says
# otherwise. Long-horizon tasks declare their own wall via wall_clock_h in the
# manifest (30–96 h); a single global 6 h wall would DNF every honest run.
DEFAULT_WALL_S = 21600

# hardest-first (old-loop wall/cost ordering), then Band-B
ORDER = ["BENCH-C-009", "BENCH-C-005", "BENCH-C-002", "BENCH-C-007",
         "BENCH-C-006", "BENCH-C-008", "BENCH-C-001", "BENCH-C-003",
         "BENCH-C-004",
         "BENCH-B-004", "BENCH-B-003", "BENCH-B-006", "BENCH-B-002",
         "BENCH-B-005", "BENCH-B-007", "BENCH-B-001", "BENCH-B-008"]

PREAMBLE = """You are an autonomous computational-materials researcher on this workstation \
(RTX 5080, 24 cores, 30G RAM — a SHARED machine; nice long CPU jobs, never pkill by \
process name). You run in a PERSISTENT Claude Code session: for any compute expected \
to take more than ~2 minutes, launch it with the Bash tool's run_in_background option \
and END YOUR TURN — the harness wakes you automatically when the job completes; then \
harvest and continue. Never busy-wait, poll, or sleep in the foreground for long jobs.

WORKSPACE (absolute; read/write ALL artifacts here): {ws}

Maintain {ws}/WORKFLOW.md as durable state (method chosen, jobs launched with handles \
and expected outputs, what is harvested, what remains). Update it as you go.

## Commission
{prompt}

## Operating environment
- Activate env first: `source ~/miniconda3/etc/profile.d/conda.sh && conda activate science-tools` (ASE, pymatgen, MACE-MP-0/CHGNet/M3GNet on GPU).
- Local QE: $QE_CPU / $QE_GPU (quantum-espresso skill; do not mpirun the GPU build). LAMMPS: $LMP. MLIP is often the pragmatic route — your call to justify.
- No spend ceiling is enforced, but be cost-conscious: choose the CHEAPEST method adequate for the accuracy the commission requires, and record actual cost/wall honestly in WORKFLOW.md.

## Completion (do these as the LAST steps, only when the ENTIRE commission is complete and verified)
1. Write {ws}/report.md (method + justification, values with uncertainty, convergence evidence, provenance/citations, limitations).
2. Write {ws}/reported_values.json = {{"reported_values": {{...}}}} — {reporting_clause}
3. Run: touch {ws}/TASK_DONE
Do the real computation — do not guess."""

CLAUSE_C = ("one numeric entry per requested key; omit a key ONLY if genuinely "
            "undeterminable. Required keys: {keys}.")
CLAUSE_B = ("a flat map surfacing EVERY load-bearing quantitative result you report, "
            "with clear self-descriptive snake_case keys including units (e.g. "
            "\"Ef_vacancy_eV\": 0.66). State sign conventions explicitly where signs matter.")


def build_goal(task: dict, ws: Path) -> str:
    if task["band"] == "C":
        keys = ", ".join(task.get("reporting_keys") or [])
        clause = CLAUSE_C.format(keys=keys)
    else:
        clause = CLAUSE_B
    return PREAMBLE.format(ws=ws, prompt=task["prompt"], reporting_clause=clause)


def load_task(task_id: str) -> dict:
    band = "bandC" if "-C-" in task_id else "bandB"
    return json.loads((PRIVATE / "tasks" / band / f"{task_id}.json").read_text())


def manifest_wall_h(task: dict) -> tuple[float | None, str]:
    """Extract wall_clock_h from a task manifest, tolerating shape drift.

    Canonical home (all Caliber-1 task manifests, verified 2026-07-15) is
    environment_contract.wall_clock_h; top-level and budget-nested spellings
    are also accepted. Returns (hours, dotted_path) on success,
    (None, dotted_path) when the field exists but is unusable, and
    (None, "") when absent. First match in canonical-first order wins.
    """
    ec = task.get("environment_contract")
    ec = ec if isinstance(ec, dict) else {}
    ec_budget = ec.get("budget")
    budget = task.get("budget")
    spots = [
        ("environment_contract.wall_clock_h", ec),
        ("wall_clock_h", task),
        ("environment_contract.budget.wall_clock_h",
         ec_budget if isinstance(ec_budget, dict) else {}),
        ("budget.wall_clock_h", budget if isinstance(budget, dict) else {}),
    ]
    for path, holder in spots:
        if "wall_clock_h" not in holder:
            continue
        try:
            hours = float(holder["wall_clock_h"])
        except (TypeError, ValueError):
            hours = float("nan")
        if hours > 0:  # NaN and non-positive both fail this
            return hours, path
        return None, path
    return None, ""


def resolve_wall_s(cli_wall_s: int | None, task: dict) -> tuple[int, str]:
    """Per-run wall in seconds + one-line reason.

    Precedence: explicit --max-wall-s > manifest wall_clock_h*3600 >
    DEFAULT_WALL_S (warn-and-default on missing/unparseable manifest field).
    """
    if cli_wall_s is not None:
        return int(cli_wall_s), "cli --max-wall-s"
    hours, path = manifest_wall_h(task)
    if hours is not None:
        return int(round(hours * 3600)), f"manifest {path}={hours:g}h"
    if path:
        return DEFAULT_WALL_S, f"default {DEFAULT_WALL_S}s (unparseable manifest {path})"
    return DEFAULT_WALL_S, f"default {DEFAULT_WALL_S}s (no wall_clock_h in manifest)"


def active_config_dir() -> str:
    acct = ACTIVE.read_text().strip() if ACTIVE.exists() else ""
    return str(Path.home() / ".agents" / "accounts" / acct) if acct else str(Path.home() / ".claude")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--lanes", type=int, default=3)
    ap.add_argument("--tree", default="native-fable5")
    ap.add_argument("--model", default="claude-fable-5")
    ap.add_argument("--tasks", default=None, help="comma list; default all 17")
    ap.add_argument("--max-wall-s", type=int, default=None,
                    help="override per-run wall (s); default: task manifest "
                         f"wall_clock_h*3600, else {DEFAULT_WALL_S}")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    tasks = a.tasks.split(",") if a.tasks else ORDER
    root = PRIVATE / "pilot-loop" / a.tree
    root.mkdir(parents=True, exist_ok=True)
    log = (root / "sweep.log").open("a") if not a.dry else sys.stdout
    status_f = root / "SWEEP_STATUS.json"

    # rep-major queue: every task at rep1, then rep2, ...
    queue = [(t, r, 1) for r in range(1, a.reps + 1) for t in tasks]
    running: list[tuple] = []   # (proc, task, rep, attempt, t0)
    done, failed = [], []

    def snapshot():
        status_f.parent.mkdir(parents=True, exist_ok=True)
        status_f.write_text(json.dumps({
            "queued": [(t, r) for t, r, _ in queue],
            "running": [(t, r) for _, t, r, _, _ in running],
            "done": done, "failed": failed, "ts": time.time()}, indent=1))

    if a.dry:
        for t, r, _ in queue:
            print("would run:", t, "rep", r)
        return 0

    while queue or running:
        # reap
        for item in running[:]:
            proc, t, r, att, t0 = item
            if proc.poll() is None:
                continue
            running.remove(item)
            out = (proc.stdout.read() or "").strip().splitlines()
            rec = {}
            for ln in reversed(out):
                try:
                    rec = json.loads(ln)
                    break
                except (json.JSONDecodeError, ValueError):
                    continue
            rec.update({"task": t, "rep": r, "attempt": att,
                        "lane_wall_s": round(time.monotonic() - t0, 1)})
            print(json.dumps(rec), file=log, flush=True)
            if rec.get("status") == "done":
                done.append((t, r))
            elif rec.get("status") == "rate_limited" and att < 3:
                queue.append((t, r, att + 1))
            else:
                failed.append((t, r, rec.get("status")))
        # launch
        while queue and len(running) < a.lanes:
            t, r, att = queue.pop(0)
            task = load_task(t)
            rep_dir = root / t / f"rep{r}"
            ws = rep_dir / "ws"
            ws.mkdir(parents=True, exist_ok=True)
            goal_f = rep_dir / "goal.txt"
            goal_f.write_text(build_goal(task, ws))
            cfg = active_config_dir()
            wall_s, wall_why = resolve_wall_s(a.max_wall_s, task)
            proc = subprocess.Popen(
                [sys.executable, str(HARNESS / "asw_native.py"),
                 "--goal-file", str(goal_f), "--workspace", str(ws),
                 "--model", a.model, "--config-dir", cfg,
                 "--max-wall-s", str(wall_s)],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            running.append((proc, t, r, att, time.monotonic()))
            print(json.dumps({"event": "launch", "task": t, "rep": r,
                              "attempt": att, "config_dir": cfg,
                              "max_wall_s": wall_s, "wall_source": wall_why}),
                  file=log, flush=True)
        snapshot()
        time.sleep(10)

    snapshot()
    print(json.dumps({"event": "sweep_complete", "done": len(done),
                      "failed": failed}), file=log, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
