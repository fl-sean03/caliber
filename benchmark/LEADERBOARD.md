# Caliber — leaderboard

*No entries yet.*

For **single-rep reference results** on the saturated batch-1 generation (Claude Fable 5), see [RESULTS.md](RESULTS.md). Those are not ranked leaderboard entries.

Leaderboard entries are published only for **frozen generations**, scored on the full
three-axis profile — correctness gate, reliability (pass^k), and cost per correct
solution — never single-rep pass rates. Each entry must include the harness provenance
(`harness:{name,version,config_hash}`) and full run trajectories, and is reviewed before
the **Verified** flag is granted.

The first published generation will be **caliber-2026.2** (batch-2: H4–H6 task families
with oracle-escrow grading). Generation `caliber-2026.1-batch1` is the frontier-saturated
regression floor and is not ranked.

To submit: see [CONTRIBUTING.md](../CONTRIBUTING.md) — submissions require predictions,
metadata, logs, and complete trajectories generated at inference time.
