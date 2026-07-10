---
name: compute-validation
description: Validate that an expensive long-running compute campaign is ready for production. Combines reasoning-based verification (predict failure modes from system analysis + priors, before any compute) with empirical smoke analysis (run a cheap smoke, extract predictive signal, extrapolate to production behavior). Iterate until satisfied. Use before submitting any HPC simulation, ML training run, DFT calculation, or other expensive compute. Composes with compute-strategy (WHERE to run) and campaign-orchestration (HOW to manage long execution).
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - WebSearch
  - WebFetch
---

# Compute Validation — verify before computing, learn from cheap runs before committing to expensive ones

The discipline that catches predictable failures before any compute is spent, and turns cheap "smoke" runs into rich diagnostic measurements that *predict* production behavior. Pairs with `compute-strategy` (which decides backend) and `campaign-orchestration` (which manages long-running state).

> **One-line summary:** reason hard before compute, measure smartly during cheap runs, only commit production when both agree.

## When to use this skill

You're about to start a compute campaign that:

- Will take **hours to days** at full scale
- Has a cheaper **smoke mode** (smaller dataset, fewer steps, shorter timescale, smaller hardware)
- Has potentially **predictable failure modes** (drift, accumulation, resource exhaustion, parameter sensitivity)
- Costs real money or queue position when it fails late

This is the gate before any HPC submission, ML training run, DFT calculation, large data pipeline, or other expensive compute.

**Don't use it for:**
- One-off scripts finishing in minutes (overhead exceeds value)
- Interactive REPL work (write code, run, fix; smoke loops add no value)
- First-time exploration where you don't yet know what "smoke" means
- Pure I/O or data-movement tasks with no scientific content to validate

## The core insight

Smoke runs aren't pass/fail sanity checks — **they're measurements**. A 5-minute smoke produces enough data to predict 5-day production behavior, *if* the agent extracts the right signal.

Combined with reasoning-based verification (cheap, fast, catches predictable bugs), this gives three complementary error filters:

| Layer | Catches | Why |
|---|---|---|
| **Verification** (Layer A — physics reasoning, no compute) | Predictable physics/config failures (parameter mistakes, known-bad patterns, resource mismatches) | The agent reasons through the system using priors + analytical predictions |
| **Orchestration safety** (Layer A' — script reasoning, no compute) | Submission-side failures (runaway loops, silent chain death, race conditions, notification floods) | The agent reasons about scripts + submission patterns + automation; catches what physics-verification misses |
| **Smoke + Analysis** (Layer B — cheap compute, ~30 min) | Empirical drift bugs that only surface dynamically (slow box shrinkage, gradient explosion, memory leaks, throughput collapse) | Short-time observation → extrapolated long-time prediction |

What slips through all three layers is the genuine production-only risk class — rare and often instructive. Acceptable.

## The four-layer model

```
┌────────────────────────────────────────────────────────────────────┐
│ Layer A — VERIFICATION (physics reasoning, no compute)             │
│   • Read system, configs, priors, AGENTS.md, related campaigns     │
│   • Predict physics failure modes; estimate resources              │
│   • Apply mitigations BEFORE first compute                         │
│   → Output: VERIFICATION.md (green/yellow/red items + fixes)       │
└──────────────────────────────┬─────────────────────────────────────┘
                               ↓ (parallel sibling to A)
┌────────────────────────────────────────────────────────────────────┐
│ Layer A' — ORCHESTRATION SAFETY (script reasoning, no compute)     │
│   • Read submit scripts, deploy logic, workflow files              │
│   • Pattern-match priors + brainstorm pathological failures        │
│   • Verify circuit breakers for self-propagating actions           │
│   → Output: ORCHESTRATION_CHECK.md (risk register + mitigations)   │
│   Catches: runaway loops, mail floods, silent chain death,         │
│   walltime cliff bugs, dependency-semantics mistakes               │
└──────────────────────────────┬─────────────────────────────────────┘
                               ↓
┌────────────────────────────────────────────────────────────────────┐
│ Layer B — SMOKE LOOP (cheap compute + deep analysis)               │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  1. Run smoke on cheapest hardware (laptop, MIG slice, free) │  │
│  │  2. Extract predictive signal from output                    │  │
│  │     (box dynamics, drift, throughput, memory, anisotropy…)   │  │
│  │  3. Extrapolate to production timescale                      │  │
│  │  4. Compare measurement to Layer A predictions               │  │
│  │  5. Red flags? → propose fix → update config → re-smoke      │  │
│  │  6. Satisfied? → advance                                      │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  → Output per iteration: SMOKE_ANALYSIS_NNN.md                     │
│  → Iteration budget: default 5; escalate beyond                    │
└──────────────────────────────┬─────────────────────────────────────┘
                               ↓
┌────────────────────────────────────────────────────────────────────┐
│ Layer C — PRODUCTION                                                │
│   Configs locked, both layers satisfied, submit with confidence    │
│   Optional: real-time anomaly monitoring (mid-run state checks)    │
└────────────────────────────────────────────────────────────────────┘
```

## Where it composes

```
                ┌──────────────────────┐
                │ compute-strategy     │  WHERE to run (HPC, cloud, local)
                │ + backends/<host>.md │  Backend partition routing
                └──────────┬───────────┘
                           │
                           ▼
                ┌──────────────────────┐
                │ compute-validation   │  IS IT READY (this skill)
                │ + tools/<software>.md│  Software-specific signals
                └──────────┬───────────┘
                           │
                           ▼
                ┌──────────────────────┐
                │ campaign-orchestration│  HOW to manage long runs
                │ + WORKFLOW.md per    │  Stateful state machine
                │   campaign           │
                └──────────────────────┘
```

Read `compute-strategy/SKILL.md` first if you haven't picked a backend. Use this skill once a backend is chosen but before any submission. Hand off to `campaign-orchestration` once production runs.

## Layer A — Verification (deep reasoning before any compute)

[Detailed workflow: `workflows/verification.md`]

The agent investigates 8 categories before any compute:

| # | Category | What to check |
|---|---|---|
| 1 | **Config integrity** | Files exist, syntax valid, references resolve |
| 2 | **Domain sanity** | System is well-posed for the protocol (physics, statistics, numerics) |
| 3 | **Computational sanity** | Resource estimates match request: walltime, memory, throughput |
| 4 | **Pattern matching** | Does this match a known-bad pattern in `priors.yaml`? |
| 5 | **Precedent comparison** | How does this differ from the last successful run? Why? |
| 6 | **Risk assessment** | What are the top-3 failure modes? How would each be caught? |
| 7 | **External research** | For unfamiliar regimes: docs, forums, literature |
| 8 | **Output** | `VERIFICATION.md` with green/yellow/red items + recommended mitigations |

The agent should **falsify**, not validate. Actively try to find ways the campaign will fail. Confirmation bias is the enemy.

For high-stakes campaigns: dispatch 2 subagents to do independent verification, compare. Catches blind spots.

**Layer A is for physics reasoning. Layer A' (orchestration safety) is the sibling that reasons about scripts and submission patterns. Both must pass before Layer B.**

## Layer A' — Orchestration Safety (script/submission reasoning, no compute)

[Detailed workflow: `workflows/orchestration-safety.md`]

Parallel sibling to Layer A. Where Layer A asks "will the physics fail?", Layer A' asks "will the submission workflow fail?"

The agent investigates:

| # | Category | What to think about |
|---|---|---|
| 1 | **Pattern matching** | Does this match a known `class: orchestration` pattern in `priors.yaml`? |
| 2 | **Self-propagation register** | Every action that can spawn another action: in-script `sbatch`, arrays, dependency chains, cron/watchdogs, agent loops. For each: are all four circuit breakers present? (bounded counter, rate ceiling, failure ceiling, notification cap) |
| 3 | **Failure-mode brainstorm** | For THIS specific submission, how could it fail in pathological ways? Fast-fail loop? Walltime cliff bash unreliability? Race conditions? Dependency-type wrong choice? Resource limit hit? |
| 4 | **Worst-case enumeration** | Concrete numbers: how many submissions/emails/dollars/wasted-compute in the worst scenario? |
| 5 | **What am I NOT thinking about** | Final discipline check — re-read with fresh eyes, look for what's unusual about this job |
| 6 | **Output** | `ORCHESTRATION_CHECK.md` with risk register, mitigations applied, candidates to add to priors |

Backend-specific reasoning hints live in `tools/<backend>.md` (e.g., `tools/slurm-orchestration.md` for SLURM clusters).

The lesson encoded here: **any action that can self-propagate needs a circuit breaker.** Mail flood incidents, runaway resubmit loops, recursive agent spawning, watchdog cycles — all share this shape. The four-guardrails principle (bounded counter, rate ceiling, failure ceiling, notification cap) generalizes across all of them.

## Layer B — Smoke Loop (cheap compute + deep analysis)

[Detailed workflow: `workflows/smoke-analysis.md`]

The smoke is a *measurement instrument*. Each iteration:

1. **Run** smoke on cheapest available hardware
   - Laptop GPU if it fits (zero queue)
   - Free testing partition (atesting_a100, etc.) if not
   - Match physics to production exactly; only run length differs

2. **Extract** predictive signal from output (per-tool recipes in `tools/`)
   - For MD: box dynamics, energy drift, throughput, anisotropy, RMSD
   - For ML training: loss curve slope, gradient norms, throughput, memory growth
   - For DFT: SCF convergence rate, force consistency, time per cycle
   - Pattern: short-time observation → fit → long-time prediction

3. **Extrapolate** to production timescale
   - Linear/exponential fits where appropriate
   - Identify trajectories that cross failure thresholds before production ends
   - Flag drift trajectories that would invalidate the result

4. **Compare** measurement to Layer A predictions
   - Predicted X, measured Y, why?
   - Match → confidence builds; mismatch → priors are wrong OR a new pattern surfaced

5. **Decide**
   - Red/yellow flags remaining → propose fix, update config, re-smoke
   - All green + reproducible (2 consecutive smokes consistent) → advance to production

6. **Document** in `SMOKE_ANALYSIS_NNN.md` with what was measured, what was predicted, what diverged, what was fixed

## When the loop terminates ("satisfied" criteria)

[Full discipline: `workflows/iteration-discipline.md`]

**Advance to production when ALL hold:**

- All Layer A red items resolved
- Yellow items resolved OR explicitly accepted with rationale recorded
- Smoke measurements consistent with Layer A predictions (within tolerance)
- 2 consecutive smokes with no config changes show identical behavior (within noise) — reproducibility
- Extrapolation does not predict any failure threshold crossing within production timescale
- Iteration budget not exceeded (default: 5 smokes)

**Escalate to human when:**

- Iteration budget exceeded without satisfaction
- Same red flag persists after fix attempt — fix didn't work
- Novel signal not in priors AND agent confidence in interpretation is low
- Extrapolated production walltime exceeds requested walltime + buffer
- Cost cap would be exceeded (paid backends)
- Anything destructive proposed

## Layer C — Production

Configs frozen. Submit production with confidence.

Optional layer: **mid-run anomaly monitoring**. Periodic checks against the Layer A predictions while production runs:

- Real-time log tail
- Periodic state probes (every N hours, agent checks current trajectory matches predicted)
- Auto-cancel if anomaly detected (saves compute on a doomed run)

For one-shot productions, monitoring is optional. For multi-day campaigns, it's a strong recommendation.

## How a project adopts this skill

1. **Create `<project>/.priors.yaml`** seeded with known failure patterns for the project's typical systems
2. **Define smoke recipes** for each tool you use (or borrow from `tools/`)
3. **Update project's AGENTS.md** to require validation gate before any campaign submission
4. **Each new campaign** produces a `VERIFICATION.md` and ≥1 `SMOKE_ANALYSIS_NNN.md` before production
5. **As patterns are discovered**, append to `priors.yaml` so future campaigns benefit

This is the same pattern as `compute-strategy/backends/` — framework lives in ASW, application lives in project.

## Bidirectional learning loop

The system gets smarter over time:

```
Verification predicts X
   ↓
Smoke measures X
   ↓
Match? ───── YES → confidence in this prior pattern; reuse for similar systems
   │
   NO ────→ prior was wrong/incomplete; UPDATE priors.yaml with refinement

Smoke surfaces unexpected signal Y
   ↓
Did verification miss this?
   YES → add Y-pattern to verification checklist; update priors
   NO  → Y is genuinely new; document for future
```

After 10 campaigns the priors are meaningfully sharper. After 50, the system is hard to break. The patterns become tribal knowledge that doesn't depend on any one agent or person remembering.

## Generality across compute types

The framework is tool-agnostic. Specifics live in `tools/`:

| File | For |
|---|---|
| `tools/namd.md` | NAMD molecular dynamics |
| `tools/lammps.md` | LAMMPS molecular dynamics |
| `tools/qe.md` | Quantum ESPRESSO DFT |
| `tools/ml-training.md` | Generic ML training (PyTorch/JAX/etc.) |
| `tools/TEMPLATE.md` | How to add a new tool |

Each tool page documents:
- What diagnostic interfaces the tool exposes (logs, restart files, output formats)
- How to extract predictive signal (which numbers to fit, which trends to extrapolate)
- Tool-specific failure modes and how smoke surfaces them
- Throughput / memory benchmarks for sizing predictions

To add support for a new tool: copy `tools/TEMPLATE.md`, fill in. No change to `SKILL.md` or workflow docs needed.

## Templates

Use these as starting points:

- `templates/VERIFICATION.template.md` — per-campaign verification report
- `templates/SMOKE_ANALYSIS.template.md` — per-smoke-iteration analysis
- `templates/priors.template.yaml` — pattern catalog for a project

## Quick start (for an agent driving this)

You are about to validate a compute campaign. Walk this sequence:

1. **Read** the project's AGENTS.md, the campaign config(s), the project's `priors.yaml` (if present), and the relevant `tools/<software>.md` page
2. **Verify** — produce `VERIFICATION.md` with all 8 categories addressed; apply any red-item mitigations to the config
3. **Submit** the smoke (cheapest backend per `compute-strategy`)
4. **Wait** for completion (use ScheduleWakeup or `campaign-orchestration` cadence)
5. **Analyze** — produce `SMOKE_ANALYSIS_001.md` extracting all predictive signal; compare to Layer A predictions
6. **Decide**:
   - All clear AND reproducible? → advance to production
   - Red flag from smoke that's diagnosable? → propose fix, update config, re-smoke (loop)
   - Iteration budget exceeded OR genuinely novel issue? → escalate to human
7. **Submit production** once satisfied; optionally enable mid-run monitoring

The agent should record everything. The audit trail (VERIFICATION.md + SMOKE_ANALYSIS_NNN.md per campaign) becomes both reproducibility documentation and training data for future verifications.

## Why this design (rationale)

- **Reasoning is cheap, compute is expensive.** Spend reasoning to avoid compute.
- **Smoke is a measurement, not a check.** Extract everything possible.
- **Falsification beats validation.** Try to find failures, not confirm success.
- **Bounded iteration, explicit termination.** Don't loop forever.
- **Bidirectional learning.** Priors improve from every smoke.
- **Tool-agnostic framework, tool-specific specifics.** Same pattern, different signals.
- **Composable.** Pairs with compute-strategy + campaign-orchestration; doesn't reinvent.

## What this skill is NOT

- A test framework. There's no pass/fail boolean. The output is reasoned judgment + audit trail.
- A replacement for science. The agent doesn't decide if the protocol is scientifically correct — that's the human's call.
- A bypass for human review. High-stakes or novel campaigns still warrant a human eye on VERIFICATION.md.
- A substitute for monitoring. Production runs still need observability.

## Cross-references

- `compute-strategy/SKILL.md` — backend selection, where to run
- `campaign-orchestration/SKILL.md` — long-running state management
- `compute-strategy/backends/<backend>.md` — hardware specifics
- `compute-validation/tools/<tool>.md` — software specifics

When in doubt, read all four for the campaign you're driving.
