# Task versioning

Two mechanisms, following UK AISI Inspect + ARC-AGI/LiveBench practice.

## Per-task version — `N-X`
Each task carries `version: "N-X"` in its manifest entry:
- **N** (major) — bumps when a change breaks result comparability (tolerance, ground-truth,
  or scored quantity changed). Results across different N are NOT comparable.
- **X** (minor) — bumps when the task interface changes but scores stay comparable
  (prompt wording, reporting-key rename with a shim).

## The suite
Caliber-1 is a frozen, versioned suite: its public prompts + reporting keys live under
`benchmark/suite/<name>/MANIFEST.json` (no answers), its sealed answers/tolerances live under
the matching path in the private store, and it carries a **held-out set** (never-published
tasks) in the private store for independent verification — the defense against tuning against
public tasks. Once frozen, the suite and its per-task versions are stable so results stay
comparable.

## What a run records
Every run records the task `version` and the
`harness:{name,version,config_hash}` that produced it, so a leaderboard entry is always
traceable to an exact task+harness state.
