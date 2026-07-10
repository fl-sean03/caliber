# Workflow: Orchestration Safety (Layer A')

The agentic-reasoning workflow that catches script-level, submission-level, and chain-level failures **before** any compute is committed. Sibling to Layer A (physics verification). Both run before the smoke loop.

> **Core principle: this is reasoning, not linting.** Hardcoded checks only catch known patterns. Genuinely novel failure modes need an agent thinking through "what could go wrong with THIS specific submission?" Priors are *seeds* for that reasoning, not substitutes for it.

---

## When this workflow applies

Use this before any compute that involves:

- **Self-propagating actions** — in-script `sbatch`, job arrays, cron triggers, recursive agent spawning, watchdogs, auto-resubmit logic
- **Chained submissions** — dependency graphs, multi-stage pipelines, batch processing
- **Long-running workflows** — anything that runs for hours and could degrade silently
- **Notifications / external side effects** — email, Slack, webhooks, file watchers, cloud provisioning
- **Anything with quota/cost implications** — paid cloud, allocation-managed HPC, rate-limited APIs

Skip this for simple one-shot interactive jobs that finish in minutes with no automation. The cost of the reasoning exceeds the risk.

---

## Why this layer exists (the gap)

Layer A (verification) catches **physics-side predictable bugs** by reasoning about the simulation config + project knowledge.

Layer B (smoke loop) catches **drift bugs** by running a short empirical test.

Neither catches the class of bugs that live in the *interactions between script behavior, scheduler semantics, and self-propagation patterns*. Examples encountered in real campaigns:

- A simulation that crashes in 1 sec, plus an in-script auto-resubmit on failure, plus email-on-failure notification: produced 8,366 jobs and 16,000+ emails before being caught.
- An in-script resubmit pattern that relies on bash code running *after* the scheduler may have killed it: chain silently dies at walltime.
- A pre-chained dependency graph with both `afterany` resubmits AND in-script resubmits firing simultaneously: race condition on restart files, runs corrupted.
- Notification storms from `--mail-type=END,FAIL` on a 60-job array, every one of which writes 2 emails.

These bugs aren't in the simulation. They're in the *orchestration layer*. They need their own validation pass.

---

## The four-phase agentic workflow

For each campaign or new submission pattern, walk these phases. They're prompts for agent reasoning, not items to mechanically check.

### Phase 1 — Pattern matching against priors

Load the project's `.priors.yaml`. For each pattern with `class: orchestration` (or `class: hybrid`), check the `matches` predicates against the current submission.

For matches:
- Apply the mitigation
- Record the match in `ORCHESTRATION_CHECK.md`
- Note in case the agent needs to revisit

For near-matches (partial overlap with `matches`, similar shape, related domain):
- Read the `related_questions` for the prior
- Apply those questions to the current setup
- Document reasoning

This is the fast tier. Cheap. Catches what we've already learned. **But don't stop here** — Phase 2 is where novel issues are caught.

### Phase 2 — Active brainstorming

The bulk of the reasoning work. The agent actively asks, for this specific job:

#### A. "What's unusual about THIS job?"

Compare to the canonical pipeline / previous successful runs. Where does this one diverge?

- New code path (different submit script, new chain pattern, new partition combo)
- Different system size, walltime, or resource request than baseline
- New dependency chain shape, array configuration, or restart logic
- Anything where the agent is in unfamiliar territory

Novelty = increased risk. Lean into reasoning hard wherever something is unfamiliar.

#### B. "What self-propagates?"

List every action in the workflow that can spawn another action. Include:

- In-script `sbatch` calls
- `sbatch --array=...` directives
- Cron jobs or watchdog scripts
- Webhook triggers
- Agent loops, recursive subagents
- Any `--dependency=afterany` chain
- File-watcher pipelines

For **every** self-propagating element, verify all four guardrails are present:

1. **Bounded counter** — iteration limit so the chain cannot run forever
2. **Rate ceiling** — maximum submissions per minute/hour, preventing fast-fail explosion
3. **Failure ceiling** — maximum consecutive failures before halt
4. **Notification cap** — maximum emails/Slacks/webhooks per time window

Missing any one of these → **think harder**. Most runaway incidents trace to one missing guardrail.

#### C. "How can this fail in pathological ways?"

For THIS specific job, work through failure modes:

- **Fail in 1 second** — what triggers? typo in config, missing file, FF parse error, GPU init fail
- **Fail at walltime cliff** — script gets SIGTERM → SIGKILL. Does post-work bash run? Does the chain continue?
- **Node preemption / SLURM cancellation** — does the workflow recover or stall?
- **External dependency loss** — license server unreachable, scratch fills up, network drops
- **Race condition** — two chain links eligible at the same time, restart-file contention
- **Wrong-dependency-type semantics** — `afterany` vs `afterok` vs `aftercorr` — picked the right one?
- **Resource over/under-allocation** — wrong partition, wrong GPU type, wrong memory size
- **Quota / rate limit** — submission rate hits cluster-level limits, gets rejected silently or noisily

Don't enumerate generically; reason about which of these are PLAUSIBLE for the specific submission in hand.

#### D. "Worst-case enumeration"

For each scary failure mode identified in C, run the math:

- **Submission count blowup**: if pattern fires repeatedly, how many submissions per hour?
- **Notification volume**: emails per failed link × number of failed links = total inbox impact
- **Compute waste**: GPU-hours / dollars consumed before failure is detected
- **Recovery effort**: automatic, or does a human need to intervene? How long to recover?

The point is to make catastrophic scenarios *concrete*. "Mail flood" is abstract; "16,000 emails in 8 hours" is a real risk you wouldn't ship.

#### E. "What am I NOT thinking about?"

Final discipline step. After A-D, take a beat. Re-read the campaign config from scratch as if you're a reviewer with no context. What stands out?

- If everything looks fine, that's a flag — re-examine for confirmation bias
- Look at the script the way you'd look at a code review comment from a sharp colleague
- Cross-reference the project's recent `incidents` in priors — is anything in the current setup adjacent to a past incident?
- Talk through it: "if this goes wrong, the first sign would be..."

This is the falsification-mindset rule applied to orchestration. Don't search for evidence the workflow will work; search for evidence it'll fail.

### Phase 3 — Produce ORCHESTRATION_CHECK.md

Per-campaign artifact, similar shape to `VERIFICATION.md` but focused on script/submission/chain safety.

Contents:
- Frontmatter: campaign, project, status (green/yellow/red), production_ready
- Pattern matches found from priors + mitigations applied
- Self-propagation register: every self-propagating element + which guardrails are present
- Failure-mode risk register: top-3 worst-case failures for THIS job
- Brainstormed novel risks not yet in priors
- Mitigations applied (or accepted with rationale)
- Open questions for human review
- Candidates to add to priors after the run

Template at `compute-validation/templates/ORCHESTRATION_CHECK.template.md`.

### Phase 4 — Close the loop (post-run)

After the campaign finishes (or fails):

- **Anything unexpected happen?** → new prior entry. Use the rich schema (`matches`, `related_questions`, `generalization`).
- **Anything in priors didn't apply / was wrong?** → refine. Mark `last_observed` or revise risk_class.
- **Generalize**: don't just record "the cuboct decorr did X." Extract the principle ("self-propagating actions need circuit breakers") and update `generalization` accordingly.

The catalog grows smarter with each campaign. Future agents pattern-match faster, brainstorm in less-trodden territory.

---

## Reasoning categories the agent should consider

These are categories of risk to think *through*, not boxes to check. For any given job, the agent reasons about which categories apply.

### 1. Self-propagation and circuit breakers

The most common source of runaway disasters. Look for any action that can trigger another action — and verify the four guardrails (bounded counter, rate ceiling, failure ceiling, notification cap).

### 2. Failure cascade reasoning

For each failure mode, ask:
- What's the immediate response (graceful exit, retry, escalate)?
- What's the secondary effect (does the failure trigger more actions)?
- What's the cleanup path?

### 3. Resource economics

- Cost ceiling (paid backends): max dollars before halt?
- Allocation impact (HPC): how many node-hours consumed in worst case?
- Fairshare cost: heavy submission load lowers priority for future jobs

### 4. Notification volume

If notifications fire on completion or failure:
- Per-job notifications × number of jobs = inbox volume
- Per-failure notifications × failure rate = potential flood
- Cap or remove notifications for chain links

### 5. Concurrency / race conditions

- Two jobs eligible simultaneously: who wins the restart-file write?
- Locking discipline: are shared resources protected?
- Race-free serialization: `afterok` chains vs parallel `afterany` triggers

### 6. Walltime cliff behavior

- Will the work fit within `--time`?
- Does post-work bash actually run on SIGKILL? (Usually no; see "SIGKILL bash" failure pattern in priors)
- Restart files written frequently enough that walltime kill costs <1 hour of redo?

### 7. Dependency semantics

- `afterany`: next job runs whether prev succeeded or failed. Most common but most dangerous.
- `afterok`: next job runs only if prev succeeded.
- `afternotok`: next job runs only if prev failed (useful for recovery).
- `aftercorr`: array-element correspondence.

Picked the right one for your case? `afterany` is a sharp tool.

### 8. Recovery path

If the workflow stalls or fails:
- Automatic recovery (chain re-fires, file is regenerated, etc.)?
- Manual recovery (human notices, intervenes)?
- How long until someone notices? (Time-to-detection is itself a metric.)

### 9. Quota/rate-limit awareness

- Cluster: submit rate limits, max jobs per user, max GPUs per partition
- Cloud: API rate limits, billing rate limits
- Network: rsync rates, SSH connection limits

If the workflow could plausibly hit any of these, plan for it.

### 10. Side effects and external state

- Does the workflow write to shared filesystems? Files others might rely on?
- Does it modify scheduler state in non-obvious ways (e.g., reservations)?
- Does it create external artifacts (cloud instances, DNS records, billing items)?

Many bugs hide in these places because the agent doesn't naturally model them.

---

## Tool-specific reasoning hints

Different backends have different failure modes. Tool-specific reasoning hints live in `tools/<backend>.md`:

| Backend | Tool page |
|---|---|
| SLURM (HPC) | `tools/slurm-orchestration.md` |
| Vast.ai (cloud) | `tools/vast-ai-orchestration.md` (when written) |
| Kubernetes / pods | `tools/k8s-orchestration.md` (when written) |

Each tool page is itself NOT a hardcoded checklist. It's a reasoning hint document — categories the agent should think about, with examples of failures that have hit each category, and recommended patterns. The agent reads it to *seed* its thinking for the specific backend, then applies general reasoning.

---

## How orchestration safety composes with Layer A (physics verification)

Both are agentic verification layers. They run in parallel (or in either order) before the smoke loop:

```
   Layer A (verification)           Layer A' (orchestration safety)
   "Will this physics fail?"        "Will this submission fail?"
        │                                  │
        └───────────┬──────────────────────┘
                    ▼
           Both clear → smoke loop
```

They share patterns:
- Falsification mindset, not validation
- Priors as seeds, agent reasoning as engine
- Per-campaign artifact (VERIFICATION.md and ORCHESTRATION_CHECK.md)
- Bidirectional learning loop
- Escalation rules

They differ in domain:
- Layer A reasons about config content, physics, scientific correctness
- Layer A' reasons about scripts, submission, chain dynamics, automation

A campaign with a perfect physics config but a runaway resubmit is still a disaster. A campaign with bulletproof orchestration but wrong physics produces useless data. Both layers must pass.

---

## Bidirectional learning loop

The priors catalog is the durable artifact. Every campaign that surfaces a new orchestration failure (or near-miss) should add an entry. Every campaign that confirms an existing pattern should mark it as `last_observed`.

The schema for orchestration priors:

```yaml
- id: <slug>
  class: orchestration                # distinguishes from physics priors
  name: <human-readable>
  description: <one-paragraph>
  matches:                            # exact-match seeds (cheap pattern match)
    <key>: <value>
    <key>: { lt: <value> }
  related_questions:                  # prompts for novel-case reasoning
    - <question to ask if exact match doesn't fire>
    - <question to ask if exact match doesn't fire>
  generalization: |                   # the principle, not the case
    <The broader rule. Example: "self-propagating actions
    need bounded counter + rate ceiling + failure ceiling + notification cap.">
  mitigation:                         # concrete fix
    - <action>
  risk_class: low | medium | high | critical
  layer_caught: orchestration | smoke | production
  references:
    - <path or URL>
  discovered: YYYY-MM-DD
  last_observed: YYYY-MM-DD
  incidents: [<list-of-job-ids>]
```

`related_questions` + `generalization` are what make priors useful for novel cases. An agent encountering a new self-propagating workflow won't have an exact `matches` hit — but reading "is there a circuit breaker?" reasoning hint applies the same lesson.

---

## When to escalate to the human

The agent halts the campaign and surfaces to user when:

- A self-propagating element has missing guardrails AND the agent isn't confident in a mitigation
- Worst-case enumeration produces "catastrophic" (>>quota, >>budget, irrecoverable)
- A pattern matches a `risk_class: critical` prior and mitigation isn't clearly applicable
- Confidence in the brainstorming phase is low (agent isn't sure it caught everything)
- A novel pattern was identified but the mitigation isn't obvious

Don't half-fix and proceed. Surface, get input, then proceed.

---

## Common anti-patterns (and the correct alternatives)

### Anti-pattern: in-script `sbatch` resubmit, no counter

```bash
$NAMD ... && exit 0 || sbatch --dependency=afterany:$SLURM_JOB_ID slurm.sh
```

Failures: fast-fail loops produce thousands of submissions; bash may not run after SIGKILL.

Correct: pre-chained submission (queue N follow-up jobs upfront with explicit `afterany` deps; each link checks for early-exit condition; no in-script resubmit).

### Anti-pattern: `--mail-type=END,FAIL` on a chained workflow

Failures: every link fires emails; thousands of completion events flood inbox.

Correct: no mail-type on chain links, or mail only on the explicit final-completion job, or external monitoring instead.

### Anti-pattern: `afterany` for everything

Failures: chain proceeds even when upstream produces garbage; downstream uses bad inputs.

Correct: use `afterok` for stages that require upstream success; reserve `afterany` for restart/recovery patterns where you've explicitly designed for the previous link's failure.

### Anti-pattern: post-work bash assumed to run

Failures: SLURM SIGKILLs script at walltime; post-work logic never executes.

Correct: signal trap on `--signal=B:USR1@<seconds>` for graceful pre-walltime cleanup, OR pre-chained submission so the post-work logic isn't load-bearing.

---

## Quick checklist for an agent driving orchestration safety

You're about to validate a campaign's orchestration. Walk this:

1. ☐ Read the project's `.priors.yaml`; find all `class: orchestration` patterns
2. ☐ Read the submit scripts + deploy logic + workflow files for this campaign
3. ☐ Read this skill's relevant `tools/<backend>.md` page
4. ☐ Phase 1: pattern-match against priors; apply mitigations for matches
5. ☐ Phase 2: brainstorm — what's unusual, what self-propagates, how does it fail in pathological ways, worst-case enumeration, what am I missing
6. ☐ Produce ORCHESTRATION_CHECK.md with risk register, mitigations, open questions
7. ☐ If any guardrail is missing, any worst-case is catastrophic, any pattern is critical-class: escalate before committing compute
8. ☐ After the campaign runs: append new patterns to priors; refine existing entries

The whole point is *think hard about THIS job before committing compute*. Priors are memory aids. Reasoning is the engine.

---

## Cross-references

- `compute-validation/SKILL.md` — parent skill, the 4-layer model
- `compute-validation/workflows/verification.md` — Layer A (physics verification, sibling)
- `compute-validation/workflows/smoke-analysis.md` — Layer B
- `compute-validation/workflows/iteration-discipline.md`
- `compute-validation/templates/ORCHESTRATION_CHECK.template.md` — output artifact
- `compute-validation/templates/priors.template.yaml` — schema for both physics and orchestration priors
- `compute-validation/tools/<backend>.md` — backend-specific reasoning hints
- `campaign-orchestration/SKILL.md` — covers runtime monitoring during long campaigns; Layer A' is the static-analysis sibling
