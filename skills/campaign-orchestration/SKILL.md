---
name: campaign-orchestration
description: Orchestrate one or more long-running compute campaigns (HPC simulations, multi-stage MD pipelines, ensemble runs) where stages take hours to days and failures must not halt the pipeline. Use when running multiple parallel campaigns that share a stage structure (smoke → equilibration → production → analysis), when waiting on long jobs makes interactive driving impractical, or when designing a self-healing tick-based supervisor for compute work. Reads/writes per-campaign WORKFLOW.md files as durable state.
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
---

# Campaign Orchestration — stateless agents, durable workflow files

A practical pattern for managing many long-running compute campaigns (think: 10+ HPC simulations, each a multi-stage pipeline, each stage taking hours to days) without dedicating a persistent agent to each one.

## Core idea

> **State lives in `WORKFLOW.md` files. Agents are stateless workers that tick over the files.**

Each campaign has a `WORKFLOW.md` that declares its stages, current position, job IDs, action queue, failure history. An orchestration tick reads all the files under a search root, advances or debugs each one, writes the files back, and exits. Next tick is a fresh agent that picks up where it left off. The file is the state machine; the agent is a function `(file, time) → (new file, side effects)`.

This is the same pattern that powers Argo Workflows, Airflow, and anything else that has to survive worker restarts.

> **Who re-invokes you matters (2026-07-07).** A tick ends by yielding, expecting
> a *fresh* agent next. That re-invocation comes from your **surface**: a live/
> managed session (`ScheduleWakeup`/`/loop`) OR the **`asw-loop` supervisor**
> (`claude -p --resume`, used for headless/benchmark runs). Under headless
> single-shot `-p` with NO supervisor, a yield is a DEATH — nothing re-invokes
> you. So: run long campaigns under `asw-loop` (or a managed session), and for
> the per-job launch/detach/harvest mechanics follow the **`long-compute`**
> skill. `status == running` is **never** `done` — always re-validate against the
> job's own exit sentinel, never your memory. Short jobs (≲10 min): BLOCK in the
> tick (`run_in_background` + poll), don't detach-and-yield.

## When this skill is the right pattern

- You have **N ≥ 2 campaigns** (otherwise just drive interactively).
- Stages are **long** (hours to days). Interactive driving wastes context.
- Failures are **expected** but **diagnosable** — the agent can read a log, infer a fix, retry.
- You want a **single dashboard** view (`cat WORKFLOW.md`) without building a UI.
- You want to **escalate to a human** only on novel or destructive situations.

If your work is one short campaign, skip this — interactive is fine. If failures are catastrophic / irreversible, this isn't the right substrate.

## The WORKFLOW.md schema

One file per campaign. YAML frontmatter for machine-readable state, Markdown sections for human-readable detail.

```yaml
---
campaign: <slug>                  # short identifier, must match dirname
project: <project-name>           # e.g. hydrogenation
created: 2026-05-05
last_tick: 2026-05-05T20:10:00Z   # updated each orchestration tick
status: <enum>                    # see Status section
current_stage: <stage-name>       # the first non-done stage
escalation_required: false        # true halts ticks until cleared
escalation_reason: ""             # one-line summary if escalated
budget:
  backend: alpine                 # alpine | vast-ai | local
  cap_usd: 0                      # 0 for free Alpine; cumulative cap for paid
  spent_usd: 0                    # updated post-stage
notify:
  on_advance: false               # ping user when stage advances
  on_escalate: true               # ping user when blocked
references:                       # files agents should read for context
  - path: AGENTS.md
    section: HPC operations
  - path: simulations/surfaces/HPC_PLAYBOOK.md
---

# <Campaign Title>

One-paragraph purpose. Why this campaign exists, what it produces.

## Stages

| # | Name              | Entry condition       | Exit condition                | Status   | JobID    | Started     | Completed   | Retries |
|---|-------------------|-----------------------|-------------------------------|----------|----------|-------------|-------------|---------|
| 0 | dry-run           | always                | manifest OK                   | done     | —        | YYYY-MM-DD  | YYYY-MM-DD  | 0       |
| 1 | smoke             | stage 0 done          | exit=0, restart, no NaN       | done     | 12345678 | YYYY-MM-DD  | YYYY-MM-DD  | 1       |
| 2 | npt-prod          | stage 1 done          | npt_equil.restart.xsc, ρ ≈ ρ* | running  | 12345700 | YYYY-MM-DD  | —           | 0       |
| ...                                                                                                                          |

Each row tracks one stage. **Entry condition** is what must be true before this stage can submit. **Exit condition** is the validation predicate. **Status** is the enum below. **Retries** counts attempts at this stage (escalation triggers at retries ≥ 2 for the same error).

## Status enum

| Status     | Meaning                                                    | Next tick action |
|-----------|------------------------------------------------------------|------------------|
| `pending` | not yet eligible (entry condition not met)                 | check entry condition; advance to `ready` if met |
| `ready`   | entry condition met, not yet submitted                     | submit; advance to `running` |
| `running` | submitted to scheduler, job in flight                      | poll status; on completion validate exit and advance to `done` or `failed` |
| `done`    | exit condition validated                                   | move on to next stage |
| `failed`  | scheduler reported failure OR exit condition not met       | diagnose, attempt one fix, retry once → `ready`; on second same-error → `escalated` |
| `escalated` | requires human                                            | no-op, log timestamp |

## Action queue

Free-form bullets describing what the agent should consider on the next tick. The agent updates this section as it works. Example:

```
- [ ] Job 12345700 submitted at 19:55. Re-check status next tick.
- [ ] If job completes cleanly: rsync npt_equil.restart.* back locally, then deploy stage 3.
- [ ] If job fails with "OOM": switch to gh200 partition. (Pre-approved fallback.)
```

## Failure log

Append-only. Each failure adds a row.

```
| Date | Stage | Error class | Error msg (1 line) | Action taken | Result |
|------|-------|-------------|---------------------|--------------|--------|
| 2026-05-05 | smoke | velocity-limit | Atom 19658 v=14658 > 12000 | minimize 1000 → 10000 | RESOLVED |
```

## Lessons learned

Free-form notes. Append as discovered. Useful for "next time we hit this, do X."

## References

Pointers to playbooks, framework skills, related project docs.

---

## Orchestration agent behavior — spec

This is what an agent runs when invoked with "orchestrate the campaigns under <root>."

### Tick procedure

```
For each WORKFLOW.md found under <root>:
  1. Read frontmatter + stage table + action queue.
  2. If escalation_required is true:
       log timestamp, skip this campaign.
  3. Find the first stage with status != done.
     a. If status == pending: check entry condition (parse it from the row).
        - If met: advance to ready.
        - Else: skip.
     b. If status == ready: submit (deploy_hpc.sh, sbatch, etc.).
        - Record JobID, set status=running, started=now.
     c. If status == running: query scheduler.
        - Still running: log "still running at HH:MM:SS", no-op.
        - Completed:
            evaluate exit condition (parse from row, e.g. "exit=0, restart written").
            If passes: status=done, completed=now. Continue loop to next stage same tick.
            If fails: status=failed, append to failure log.
        - Failed (scheduler-reported): same as failed-validation path.
     d. If status == failed:
        Pull log, classify error against catalog (or new):
        - If catalogued + auto-fix exists + retries < 2: apply fix, status=ready, retries++.
        - Else: status=escalated, escalation_required=true, escalation_reason=<class>.
     e. If status == escalated: skip (handled at top).
  4. Update last_tick timestamp.
  5. Save WORKFLOW.md.

After processing all campaigns:
  Compute next-tick cadence based on most-active campaign (see cadence table).
  ScheduleWakeup with that delay.
```

### Cadence table (next-tick delay)

| Most active campaign state | Re-tick in |
|----------------------------|------------|
| Active short job (smoke, < 1 hr expected) | 4–6 min |
| Active medium job (1–4 hr expected) | 30–60 min |
| Active long job (4–24 hr expected) | 2–4 hr |
| Active multi-day job (> 24 hr) | 8–12 hr |
| All campaigns idle / done / escalated | 12 hr (or until user prompt) |

Choose the **shortest** cadence among active campaigns. Don't sleep through fast jobs to be polite to slow ones.

### Failure classification

The agent maintains two catalogs:

1. **Cross-project (in this skill, see `failure-catalog.md`)** — generic patterns: walltime exceeded, GPU OOM, node death, transient SSH failure.
2. **Per-project (in the project's docs)** — physics-specific: NAMD velocity limit, density drift, snapshot extraction errors. Lives in the project's HPC playbook or AGENTS.md.

When the agent sees a failure: try to classify against both catalogs. If matched and an auto-fix exists, apply it. If unmatched, escalate. After resolving, append to the project catalog so the next agent recognizes it.

### Escalation rules — when to halt and ping the user

The agent **halts the campaign** (sets `escalation_required: true`) on any of:

- **2 consecutive same-error failures** at the same stage. The fix didn't work; humans needed.
- **Unfamiliar error** not matched in either catalog and not in a "safe to retry" pattern.
- **Cost cap exceeded** (paid backends only).
- **Destructive action proposed** (cancel > 1 job, delete data, restart-from-zero, modify force-field params).
- **Stage stuck > 3× expected walltime** without checkpoint progress (deadlock indicator).

Escalated campaigns sit until the human resolves and clears the flag. Other campaigns continue normally.

### Pre-approved actions (no escalation)

The agent may freely:

- Submit a stage when its entry condition is met
- Validate exit conditions and advance
- Re-submit a job that hit walltime *if* checkpoint state advanced
- Apply a catalogued fix once
- Sync output files back to local
- Update WORKFLOW.md state and timestamps
- Append to failure log and lessons learned
- Call `squeue`, `sacct`, `scancel <single_job>` (single-job cancellation only)

## How to invoke

Three reasonable invocation patterns:

### Pattern 1: User-driven manual tick

```
"Run an orchestration tick across all campaigns under simulations/."
```

The agent walks the files, advances/debugs, schedules a wakeup, exits.

### Pattern 2: Self-paced loop

```
/loop "Run an orchestration tick on simulations/<project>/. Schedule the next tick yourself based on cadence."
```

The agent re-fires itself on each tick. Most autonomous mode.

### Pattern 3: Cron-triggered (most production-grade)

System cron or `/schedule` triggers the agent every N minutes with the same prompt as Pattern 1. Stateless invocations; durable WORKFLOW.md state.

## Project-level integration

The skill is project-agnostic. To use it on a new project:

1. **Pick a search root** — usually `simulations/` or `campaigns/`.
2. **Drop a `WORKFLOW.md` in each campaign directory** following the schema above.
3. **(Optional) Add a project-level slash command** (e.g. `/<project>-tick`) that just expands to "orchestrate campaigns under <root>" — saves typing.
4. **Maintain a project-specific failure catalog** in your project's HPC playbook (e.g., `simulations/.../HPC_PLAYBOOK.md` § Common failure modes). The agent reads it on each tick.

## Templates

Starter WORKFLOW.md skeletons live in `templates/`. Copy and edit:

- `templates/WORKFLOW.template.md` — generic multi-stage HPC campaign
- `templates/WORKFLOW.namd-ensemble.md` — pre-fab for NAMD MD ensembles (NPT → 1000K decorr → snapshots → cool+prod array)

## Runtime monitoring during the tick (agentic anomaly scan)

Each orchestration tick should do more than progress state machines. It should also reason about whether the *current state of all campaigns* looks healthy — the runtime sibling to `compute-validation/workflows/orchestration-safety.md` (which is static pre-submission analysis).

This is agentic, not threshold-based. The agent reads sacct + queue state + recent logs and asks:

- **Does the pattern of completions look right?** Compare submissions/completions per hour against expected throughput for each campaign. Sudden spikes (>10 completions in 15 min) or pile-ups (>50 same-name jobs queued) are anomalies even if no single threshold fires.
- **Are any chains stalling?** A chain link in PD for >24 hr while others advance is suspicious.
- **Are any failures replicating?** Two consecutive same-error failures on a chain = pattern; investigate before continuing.
- **Are any logs producing unexpected output?** Real-time log tail check for FATAL, OOM, "RESTART" without progress, or other anomaly signatures.

Use the project's `.priors.yaml` (`class: orchestration` patterns) as seeds for what anomalies to look for. The runaway-resubmit pattern (today's bug class) shows up as "many fast completions in short time" — a heuristic the agent can apply.

When the scan flags concerns:
- **Low confidence**: write to the campaign's WORKFLOW.md action queue for next tick
- **Medium confidence**: pause the chain (`scancel` future links) and write to ORCHESTRATION_CHECK.md
- **High confidence + critical class**: escalate to user immediately

The agent should reason about the specific campaign, not just match thresholds. A pattern that looks like a runaway in a NAMD context might be normal in a different campaign — context matters. Same falsification mindset that drives Layer A and Layer A' applies to runtime monitoring.

This is the *post-submission* analog to Layer A' (`compute-validation/workflows/orchestration-safety.md`'s pre-submission static analysis). Together they catch:
- Pre-submission: predictable orchestration anti-patterns + brainstormed risks
- Runtime: novel anomalies that emerge during execution
- Post-run: bidirectional learning loop updates priors

## Why this design

- **Durable state** — files survive agent restarts, reboots, model changes
- **Stateless workers** — agents are cheap to spin up, don't need conversation continuity
- **Inspectable** — `cat WORKFLOW.md` is the dashboard
- **Composable** — adding a 6th campaign is dropping a file
- **Human-in-the-loop where it matters** — escalation rules keep destructive things gated
- **Cadence-aware** — fast jobs get fast checks, slow jobs get slow checks; nothing's polled in a tight loop

## What this skill does NOT do

- Build a job-tracking database. The filesystem is the database.
- Provide a web dashboard. `cat WORKFLOW.md` is the dashboard.
- Wire event-driven notifications from HPC. Periodic polling is fine at HPC timescales.
- Execute simulations. It only orchestrates them — it calls deploy scripts and SLURM submit scripts that already exist.
- Replace project judgment about what stages should exist. Each project defines its own stages in its WORKFLOW.md files.

## Cross-references

- `compute-strategy/SKILL.md` — backend selection, smoke-first iteration, the underlying compute decisions this skill orchestrates over
- `compute-validation/SKILL.md` — verification + orchestration-safety + smoke-loop discipline. A campaign's stages should follow this skill's protocol. WORKFLOW.md may include `0.5-verification` (requires `VERIFICATION.md`) AND `0.6-orchestration-check` (requires `ORCHESTRATION_CHECK.md`) before any compute-bearing stage.
- `compute-validation/workflows/orchestration-safety.md` — Layer A' static analysis of submission scripts; this skill's runtime-monitoring tick is the post-submission complement.
- `vast-cloud/SKILL.md` — Vast.ai backend driver
- For Alpine HPC specifics: `compute-strategy/backends/alpine.md`
