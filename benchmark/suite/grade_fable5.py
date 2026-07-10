#!/usr/bin/env python3
"""grade_fable5.py — grade a completed Fable-5 Band-C loop run and write
score.json in the rep dir (same record shape as the Opus calibration, plus
`model`). Reuses grade.py::grade_bandC (sealed key + mechanical anchors +
frozen judge). STDLIB only.

Usage: python3 grade_fable5.py BENCH-C-003 [--rep 1] [--tree bandC-fable5]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scoring"))
from grade_bandc_bridge import grade_bandC  # noqa: E402
from judge_openai import OpenAIJudge  # noqa: E402

PRIVATE = Path.home() / ".asw-suite-private"


def harvest(ws: Path) -> tuple[dict, dict, float, float, int]:
    """Pull result-shaped facts out of the loop transcript + workspace."""
    # total_cost_usd is CUMULATIVE within one claude process. Tick-loop trees:
    # one process per result -> sum totals. Native trees: one long process, init
    # fires per turn (NOT a process boundary) -> blocks split where the total
    # DECREASES (process restart); cost = sum of block finals.
    native = "native" in str(ws)
    totals: list = []
    wall = 0.0
    ticks = 0
    model = None
    for line in ws.joinpath("loop_transcript.jsonl").open():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "system" and ev.get("subtype") == "init":
            model = ev.get("model", model)
        if ev.get("type") == "result":
            ticks += 1
            if ev.get("total_cost_usd") is not None:
                totals.append(ev["total_cost_usd"])
            wall += (ev.get("duration_ms") or 0) / 1000.0
    if native:
        cost, prev = 0.0, None
        for v in totals:
            if prev is not None and v < prev:
                cost += prev
            prev = v
        cost += prev or 0.0
    else:
        cost = sum(totals)
    reported = {}
    rv = ws / "reported_values.json"
    if rv.is_file():
        reported = (json.loads(rv.read_text()) or {}).get("reported_values", {})
    report_text = ""
    rp = ws / "report.md"
    if rp.is_file():
        report_text = rp.read_text()[:30000]
    result = {"status": "done" if (ws / "TASK_DONE").exists() else "incomplete",
              "model": model, "cost_usd": cost, "wall_s": wall, "ticks": ticks}
    run_context = {"reported_values": reported, "artifacts_text": report_text,
                   "trace_digest": f"loop run, {ticks} ticks, ${cost:.2f}"}
    return result, run_context, cost, wall, ticks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("task_id")
    ap.add_argument("--rep", type=int, default=1)
    ap.add_argument("--tree", default="bandC-fable5")
    args = ap.parse_args()

    rep_dir = PRIVATE / "pilot-loop" / args.tree / args.task_id / f"rep{args.rep}"
    ws = rep_dir / "ws"
    result, ctx, cost, wall, ticks = harvest(ws)
    score = grade_bandC(args.task_id, result, ctx, private_root=PRIVATE,
                        judge=OpenAIJudge())

    rec = {
        "task_id": args.task_id, "rep": args.rep, "model": result["model"],
        "loop_status": "done" if result["status"] == "done" else "incomplete",
        "ticks": ticks,
        "verdict": score.verdict,
        "mechanical": score.mechanical,
        "anchors_passed": sum(1 for a in (score.anchors or []) if getattr(a, "passed", a.get("passed") if isinstance(a, dict) else False)),
        "n_anchors": len(score.anchors or []),
        "judge_score": getattr(score.judge, "score", None),
        "reported_values": ctx["reported_values"],
        "wall_s": round(wall, 1), "cost_usd": cost,
        "detail": score.detail,
    }
    (rep_dir / "score.json").write_text(json.dumps(rec, indent=1))
    print(json.dumps({k: rec[k] for k in
                      ("task_id", "model", "verdict", "anchors_passed",
                       "n_anchors", "judge_score", "cost_usd")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
