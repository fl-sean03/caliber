# Task & generation versioning

Two mechanisms, following UK AISI Inspect + ARC-AGI/LiveBench practice.

## Per-task version — `N-X`
Each task carries `version: "N-X"` in its manifest entry:
- **N** (major) — bumps when a change breaks result comparability (tolerance, ground-truth,
  or scored quantity changed). Results across different N are NOT comparable.
- **X** (minor) — bumps when the task interface changes but scores stay comparable
  (prompt wording, reporting-key rename with a shim).

## Named generations
A release is a frozen suite published together (`Caliber-1`, and only if it ever saturates, `Caliber-2`),
tagged in git. Each generation:
- lives under `benchmark/suite/<release>/MANIFEST.json` (public prompts + keys, no answers),
- has its sealed answers/tolerances under the matching path in the private store,
- SHOULD carry a **held-out variant** (never-published tasks) in the private store for
  independent verification — the defense against tuning against public tasks.
Generations rotate on a semi-annual cadence, retiring the most saturated tasks first.

## What a run records
Every run records the task `version`, the generation id, and the
`harness:{name,version,config_hash}` that produced it, so a leaderboard entry is always
traceable to an exact task+harness state.
