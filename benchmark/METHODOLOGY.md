# Caliber — methodology

Caliber is a benchmark for **autonomous computational-materials-science agents**: given a
research commission and a compute environment, does the agent choose a sound method, run
the real calculation, verify its own numbers, and report them honestly — reliably and
efficiently. Public methodology, private answers.

## What is measured — three axes

An agent's result on a task is not a single pass/fail. Every run is scored on three
orthogonal axes, because a frontier agent can be correct-but-unreliable or
correct-but-ruinously-expensive:

1. **Correctness gate (binary).** The load-bearing physical quantities must land inside
   sealed per-task tolerances. Mechanical, judge-independent, all-or-nothing. A process
   judge (below) can never overturn a failed gate.
2. **Reliability — pass^k.** The task is run k independent times; we report **pass^k**, the
   probability the agent passes *all* k trials (contrast pass@k, which rewards one lucky
   run). Single-rep success hides reliability collapse; pass^k exposes it.
3. **Cost-efficiency.** Dollars and tokens **per correct solution**, reported as an
   accuracy-vs-cost Pareto frontier — not raw accuracy. Cheap-per-token agents can be
   expensive per task; this axis catches that.

A fourth, **DNF** (did-not-finish: budget/time exhausted without a verified answer), is a
distinct outcome from a wrong answer.

## Grading — how "correct" is defined (D1)

Ground truth is a **high-compute reference the grader computes**, not experiment and not
the agent's own numbers (oracle-escrow: the grader spends 10–100× the agent's budget on a
higher-fidelity calculation). Sealed per task:

- **DFT-gradeable quantities:** a converged reference at the task's specified functional,
  tight convergence (high plane-wave cutoff, dense k-mesh, tight force/energy thresholds).
- **MD/MLIP quantities:** long, equilibrated references with finite-size and statistical
  error quantified.
- **Gate tolerance** is the reference method's own uncertainty band (relative, per-quantity
  — tighter for structural, wider for energetics), sealed in the answer key. Never a global
  epsilon. Where experiment exists it is a *secondary* cross-check in the process rubric,
  never the gate — so a correct but method-limited result is not failed.

Mechanical extraction reads the agent's structured `reported_values`; a frozen,
separately-validated LLM judge scores *process* (method justification, uncertainty,
provenance, limitations) against a sealed rubric — decomposed so it cannot move the gate.

## Difficulty — the horizon (D2)

Difficulty is a dial, not a fixed bar, so Caliber degrades gracefully instead of
saturating. The scale is **coupled-stage count** (secondarily, required reference compute):

| Horizon | Shape | Example |
|---|---|---|
| **H1** trivial | single property / one SCF or MD observable | lattice constant of a metal |
| **H2–H3** | 2–4 coupled stages (structure → relax → property → cross-check) | cohesive energy with convergence + citation |
| **H4–H5** | multi-stage campaign + uncertainty + decision-under-uncertainty + model-adequacy validation | activation energy decomposed into formation + migration |
| **H6+** frontier | end-to-end paper reproduction / bounded discovery; oracle-escrowed answer; near-0% expected pass | reproduce a 2026 paper's key result from its methods |

The headline metric is the **stage-count at which pass-rate crosses 50%** — a scale that
moves up as models improve, never a ceiling they saturate. Each generation raises the
ceiling by adding stages.

## Contamination & gaming defenses

- **Sealed answers, off public repo** (in `caliber-private`), injected only at grade time.
- **Seal the whole environment, not just the answer**: graded runs block lookups of the
  exact target (Materials Project / OQMD / literature), sanitize tool output, and
  trajectories are audited for retrieval-vs-derivation.
- **Procedural instantiation**: tasks are drawn from parameterized families
  (composition × property × structure × conditions) and instantiated fresh each
  generation, with automated construct-validity checks on every instance.
- **Semi-annual rotation** with a permanent private holdout and disclosed access
  governance. Canary tokens are hygiene, not a primary defense.
- **Held-out generation** — each published generation is paired with a never-released
  variant slate in the private store, used for independent verification. Because the
  agent capability layer and the benchmark share this monorepo, this held-out slate is
  what keeps results honest: public tasks can be tuned against, the held-out slate cannot.
  Our own agent is scored through the same public submission path as any entrant.
- Sealing and rotation defend against *contamination*; the horizon axis is what defends
  against *capability-driven saturation* — both are required.

## Difficulty calibration

Candidate task families are screened against a frontier-model panel *before* scale
authoring, kept only if they land in a target pass-rate window (gate 20–50%; hardest tier
near 0–10%), with per-item difficulty and discrimination estimated from pilot data.

## Harness & provenance

Each model is run through its **own native harness** (Claude via Claude Code's native
session-holder; other vendors via their native runners), recorded in a
`harness:{name,version,config_hash}` provenance field — the measurement path adds no
custom orchestration. See `harnesses/native-claude/RUNNER.md`. Full run traces (reasoning, tool calls,
per-turn cost) and a PROV-typed provenance graph are captured for every run.

## Status

Generation batch-1 (the current sealed slate) is saturated on correctness at the frontier
and serves as the regression floor. Batch-2 (H4–H6 families, oracle-escrow, procedural
instantiation) is in design. No leaderboard numbers are published until a generation is
frozen with pass^k + cost.
