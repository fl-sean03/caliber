---
campaign: <slug>                       # short identifier, must match campaign dir
project: <project-name>                # e.g. hydrogenation, mxene-2026, solvfe
verified_by: claude-opus-4-7-1m        # model + identifier
created: YYYY-MM-DD
orchestration_status: yellow           # green | yellow | red | needs-human
production_ready: false                # set true only after Phase 2 brainstorm is satisfied
references:
  scripts:
    - <path>                           # e.g. simulations/<campaign>/deploy_hpc.sh
    - <path>                           # e.g. simulations/<campaign>/slurm.sh
  workflow:
    - <path>                           # e.g. simulations/<campaign>/WORKFLOW.md
  priors:
    - <path>                           # e.g. simulations/.priors.yaml
---

# Campaign: <name>

One-line purpose. Why this campaign exists, what it submits. Be specific about the
orchestration shape (single job? array? dependency chain? in-script resubmit?
agent-driven loop?) — that shape is what this document is reasoning about.

---

## TL;DR

- **Status:** <green / yellow / red> — one-line gist (e.g. "yellow: pre-chained
  dependency depth=8 reviewed; no in-script resubmit; mail-type capped on final
  link only").
- **Top concerns:** up to 3 bullets, highest-impact first.
- **Recommended next action:** advance to physics verification + smoke /
  apply mitigations and re-check / escalate to human.

---

## Phase 1 — Pattern matches from priors

**Priors loaded from:** `<path-to-priors.yaml>` (or "no priors.yaml; used
`<alternate-source>` such as project AGENTS.md or recent ORCHESTRATION_CHECK.md
files").

Patterns with `class: orchestration` or `class: hybrid` evaluated against this
submission:

| Pattern ID | Triggered? | Mitigation applied | Rationale |
|---|---|---|---|
| `slurm-runaway-resubmit-mail-flood` | yes (partial: has `--mail-type=END,FAIL` on a chained workflow) | removed `--mail-type` from chain links 2–8; kept on link 1 and on explicit `final-report` job only | per `priors.yaml` generalization: every chain link multiplying emails is a flood multiplier |
| `slurm-in-script-resubmit-no-counter` | no | n/a — using pre-chained submission instead | precedent campaign `2026-04-12-cubic-npt` already switched to pre-chained pattern |
| `walltime-cliff-post-bash-assumed` | yes | added `--signal=B:USR1@120` + trap to write a `terminated_at_walltime` flag before SIGKILL | submit-script's post-NAMD bash was previously load-bearing for the `progress.json` update |
| `<other patterns evaluated>` | — | — | — |

If a `risk_class: critical` pattern matched and mitigation was *not* applied,
that is a RED — explain why and either apply the mitigation or escalate.

---

## Phase 2 — Active brainstorming

The bulk of the reasoning work. Each subsection is a prompt the agent worked
through; the bullets are what came out. Detail beats generality here.

### A. What's unusual about THIS job

Compare to the canonical pipeline / last successful campaign. Where does this
one diverge?

- **Dependency chain depth = 8 (previous campaigns: 3).** This is the first time
  we've pre-chained 8 links. New territory for restart-file handoff between
  links.
- **First use of `--array=1-60` on this project.** Sixty array elements with
  per-task scratch directories; the previous record was 12.
- **New partition combo:** `aa100` requested with a fallback to `gpu` if
  full. Fallback path has never been exercised here before.
- **Walltime per link = 12 h** (vs. 6 h baseline). Twice the cliff exposure
  per link.

Novelty = risk. Each of the bullets above earns a deeper look in C below.

### B. Self-propagation register

Every action that can spawn another action — and whether each of the four
guardrails (bounded counter, rate ceiling, failure ceiling, notification cap)
is present.

| Element | Bounded counter | Rate ceiling | Failure ceiling | Notification cap | Mitigation applied |
|---|---|---|---|---|---|
| Pre-chained `afterany` deps (8 links) | yes — N=8 fixed at submit time | n/a (no in-script resubmit) | n/a (chain proceeds regardless; downstream re-checks input) | yes — `--mail-type` removed from links 2–8 | added `progress.json` early-exit guard so a corrupted link doesn't waste 12 h |
| Array `--array=1-60` | yes — bounded by spec | implicit (cluster sched) | no per-task ceiling — array continues if elements fail | NOT capped — `--mail-type=END` fires per task → 60 emails | **YELLOW**: removed `--mail-type` from array spec; only the final reduce job mails |
| Watchdog cron (`hourly_health.sh`) | no — runs forever | yes (1/hr) | no | yes (Slack-only, rate-limited at receiver) | accepted as-is (cheap, idempotent) |
| Auto-relaunch on node preemption | yes — `--requeue` with `MaxRequeue=3` in slurm.conf | yes | yes (3) | yes | OK |

Missing-guardrail rows must either be fixed or have explicit justification in
the rationale column. A missing guardrail with no rationale is a RED.

### C. Failure-mode brainstorm

For THIS specific job, what plausible pathological failures exist?

- **Fail in seconds**: a PSF/PDB path typo would crash NAMD before the 2-step
  minimization completes. With pre-chained deps using `afterany`, the next link
  fires immediately on the bad restart file. Without `progress.json` guard, all
  8 links would burn through queue in <1 minute. Mitigated: guard added.
- **Walltime cliff on link 4**: heaviest link; if it doesn't write restart in
  the last 30 s before SIGKILL, link 5 sees stale restart and runs duplicate
  ground. Mitigated: signal trap on SIGTERM writes restart pre-emptively.
- **Array element drift**: per-task scratch is local to the node; if a task
  re-runs on a different node (preemption + requeue), local scratch is empty.
  Not yet mitigated — see Open questions.
- **`afterany` semantics for a stage that needs upstream success**: link 3 is
  the unbiasing reweight; if link 2's MD failed, the reweight uses garbage
  inputs. Mitigated: changed link-3 dependency from `afterany` to `afterok`.
- **Quota: 60-element array hits `MaxSubmitJobs` per user**. Cluster limit on
  Alpine is 1000; we're well under. Accepted.
- **Mail flood**: 60 array elements × `--mail-type=END,FAIL` = up to 120 emails;
  if a config bug causes fast-fail, this compounds to thousands. Mitigated:
  mail-type stripped from array.

### D. Worst-case enumeration

For each scary failure mode in C, run the math. Make it concrete.

| Scenario | If unmitigated | After mitigation |
|---|---|---|
| Fast-fail loop on dependency chain (1 s NAMD fail, 8 links) | 8 jobs submitted in ~10 s, 8 emails, no compute waste | first link fails, `progress.json` flag set, downstream links exit-early — 8 jobs touch queue but each ~10 s; 1 email total |
| Array mail flood (60 elements, each emits END+FAIL) | up to 120 emails per run; on a fast-fail config bug w/ requeue, could compound to ~600 in an hour | 0 array emails; final-reduce job mails once |
| Link-4 walltime miss → stale restart → link 5 redo | 12 h wasted GPU-hours on link 5 (re-running already-done work, then crashing on validity check) | signal trap writes restart pre-emptively; link 5 starts from correct frame |
| Array element on preempted node loses scratch | redo from scratch on requeue, ~6 h wasted per task; up to ~360 GPU-hours across 60 tasks worst case | **NOT mitigated** — see Open questions; documented as accepted residual risk |

The point is to make catastrophic scenarios concrete. "Mail flood" is abstract;
"120 emails per submission, 600/hr if requeuing" is a problem you'd never ship.

### E. What am I NOT thinking about?

Final discipline. Re-read the campaign config from scratch as a hostile
reviewer.

- **Mid-run config swap**: the operator sometimes hand-edits `production.namd`
  between links to tune output frequency. If they edit while link N is in
  flight, link N+1 reads the new config. Not protected. **Action:** documented
  in WORKFLOW.md; consider freezing config to `inputs/.locked/production.namd`
  per-link in future.
- **Shared scratch contention**: array task 47 and task 48 both write to
  `/scratch/$USER/array_$SLURM_ARRAY_TASK_ID/`. Distinct paths — no contention.
  Verified by reading paths.
- **Restart write half-completes during SIGKILL**: NAMD writes restarts via
  rename, which is atomic on the same FS. Verified scratch and output dirs are
  same FS. OK.
- **Confirmation-bias check**: I keep wanting to say "the array is fine because
  we sized it well." But the *interaction* of array + fallback partition is
  untested. Marking as YELLOW pending smoke confirmation.

---

## Risk register

Top-3 worst-case failures specific to this job. Be specific; "things might go
wrong" is not a risk.

| # | Mode | Likelihood | Impact | Catch tier | Mitigation |
|---|---|---|---|---|---|
| 1 | Array element on preempted node loses local scratch | medium (preempt rate ~5%/day on `aa100`) | up to ~6 h wasted per task | production (only visible in retrospect) | accepted residual risk; documented in WORKFLOW.md; mitigation deferred |
| 2 | Operator mid-run config edit clobbers link N+1 inputs | low | invalidates the run | none currently | documented in WORKFLOW.md; agent-side check in future |
| 3 | Fallback partition `gpu` (mixed GPUs) gives wrong throughput | low (only fires when `aa100` full) | walltime cliff on long links | smoke (Layer B): re-run a short smoke on `gpu` if fallback ever triggers | flag set; campaign-orchestration will alert if fallback fires |

"Catch tier" = where this would be detected:
- `orchestration` — already caught here in Phase 1/2
- `smoke` — Layer B will surface
- `production` — only visible at full scale (these are the residual risks)

---

## Mitigations applied to scripts/workflow before submit

Concrete edits made as a result of this reasoning. Each as
`<file:line> <change> <rationale>`. One per bullet.

- `slurm.sh:14` — removed `--mail-type=END,FAIL` from array spec (kept on
  `final-reduce.sh:14`). Rationale: 60-element notification cap, matched
  prior `slurm-runaway-resubmit-mail-flood`.
- `slurm.sh:22` — added `#SBATCH --signal=B:USR1@120` + trap handler that calls
  NAMD's `outputname.checkpoint`. Rationale: matched prior
  `walltime-cliff-post-bash-assumed`.
- `deploy_hpc.sh:48` — changed link-3 dependency from `afterany` to `afterok`.
  Rationale: reweight stage requires valid upstream MD; brainstorm phase
  surfaced this.
- `deploy_hpc.sh:62` — added pre-flight `progress.json` early-exit check
  inserted at top of each chain link. Rationale: prevent fast-fail propagation
  through 8 pre-chained links.

If no mitigations were applied, write "none — submission passes orchestration
review as-is" and explain why no edits were needed. Acceptable for byte-identical
re-runs of an already-cleared submission pattern.

---

## Recommended monitoring during the run

What the agent (or operator) should watch for to detect a problem early.

- **First 5 minutes after submit:** confirm only link 1 is `RUNNING` and links
  2–8 are `PENDING (Dependency)`. Anything else means dep graph is malformed.
- **Hourly:** check `squeue -u $USER` count is bounded. Spike to >70 = runaway.
- **On every link transition:** read tail of `out.<jobid>.log`, confirm NAMD
  log ends with a clean restart write (not SIGKILL mid-write).
- **End of campaign:** confirm exactly 1 email arrived from `final-reduce.sh`.
  More than 1 = a chain link bypassed the mail-type strip.

This list seeds the runtime monitoring story (handed to `campaign-orchestration`).

---

## Open questions for human review

If any. Often empty for well-precedented submissions; non-empty when the agent
identified a residual risk it couldn't cleanly mitigate.

- **Array element scratch loss on preempt:** mitigation would require either
  (a) job-local scratch backed by shared FS (slow, contention), (b) periodic
  shared-FS sync (complex), or (c) accept and re-run on requeue. Recommending
  (c) for this campaign; flagging for human confirmation.
- **Mid-run config swap protection:** worth a generic agent-side check in
  campaign-orchestration?

---

## Verdict checklist

- [ ] Phase 1 patterns evaluated; mitigations applied for triggered priors
- [ ] Phase 2 brainstorm completed (A–E); novel risks surfaced
- [ ] Self-propagation register: every element has all 4 guardrails or explicit accept
- [ ] Risk register filled with concrete top-3 modes
- [ ] Mitigations applied and documented
- [ ] Monitoring plan handed to campaign-orchestration
- [ ] Cleared to proceed (or escalated to human)

---

## Candidates to add to priors after this campaign

Patterns surfaced during this brainstorm that aren't yet in `.priors.yaml` and
that future campaigns would benefit from. Use the rich schema (`matches`,
`related_questions`, `generalization`).

- **Draft:** `slurm-array-mail-type-flood` — `--mail-type=END,FAIL` on any
  `--array` is a flood multiplier. Related questions: "what does N × per-task
  notification add up to?" Generalization: cap notifications at chain
  boundaries, not at every link.
- **Draft:** `slurm-fallback-partition-throughput-drift` — fallback partition
  switch changes the throughput baseline silently. Related questions: "do all
  partitions in the fallback chain produce equivalent throughput? if not, does
  walltime sizing accommodate the slowest?"

Add after the campaign closes; refine `last_observed` / `incidents` from real
data.

---

## Cross-references

- Parent skill: `compute-validation/SKILL.md`
- Workflow: `compute-validation/workflows/orchestration-safety.md`
- Sibling Layer A: `compute-validation/workflows/verification.md`
- Priors schema: `compute-validation/templates/priors.template.yaml`
- Backend-specific reasoning: `compute-validation/tools/<backend>.md`
- Runtime monitoring: `campaign-orchestration/SKILL.md`
