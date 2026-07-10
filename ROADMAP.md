# Roadmap

This roadmap describes the direction of the project — the agent capability core and the
Caliber benchmark, which live together in this monorepo. It is intentionally high-level;
concrete work is tracked in issues.

## Now (v0.3)

- **The monorepo foundation.** One home for the capability core (`skills/`, `AGENTS.md`)
  and Caliber (`caliber/`): native per-model harnesses, decomposed three-axis scoring
  (correctness gate × pass^k × cost per correct solution), versioned task generations,
  and public methodology with sealed private answers.
- **Native harness measurement.** Each model is benchmarked through its own native harness
  (session-holder for Claude Code; others as added), recorded in run provenance — the
  measurement path adds no custom orchestration.
- **Durable execution.** Long-horizon DFT/MD campaigns that survive interruptions — jobs
  are detached, state lives in files, and the agent is woken to harvest.

## Next — Caliber generation 2026.2 (batch-2)

- **Harder, unsaturatable task families.** The difficulty *horizon* (coupled-stage count,
  H1 trivial → H6+ end-to-end paper reproduction / bounded discovery) becomes the headline
  scale; generation batch-1 is retained as the saturated regression floor.
- **Oracle-escrow grading.** References computed by the grader at 10–100× the agent's
  budget; gate tolerances set to the reference method's own uncertainty.
- **Procedural instantiation + held-out generation.** Task families instantiated fresh per
  generation with construct-validity checks; a never-published held-out slate for
  independent verification.
- **Difficulty calibration before authoring at scale.** Candidate families screened
  against a frontier-model panel into target pass-rate windows.
- **Leaderboard + submissions flow.** Frozen-generation entries only, full trajectories
  required, Verified review flag; our own agent submits through the same public path.

## Later

- **Environment sealing for graded runs** (target-lookup blocking, retrieval-vs-derivation
  trajectory audits) as a first-class harness feature.
- **Per-task containerized environments** for bit-reproducible compute.
- **Additional science domains** beyond the current materials focus.
- **Human expert baseline** for the hardest tier.

Have a use case or a benchmark task family you'd like to see? Open an issue.
