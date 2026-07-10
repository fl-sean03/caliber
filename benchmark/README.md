# Caliber

A benchmark for autonomous computational-materials-science agents — does the agent choose
a sound method, run the real calculation, verify its own numbers, and report them honestly,
reliably, and efficiently.

- **[METHODOLOGY.md](METHODOLOGY.md)** — the three axes (correctness gate × pass^k ×
  cost-efficiency), grading (oracle-escrow ground truth), the difficulty horizon, and
  contamination defenses.
- **`runner/`** — the native session-holder runner (each model on its own native harness).
- **`scoring/`** — decomposed scoring (mechanical anchors ⊕ frozen judge), evidence store,
  provenance graph.
- **`suite/`** — task manifests (prompts + reporting keys) and sweep/audit tooling.

Public methodology, private answers: sealed keys, tolerances, and oracles live off-repo in
`caliber-private` and are injected only at grade time. No leaderboard numbers are published
until Caliber-1 is frozen with pass^k + cost.
