# Changelog

All notable changes to Caliber are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and versions follow
[Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-07-13

**The repository is now benchmark-only.** Caliber presents one thing: the Caliber-1
benchmark for autonomous hard-science research agents.

### Removed
- The agent skills layer (`skills/`, `AGENTS.md`, `CLAUDE.md`, `examples/`, `showcases/`,
  `configs/`, `templates/`, `scripts/`, agent environment/config templates). It is
  preserved in full, with history, on the `archive/capability-core` branch.

### Changed
- `README.md`, `CONTRIBUTING.md`, `ROADMAP.md`, and `CITATION.cff` rewritten around the
  benchmark alone: oracle-escrow grading, adversarial task validation, environment sealing
  + trajectory audit, provenance-verified runs, and three-axis scoring.
- CI pruned to the benchmark test surface.

## [0.1.0] - 2026-07-10

Initial public release of **Caliber** — one project, two halves:

- **Capability core** (`skills/`, `AGENTS.md`): 17 science skills + agent methodology
  that turn a coding agent into an autonomous computational-materials researcher.
- **Benchmark** (`benchmark/`): three-axis scoring (correctness gate × pass^k ×
  cost-per-correct-solution) against sealed oracle-escrow references; per-model native
  harnesses with run provenance; a versioned task suite (the calibration pilot sealed as the
  regression floor); public methodology, private answers.

Caliber continues the work previously published as the **Agentic Science Worker**
(github.com/fl-sean03/agentic-science-worker, archived at v0.3.0). Full prior history
lives in that repository.
