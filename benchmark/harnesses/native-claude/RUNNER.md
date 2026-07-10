# Runner — native session-holder (`asw_native.py`)

**Status:** ADOPTED 2026-07-10, replacing the `asw_loop.py` tick-cadence supervisor
for benchmark/calibration runs. `asw_loop.py` is retired (kept only for reference).

## Why the change

`asw_loop.py` re-invoked the worker on a ~30s cadence via `claude -p --resume`,
**even while a simulation was still running**. Each re-invocation re-read the whole
accumulated session (cache-read tokens grew to ~1.9M/tick). On long tasks this
dominated cost: BENCH-C-006 spent ~$49 across 97 working ticks where ~10 real
compute cycles were needed. It also burned its fixed tick budget on rejected calls
during account rate-limit windows, turning outages into DNFs.

## The mechanism (empirically verified 2026-07-10)

`claude -p --input-format stream-json` with **stdin held open** natively re-wakes
the agent when a background Bash task completes — no polling. The runner therefore:

1. spawns ONE pinned session per task (`--model`, `--config-dir` = account pin),
2. sends the goal, then **holds stdin open** and streams the event trace to
   `loop_transcript.jsonl` (unchanged evidence contract),
3. lets the worker launch long compute with `run_in_background` and YIELD; the
   background completion wakes it to harvest — zero token cost while the sim runs,
4. enforces budgets EXTERNALLY (wall cap; a trip never kills running compute),
5. closes stdin when the worker writes the `TASK_DONE` sentinel.

Stall/outage recovery: idle nudges fire on **exponential backoff** (900s·2^n,
capped 2h), never on a cadence, and are non-fatal — only the wall cap ends a run.

Verified: launch → yield → (background sim) → auto-wake → harvest in 2 turns.
Clean cost example — BENCH-C-002 (Si phase transition): **$8.41 native vs $25.56
old-loop**, same PASS 3/3.

## Cost accounting (important)

`total_cost_usd` in the stream is **cumulative within a single `claude` process**,
not per-turn. The native runner emits many `result` events from ONE process, so
cost = the LAST cumulative value per process block (blocks split where the value
decreases = process restart). The old tick loop ran one process per tick, so its
cost = sum of per-tick totals. `native_audit.py` and `grade_fable5.py` both branch
on tree name (`native` in path) to apply the correct rule. Summing native totals
per-turn was the phantom-cost bug (2026-07-10); do not reintroduce it.

## Files

- `asw_native.py` — the runner (CLI + importable `run()`).
- `../suite/native_sweep.py` — capped-concurrency sweep driver over the sealed
  task set; follows the fleet-active account at each spawn; requeues rate-limited
  runs; no spend ceilings (record actual cost).
- `../suite/native_audit.py` — per-run forensic audit (wake pattern, cost anatomy,
  cache growth, background-task usage, stalls, artifact/model integrity) with
  anomaly flags tuned to catch tick-loop-style regressions.
- `../suite/bandC/grade_fable5.py` — grade a completed native/loop Band-C run
  (sealed anchors + frozen judge) into the standard `score.json` record.
