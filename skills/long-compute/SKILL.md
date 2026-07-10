---
name: long-compute
description: Run compute jobs (QE DFT, LAMMPS/MD, MLIP) that may outlive a single agent turn, without parking-and-dying. Use whenever a task launches work that could take more than a few minutes — decide block-vs-detach, detach long jobs durably, keep state in files, and let the asw-loop supervisor re-invoke you across ticks. Read BEFORE launching any simulation whose runtime you are unsure of.
---

# long-compute — durable execution across agent ticks

You may be running under the **asw-loop supervisor**: a fresh copy of you is
re-invoked on a cadence until you write the completion sentinel. **Your context
does not persist between ticks — the workspace files do.** Never assume you can
"wait" inside one turn for a long job; a headless turn ends the moment you yield.

## The one decision: BLOCK or DETACH

Estimate the job's wall time first (smoke it, or reason from size).

- **Short / medium (≲ ~10 min, fits one turn):** **BLOCK.** Launch with the
  Bash tool's `run_in_background`, then poll its output to completion *within
  this turn* and report. Do NOT park. Example: an MLIP relax, a small SCF.
- **Long (minutes→days, exceeds a turn):** **DETACH + record + yield.** Launch
  so the job survives your turn ending, record its handle, then STOP — the loop
  re-invokes you to harvest.

If unsure, smoke a tiny version first (compute-validation), then decide.

## Detach recipe (long jobs)

Launch truly detached so the OS does not reap it when your turn ends (the Bash
`run_in_background` child IS reaped — do not rely on it for long jobs):

```bash
# local (RTX 5080): setsid + nohup, own workdir, atomic sentinels
mkdir -p runs/jobA
setsid nohup bash -c '
  cd runs/jobA
  <your compute, e.g. mpirun pw.x -in in.scf > scf.out 2>&1>
  echo $? > exit.rc            # atomic-ish; write LAST
  touch DONE
' >/dev/null 2>&1 &
echo "jobA pid=$! workdir=runs/jobA" >> WORKFLOW.md
```

- **HPC:** `sbatch --parsable job.sh` → record the returned job id; poll with
  `squeue -j <id>` then `sacct -j <id>`; harvest on COMPLETED.
- **Cloud (Modal):** dispatch → record the call id; poll `.list()`/status.

Record in `WORKFLOW.md` (durable state — the loop and future-you read it):
`{stage, backend, handle (pid/jobid/callid), workdir, expected_output, state}`.

## The tick contract (how each re-invocation behaves)

1. Read `WORKFLOW.md` / your progress notes — what did prior-you launch?
2. For each non-terminal job, check its **sentinel** (`DONE` + `exit.rc`) or
   poll the scheduler by handle. **A "running" mark is NEVER "done"** — verify
   against the artifact, not your memory.
3. If a job finished: verify output completeness, harvest, update WORKFLOW.md.
4. If all work is complete: write your final results, then create the
   completion sentinel **as the last step**: `touch TASK_DONE` (the loop stops
   when it appears). For benchmark tasks also write `reported_values.json`.
5. If work is still running: append a one-line status to WORKFLOW.md and STOP.
   Do not block waiting — yield; the loop re-invokes you next tick.

## Rules

- **Idempotent:** before launching, check WORKFLOW.md — never double-submit a
  job you already launched (crash-safe re-entry).
- **Harvest by pull:** the job writes results to its own workdir; you read them
  on a later tick. Never require the compute to reach back to you.
- **Distinguish failure types:** science failure (bad output) vs infra failure
  (scheduler/SSH/OOM) — the latter is retryable/void, not a capability failure.
- **Clean up:** on giving up a job, kill it (by the recorded pid/handle), don't
  leave orphans.
- **Budget:** respect the task's spend/wall ceiling; record cost as you go.

## Record provenance as you compute (verification substrate)

When you launch a real computation and when you harvest a result, record it in the
campaign provenance graph so every reported value can be walked back to the exact
inputs that produced it. Use the `asw-graph` CLI (append-only `graph.jsonl` in your
workspace — cheap, plain JSON):

```bash
G=$WS/graph.jsonl
# when you run a job: register its input(s) and the run
IN=$(asw-graph --graph $G artifact runs/jobA/espresso.pwi --role input)
RUN=$(asw-graph --graph $G run --tool quantum-espresso --label jobA --used $IN)
# when it finishes: register the output as generated-by that run
OUT=$(asw-graph --graph $G artifact runs/jobA/espresso.pwo --role output)
asw-graph --graph $G edge $OUT prov:wasGeneratedBy $RUN
# when you report a value: make it a Claim derived from the runs/outputs
asw-graph --graph $G claim --key pt_GPa --value 9.7 --units GPa \
  --derived-from $RUN $OUT --method "Birch-Murnaghan EOS"
```

`asw-graph` = `python <harness>/asw_graph.py`. This is best-effort but valuable: even
just registering inputs+outputs+claims makes the campaign auditable. If you skip it,
the grader reconstructs an artifact-level graph from your `runs/` files at grade time —
but recording as you go captures the decision chain, which cannot be backfilled.

This skill is harness-neutral: the tick contract is the same whether the
supervisor is `asw-loop` (`claude -p --resume`), `/loop`, or ScheduleWakeup.
