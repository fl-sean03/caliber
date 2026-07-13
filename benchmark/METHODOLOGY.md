# Caliber — methodology

Caliber-1 is the benchmark for **autonomous hard-science research agents** — chemistry,
physics, and materials (no biology). Given a hard research commission and a compute
environment, does the agent choose a sound method, run the real calculation, verify its own
numbers, and report them honestly — reliably and efficiently?

Caliber-1 is deliberately **lean and brutal**: ~30 commissions (a hard **core of 10** plus
**20 for breadth**), each an expensive real research run, so a model can be measured with a
handful of agent runs rather than a fleet of a hundred. It is built to **launch
unsaturated**. Public methodology, private answers.

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
moves up as models improve, never a ceiling they saturate.

**Structure of Caliber-1.** ~30 commissions on a single hard tier, tagged by **domain**
(chemistry · physics · materials, roughly balanced) and horizon:
- **Core (10)** — the brutal headline, horizon **H5–H7** (long campaigns → bounded
  discovery). Authored and iterated first.
- **Breadth (20)** — comprehensive coverage of hard-science sub-areas, horizon **H4–H6**.

There are no easy "warm-up" tasks in the release; saturated pilot tasks live in `examples/`.

## Release gate

Caliber-1 does not release until it is **brutal but cracking**. The gate, measured by
screening every candidate task against a frontier panel (GPT-5.6, Fable 5, Grok 4.5) at
**maximum effort**:
- the **best** model lands **~15–40%** on the correctness gate across the suite,
- there is **clear separation between models** (the suite discriminates the frontier), and
- **pass^k is well below 1** (no model is reliably perfect).

Candidate tasks a frontier model aces at max effort are discarded. This is the FrontierMath
funnel — launch below the frontier, keeping multi-year headroom — narrowed to hard science.

## Contamination & gaming defenses

- **Sealed answers, off public repo** (in `caliber-private`), injected only at grade time.
- **Seal the whole environment, not just the answer**: graded runs block lookups of the
  exact target (Materials Project / OQMD / literature), sanitize tool output, and
  trajectories are audited for retrieval-vs-derivation.
- **Procedural instantiation**: tasks are drawn from parameterized families
  (composition × property × structure × conditions) and instantiated fresh, with
  automated construct-validity checks on every instance.
- **Semi-annual rotation** with a permanent private holdout and disclosed access
  governance. Canary tokens are hygiene, not a primary defense.
- **Held-out set** — the released suite is paired with a never-published held-out slate in
  the private store for independent verification and overfitting monitoring. Public tasks can
  be tuned against; the held-out set cannot. Our own agent is scored through the same public
  submission path as any entrant.
- Sealing and rotation defend against *contamination*; the horizon axis is what defends
  against *capability-driven saturation* — both are required.

### Environment sealing & trajectory audit (v1)

Sealed answers protect the key; the trajectory audit protects the **path to the number** —
it detects an agent *retrieving* a graded quantity (database query, literature lookup on
the target system) instead of deriving it. Every task carries an **environment contract**
(allowed tools, blocked-and-audited lookups) in its prompt and in the private task store;
after each run, `suite/trajectory_audit.py` replays the transcript against that contract
as data (the tool is pure mechanism — no task specifics are embedded in the public repo):

1. **Tool-surface scan** — every tool call classified against the contract's
   allowed/blocked lists plus a built-in retrieval taxonomy (web search/fetch, browser,
   materials/chemistry databases, paper search).
2. **Lookup-phrase scan** — contract-supplied target-system names and close analogues
   matched over retrieval inputs *and* outputs, with context capture.
3. **Numeric-proximity heuristic** — numbers in retrieval outputs inside a graded key's
   window (suspicion only, never auto-void; locations reported redacted — sealed values
   never appear in the audit report).
4. **Provenance gap** — a reported graded value that never appears in any computation
   tool's output "came from nowhere".

Verdicts: **CLEAN** / **SUSPECT** (human adjudication) / **VIOLATION** (run **VOIDed** —
distinct from FAIL, and audited runs feed back into task hardening). Vendor-native raw
transcripts, where tool inputs and outputs cannot be separated, cap at SUSPECT — a run is
never auto-voided on unstructured evidence. v2 hardening (per-task network egress
allowlist, sanitized tool output) is planned post-launch.

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

**Caliber-1 is in active development.** A 17-task calibration pilot verified the grading
pipeline end-to-end and was saturated by a frontier model — the finding that set the release
gate above (see [DEVELOPMENT.md](DEVELOPMENT.md)). The release suite (~30 commissions, core
10 first) is being authored and screened against the frontier panel. No leaderboard numbers
publish until Caliber-1 freezes with pass^k + cost.
