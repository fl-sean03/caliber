# Caliber — leaderboard

*No entries yet.*

For the development/calibration pilot data (Claude Fable 5), see [DEVELOPMENT.md](DEVELOPMENT.md). That is not a ranked leaderboard entry.

Leaderboard entries are published only for **frozen generations**, scored on the full
three-axis profile — correctness gate, reliability (pass^k), and cost per correct
solution — never single-rep pass rates. Each entry must include the harness provenance
(`harness:{name,version,config_hash}`) and full run trajectories, and is reviewed before
the **Verified** flag is granted.

The leaderboard opens when **Caliber-1** freezes — a ~30-task suite (10-task brutal core +
20 for breadth across chemistry/physics/materials) authored to launch *unsaturated* (best
frontier model ~15–40% gate-pass). Until then it is intentionally empty. The 17-task
development pilot ([DEVELOPMENT.md](DEVELOPMENT.md)) is calibration evidence, not a ranked
result.

To submit: see [CONTRIBUTING.md](../CONTRIBUTING.md) — submissions require predictions,
metadata, logs, and complete trajectories generated at inference time.
