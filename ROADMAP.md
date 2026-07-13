# Roadmap

This roadmap describes the direction of the project. It is intentionally high-level;
concrete work is tracked in issues.

## Now — building Caliber-1

- **Task authoring.** ~30 research commissions across chemistry, physics, and materials —
  a brutal core of 10 (long-horizon campaigns, model-adequacy landmines, bounded discovery)
  plus 20 for breadth. Every candidate is screened against frontier models at maximum
  effort; tasks they ace are discarded.
- **Oracle grading.** Each task's ground truth is a high-compute reference computed by the
  grader (10–100× the agent's budget), with tolerances set to the reference method's own
  uncertainty — sealed off-repo.
- **Environment sealing.** Graded runs block lookups of the exact target; trajectories are
  audited for retrieval-vs-derivation.
- **Native harnesses for the evaluation panel** — Claude Code today; adapters for other
  vendors' native agent harnesses as they are benchmarked.

## At release

- **The release gate.** Caliber-1 ships only when the best frontier model at maximum effort
  lands ~15–40% on the correctness gate, with clear separation between models and pass^k
  well below 1.
- **Leaderboard + submissions.** Frozen-suite entries only, full trajectories required,
  Verified review flag from day one; every entrant scored through the same public path.
- **Reference results** published with the full three-axis profile (gate × pass^k × cost
  per correct solution) and an accuracy-vs-cost Pareto frontier.
- **Per-model failure profiles.** Results report *how* each model fails — where on the
  difficulty horizon it breaks, and whether the failure is method choice, convergence,
  reliability collapse, or cost blow-up — not just pass rates.

## Beyond

- **Environment sealing v2** — per-task network egress control and sanitized tool output.
- **Per-task containerized environments** for bit-reproducible compute.
- **Human expert baseline** for the hardest tier.

Have a task family you'd like to see? Open an issue.
