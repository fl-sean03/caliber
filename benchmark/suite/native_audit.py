#!/usr/bin/env python3
"""
native_audit.py — per-run deep audit for the native session-holder runner.

For one rep dir, reconstructs HOW the run executed (not just whether it passed):
wake pattern, cost anatomy, cache growth, nudges, rate-limit events, background
task usage, sentinel/artifact integrity. Purpose (owner directive 2026-07-10):
catch remaining architecture problems while the re-sweep runs, not after.

Prints one JSON record; --brief prints a one-line human summary too.
STDLIB only.  Usage: python3 native_audit.py <rep_dir> [--brief]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

NUDGE_MARK = "harvest any finished jobs"


def audit(rep_dir: Path) -> dict:
    ws = rep_dir / "ws"
    tr = ws / "loop_transcript.jsonl"
    rec: dict = {"rep_dir": str(rep_dir), "flags": []}
    if not tr.is_file():
        rec["flags"].append("NO_TRANSCRIPT")
        return rec

    # COST SEMANTICS (2026-07-10 phantom-cost bug): total_cost_usd is CUMULATIVE
    # within one claude process. Old tick-loop = one process per tick (one result
    # each) -> SUM all totals. Native session-holder = one long process emitting
    # many results (init fires per TURN, so init is NOT a process boundary) ->
    # blocks split where the cumulative total DECREASES (process restart), cost =
    # sum of block finals.
    native = "native" in str(rep_dir)
    totals: list[float] = []
    turns = 0
    out_tokens = 0
    cache_reads = []
    bg_launches = 0
    monitors = 0
    fg_sleeps = 0
    nudges = 0
    rejections = 0
    models = set()
    errors = 0
    for line in tr.open():
        try:
            ev = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        t = ev.get("type")
        if t == "system" and ev.get("subtype") == "init":
            if ev.get("model"):
                models.add(ev["model"])
        elif t == "rate_limit_event":
            if (ev.get("rate_limit_info") or {}).get("status") == "rejected":
                rejections += 1
        elif t == "result":
            turns += 1
            if ev.get("total_cost_usd") is not None:
                totals.append(ev["total_cost_usd"])
            if ev.get("is_error"):
                errors += 1
            u = ev.get("usage") or {}
            out_tokens += u.get("output_tokens") or 0
            cache_reads.append(u.get("cache_read_input_tokens") or 0)
        elif t == "assistant":
            for b in (ev.get("message") or {}).get("content") or []:
                if b.get("type") == "tool_use" and b.get("name") == "Bash":
                    inp = b.get("input") or {}
                    cmd = str(inp.get("command", ""))
                    if inp.get("run_in_background"):
                        bg_launches += 1
                    elif cmd.strip().startswith("sleep") or "; sleep" in cmd[:200]:
                        fg_sleeps += 1
                elif b.get("type") == "tool_use" and b.get("name") == "Monitor":
                    monitors += 1
        elif t == "user":
            for b in (ev.get("message") or {}).get("content") or []:
                if b.get("type") == "text" and NUDGE_MARK in str(b.get("text", "")):
                    nudges += 1

    if native:
        cost, prev = 0.0, None
        for v in totals:
            if prev is not None and v < prev:
                cost += prev          # process restarted: bank finished block
            prev = v
        cost += prev or 0.0
    else:
        cost = sum(totals)            # tick loop: one process per result
    rec.update({
        "turns": turns, "cost_usd": round(cost, 4), "output_tokens": out_tokens,
        "cache_read_total_M": round(sum(cache_reads) / 1e6, 2),
        "cache_read_max_M": round(max(cache_reads) / 1e6, 2) if cache_reads else 0,
        "bg_launches": bg_launches, "monitors": monitors, "fg_sleeps": fg_sleeps,
        "nudges": nudges, "rejections": rejections, "error_turns": errors,
        "models": sorted(models),
        "task_done": (ws / "TASK_DONE").exists(),
        "has_report": (ws / "report.md").exists(),
        "has_values": (ws / "reported_values.json").exists(),
        "has_workflow": (ws / "WORKFLOW.md").exists(),
    })
    # anomaly flags — each one is a "look here" for the architecture audit
    if turns > 25:
        rec["flags"].append(f"MANY_WAKES({turns})")          # wake pattern regressing toward tick-loop
    if rec["cache_read_max_M"] > 3.0:
        rec["flags"].append("HUGE_CONTEXT")                  # session bloat: worker not keeping state lean
    if fg_sleeps > 2:
        rec["flags"].append(f"FG_SLEEPS({fg_sleeps})")       # worker polling in foreground = wasted turns
    if nudges > 2:
        rec["flags"].append(f"STALLS({nudges})")             # runner had to rescue repeatedly
    if rejections:
        rec["flags"].append(f"RATE_LIMITED({rejections})")
    if rec["task_done"] and not (rec["has_report"] and rec["has_values"]):
        rec["flags"].append("DONE_WITHOUT_ARTIFACTS")        # sentinel discipline violation
    if len(rec["models"]) > 1:
        rec["flags"].append("MODEL_MIX")                     # provenance violation
    if turns and cost / max(turns, 1) > 3.0:
        rec["flags"].append("EXPENSIVE_TURNS")
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("rep_dir")
    ap.add_argument("--brief", action="store_true")
    a = ap.parse_args()
    rec = audit(Path(a.rep_dir))
    print(json.dumps(rec))
    if a.brief:
        name = "/".join(Path(a.rep_dir).parts[-2:])
        print(f"AUDIT {name}: {rec.get('turns','?')} wakes ${rec.get('cost_usd','?')} "
              f"bg={rec.get('bg_launches','?')} nudges={rec.get('nudges','?')} "
              f"flags={','.join(rec['flags']) or 'CLEAN'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
