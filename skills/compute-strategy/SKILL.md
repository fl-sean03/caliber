---
name: compute-strategy
description: Decide where and how to run compute jobs across available backends (HPC, cloud GPUs, local). Use when starting any compute-intensive task, choosing a backend or partition, deciding job parameters (walltime, GPU type, parallelism), or debugging compute infrastructure issues. Embeds the smoke-first iteration pattern — validate cheaply before scaling.
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
---

# Compute Strategy — backend selection and iteration discipline

You are about to run a compute job. Before submitting **anything**, walk this skill.

This skill answers three questions for any compute-bearing task:

1. **Which backend?** HPC, cloud (Vast.ai/etc.), or local?
2. **Within that backend, which partition / queue / instance?** Testing, production, long-running?
3. **What's the iteration loop?** How do you avoid wasting hours on a config that was never going to work?

The framework below is backend-agnostic. The `backends/` subdirectory contains per-backend pages with the concrete partition/queue/instance details — read the relevant one(s) when picking specifics.

> **Project-level rules win.** If the project's `AGENTS.md` or `CLAUDE.md` says "always use CCM, never call vastai directly" or "this group has a CU Alpine allocation, use it for production," respect that. This skill is the framework; the project tells you the authority gradient.

---

## Core principle: iteration speed beats compute size

> **A failed cheap-partition job costs ~20 min. A failed production job costs 6–24 hr + queue politics.**

The moment you understand this, the rest of the skill follows. **Always validate on the cheapest partition that can run real physics, before scaling.** This isn't optional discipline — it's the default workflow. Skip it only when the config is *byte-identical* to a previously-validated one.

---

## Backend selection — decision tree

Walk the questions in order. Stop at the first match.

```
1. Is this a sub-30-minute CPU job (file munging, lint, plot)?
   → LOCAL. Don't pay setup overhead.

2. Is this a < 1-hour GPU job, or a smoke test of a new config?
   → CHEAPEST GPU AVAILABLE: testing partition on HPC if accessible,
      otherwise short Vast.ai instance. (~$0.20–0.50)

3. Is this a 1–8 hour GPU job, single-shot, no chained dependencies?
   → IF urgent or HPC busy: Vast.ai (instant queue, ~$0.50–4 total).
      ELSE: HPC production partition (free with allocation).

4. Is this an 8–24 hour GPU job?
   → HPC production partition. Cost balance favors HPC for jobs > ~6 hr.

5. Is this a > 24 hour single-shot job?
   → Prefer chained HPC jobs with restart. Use long-QoS only if
      restart isn't viable (rare for MD; common for some QM).

6. Is this an embarrassingly-parallel ensemble (50+ independent jobs)?
   → JOB ARRAYS on HPC if it fits. Vast.ai if HPC is throttling concurrency.
      Multi-backend split if budget + capacity allow.

7. Is the primary backend unavailable (network, VPN, allocation expired)?
   → Fall over to next-best backend per the table above. Document the
      fallback. Don't wait passively for primary if work can proceed.
```

### Code availability by backend (status 2026-07-04)

| Code | LOCAL | Vast.ai | Alpine |
|------|-------|---------|--------|
| LAMMPS | ✅ `$LMP` (`~/builds/lammps/build/lmp`, verified) | ✅ image/build per vast-cloud skill | ✅ modules |
| QE (pw.x) | ✅ **working** — QE 7.5 rebuilt 2026-07-03 (`~/builds/qe/{cpu,gpu}/bin`; CPU-MPI + GPU-serial); see quantum-espresso skill banner | ✅ build-from-source ("QE on VAST" section) | ✅ modules |
| MLIP stack | ✅ science-tools env (installed 2026-07-04; check `--verify`) | ✅ GPU images | ⚠ per-env |

Verify liveness with `python -m pytest benchmark/scoring -q` (and your compute backends) before
routing a job locally; this table records status as of its date, the probe
records truth.

If none of the above fits, stop and **ask the user** — that's a signal the job has unusual characteristics worth a human-in-the-loop discussion.

---

## The universal iteration loop

Every backend, every job size, follows this loop. The partition names change; the structure doesn't.

```
┌─ STAGE 0  Local sanity                 (< 5 min,  free)
│           dry-run, file manifest, syntax lint
└─ ↓ if clean
   ┌─ STAGE 1  Smoke on cheapest GPU     (~20 min,  ≈ free)
   │           5–10 ps run, real physics, real GPU
   │           Pass criteria: exit 0, finite energies, restart written,
   │           throughput in expected ballpark
   └─ ↓ if pass
      ┌─ STAGE 2  Single-system production  (hours)
      │           Real run, smallest realistic input
      │           Catches drift, density, long-time bugs
      └─ ↓ if pass
         ┌─ STAGE 3  Fan-out / production    (full campaign)
         │           Parallel jobs, real compute, real cost

   ↑ if any stage fails: don't escalate to a bigger partition.
     Drop *back down* to the smoke partition, fix, re-smoke, then continue.
```

**The big partition is read-only for validated configs.** Debugging substrate is the smoke partition.

### What a "smoke test" actually is

Same config as production, but `numsteps` (or `max_iter`, or `nsteps`, etc.) reduced so the job completes in 10–30 minutes. Same physics: same timestep, same thermostat, same force field, same parallelism settings, same output frequency. Only difference is the run length.

If smoke passes, the *only* untested behaviors are long-time ones (drift, slow equilibration, rare events). The bug classes filtered by a smoke test:
- File / parameter parsing errors
- Initial-geometry clashes (NaN energies in step 1–10)
- Output writing failures
- GPU memory issues
- Throughput in wrong ballpark (signals broken parallelism or missed flag)
- Restart file write failures

That's ~95% of failure modes for ~20 minutes of testing-partition time.

---

## Submission hygiene — universal

### Always

- **Dry-run before push.** Whatever local lint or `--dry-run` flag the deploy tooling has, run it.
- **Check the queue first.** `squeue -u <me>` before submitting; never stack a duplicate job.
- **Notify on completion.** `--mail-type=END,FAIL` on SLURM; equivalent on other backends. Avoid polling.
- **Log job IDs at submit time.** Drop into a tracking doc (project-level `STATUS.md`, playbook, or stage-status table). Don't rely on memory.
- **Use job arrays for fan-out.** `--array=1-N%C` caps concurrency at C. Friendly to shared queues.
- **Chain stages with dependencies.** `--dependency=afterok:$JOBID` over manual orchestration.
- **Restart-friendly checkpointing.** For long jobs, write restart files often enough that a walltime hit costs ≤ 1 hr of redo.

### Never

- ❌ Submit a production job without smoke first. The whole framework collapses.
- ❌ Submit while a sibling job for the same target is queued or running.
- ❌ Keep submitting after 3 consecutive same-error failures. Stop, ask the user.
- ❌ Hand-edit files on a remote backend. Fixes belong in the project repo, redeployed via the deploy tooling.
- ❌ `scancel` (or equivalent) without reading the log first. Even failed jobs have data.
- ❌ Poll long jobs in tight loops. Use mail-type notifications + scheduled wakeups, never `while true; do squeue; sleep 10; done`.
- ❌ Escalate "the queue was slow" → "use long QoS." Slow queue is a load signal, not a config bug.
- ❌ Run multiple smokes in parallel hoping one will work. Fix the first failure first.

---

## Failure → debug protocol

When any stage fails, walk this exact sequence. Don't skip steps.

1. **Pull the log.** Most recent `.out` and `.err` (or backend equivalent), `tail -200`.
2. **Diagnose locally.** Read the last error. Cross-reference against the project's "common failure modes" table (every project should have one — if it doesn't, add it). If the symptom is new, document it after diagnosing.
3. **Reproduce on the smoke partition** if at all possible. The smoke partition is the debugging substrate. Don't iterate against the production partition.
4. **Fix the source in the repo.** Edit the config / script / input *locally*, in the project's git tree. Hand-edits on a remote backend that don't survive a redeploy are tech debt.
5. **Re-smoke.** Stage 1 again. Then Stage 2. Then resume the campaign.
6. **Append to a "lessons learned" log.** One line: date, what failed, what fixed it. Future agents (and future-you) save real time.

---

## Waiting cadence

How long the job takes determines whether you wait, schedule, or detach.

| Job class | Wall | Strategy |
|---|---|---|
| Smoke | ~20 min | Wait in-conversation if no other work. Otherwise `ScheduleWakeup ~1500 s`. |
| Short production | 1–4 hr | Submit, log JOBID, advance. Re-check on user prompt or notification. |
| Long production | 4–24 hr | Fully detached. `--mail-type=END,FAIL`. Never poll. |
| Decorrelation / multi-day | 1+ days | Detached. Periodic `sacct` (or backend equivalent) summaries; don't watch. |

**Never** `sleep && squeue` busy-wait. Use the backend's notification channel + wakeup primitives.

---

## Multi-backend workflows

Some campaigns span backends — local prep + cloud GPU + HPC long-runs. The pattern:

| Phase | Compute load | Default backend |
|---|---|---|
| Literature search, structure prep, FF acquisition | CPU, light | LOCAL |
| Structure relaxation, equilibration | GPU, < 1 hr | LOCAL GPU or short cloud |
| Equilibration, single-system NPT | GPU, 1–8 hr | HPC or cloud |
| Production trajectory (long) | GPU, 8–24 hr | HPC (free) or cloud (urgent) |
| Ensemble fan-out (many short) | GPU, embarrassingly parallel | HPC arrays + cloud overflow |
| Analysis, plotting, manuscript | CPU, light | LOCAL |

**Data handoffs** are usually `rsync` (HPC ↔ local) or `scp` over the cloud instance's public IP. Plan handoffs explicitly — files that need to move between backends are first-class steps in the workflow, not afterthoughts.

---

## When to involve the user

Escalate (don't silently retry) on:

- Two consecutive smoke failures with the *same* error after a fix attempt.
- An unfamiliar bug not in the project's failure-modes catalog and you don't have high confidence in the fix.
- Compute cost about to exceed a previously agreed budget (cloud) or use > N% of a quarterly allocation (HPC).
- Any destructive action (canceling > 1 job, deleting remote data, restarting a campaign from scratch).
- A choice between two reasonable backends with materially different cost/latency profiles — the human gets to set the trade-off.

---

## Companion skills — composes with

This skill answers **WHERE** to run. Two siblings answer the other questions:

- **`compute-validation/SKILL.md`** — *IS IT READY*. Verification (reasoning, no compute) + smoke loop (cheap-compute measurement + extrapolation) before committing to production. Read this before any expensive submission.
- **`campaign-orchestration/SKILL.md`** — *HOW TO MANAGE LONG EXECUTION*. Stateless agents over per-campaign WORKFLOW.md files. Read this when a campaign has multiple stages over hours-to-days.

Read all three when driving a non-trivial compute campaign.

## Backend-specific details

Each available backend has a page in `backends/` with concrete partition/queue/instance details. Read the relevant one before picking specifics.

| Backend | Page | Use for |
|---|---|---|
| CU Boulder Alpine HPC | [`backends/alpine.md`](./backends/alpine.md) | Production GPU work, free with CU allocation |
| ALCF Polaris | [`backends/polaris.md`](./backends/polaris.md) | A100 GPU HPC (PBS Pro), free with DOE allocation; high-throughput MD; readiness vehicle toward ALCC/INCITE |
| ALCF Crux | [`backends/crux.md`](./backends/crux.md) | CPU HPC (dual EPYC Rome, 128 cores/node, PBS Pro), free with DOE allocation; large/parallel CPU MD, bulk core-hours |
| Vast.ai | [`backends/vast-ai.md`](./backends/vast-ai.md) | On-demand GPU, no queue, pay per hour |
| Local (WSL2 / native) | [`backends/local.md`](./backends/local.md) | Sub-hour CPU/GPU work, debugging, prep |

To add a new backend, copy `backends/TEMPLATE.md` and fill in the partition/queue/instance facts. Adding a backend should not require any change to this `SKILL.md` — it's framework, the backend page is data.

---

## Project-level layering

This skill is the *framework*. Projects are encouraged to add their own thin specialization layer:

- **Project `AGENTS.md` / `CLAUDE.md`**: which backends are authorized, any group-specific overrides ("never call vastai directly, use CCM"), per-project budget caps.
- **Project playbook** (e.g., `simulations/<campaign>/HPC_PLAYBOOK.md`): the *applied* version of this skill for one specific campaign — concrete commands, the stage-status tracking table, the lessons-learned log, the "common failure modes" catalog for that project's physics.

The skill provides the *standards* and the *decision framework*. The project provides the *application*.

A canonical example of the project-level layer (slab Thrust 4 in the Pt-NEC LOHC project): `~/work/research/hydrogenation/simulations/surfaces/HPC_PLAYBOOK.md`.

---

## Quick checklist before any compute submission

Use this as a self-check before you hit submit:

- [ ] Have I run the local dry-run / lint?
- [ ] Have I picked the backend via the decision tree?
- [ ] Have I checked the backend page for current partition/queue rules?
- [ ] If this is a new or modified config, have I smoke-tested it?
- [ ] If smoke passed, have I picked the right partition for production?
- [ ] Is `--mail-type=END,FAIL` (or equivalent) set?
- [ ] Have I checked `squeue` / equivalent for duplicates?
- [ ] Will my walltime + restart frequency survive a 24-hr cap?
- [ ] Have I logged the job ID into the project's tracking doc?
- [ ] Do I have a plan for what happens if it fails (which log to read, where the failure-modes catalog is)?

If any of those is "no" or "I don't know," fix that before submitting.
