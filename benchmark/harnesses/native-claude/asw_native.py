#!/usr/bin/env python3
"""
asw_native.py — native session-holder runner (replaces asw_loop's tick cadence).

EMPIRICAL BASIS (2026-07-10, memory: native-wake-replaces-tick-loop):
`claude -p --input-format stream-json` with stdin HELD OPEN natively re-wakes
the agent when a background Bash task completes — verified launch→yield→wake→
harvest in 2 turns / $0.40. So the runner's job shrinks to: spawn ONE pinned
session per task, feed the goal, hold stdin, capture the event stream
(unchanged evidence contract), enforce budgets EXTERNALLY (a budget trip can
never tear down running compute mid-simulation), and close stdin when the
worker writes the TASK_DONE sentinel.

Fallback nudges exist ONLY for stall recovery (worker ended turn with no
sentinel, no pending work visible) and rate-limit outages — they fire on
multi-minute idle detection, not on a cadence.

STDLIB only. CLI + importable.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

NUDGE = (
    "Continue the task. Read {ws}/WORKFLOW.md first; harvest any finished jobs; "
    "never restart work already recorded. When the ENTIRE commission is complete "
    "and verified, write report.md and reported_values.json and run: touch "
    "{ws}/TASK_DONE"
)


@dataclass
class RunOutcome:
    status: str            # done | wall_exhausted | error | rate_limited
    wakes: int             # completed turns (result events)
    wall_s: float
    total_cost_usd: float
    session_id: str | None
    reason: str = ""


def _reader(proc, transcript_path: Path, state: dict, lock: threading.Lock):
    """Stream stdout line-by-line to the transcript (capture-first rule) and
    fold key facts into shared state."""
    with transcript_path.open("a") as out:
        for line in proc.stdout:
            out.write(line)
            out.flush()
            try:
                ev = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            with lock:
                state["last_event_t"] = time.monotonic()
                t = ev.get("type")
                if t == "system" and ev.get("subtype") == "init":
                    state["session_id"] = ev.get("session_id", state.get("session_id"))
                elif t == "result":
                    state["turns"] = state.get("turns", 0) + 1
                    # total_cost_usd is CUMULATIVE per session/process — assign, never sum
                    # (summing was the 2026-07-10 phantom-cost bug caught by native_audit)
                    if ev.get("total_cost_usd") is not None:
                        state["cost"] = ev["total_cost_usd"]
                    state["last_result_error"] = bool(ev.get("is_error"))
                    state["turn_open"] = False
                elif t == "rate_limit_event":
                    ri = ev.get("rate_limit_info") or {}
                    state["rate_limited"] = ri.get("status") == "rejected"
                    if ri.get("resetsAt"):
                        state["rl_resets_at"] = ri["resetsAt"]
                elif t in ("assistant", "user"):
                    state["turn_open"] = True


def run(goal: str, *, workspace: str | os.PathLike, worker_cwd: str,
        model: str, config_dir: str | None = None,
        sentinel: str = "TASK_DONE", max_wall_s: int = 43200,
        idle_nudge_s: int = 900, max_nudges: int = 20,
        poll_s: float = 5.0) -> RunOutcome:
    ws = Path(workspace)
    ws.mkdir(parents=True, exist_ok=True)
    sent = ws / sentinel
    if sent.exists():
        sent.unlink()
    transcript = ws / "loop_transcript.jsonl"
    transcript.touch()

    env = dict(os.environ)
    env.pop("ANTHROPIC_API_KEY", None)   # OAuth account only (memory: env key overrides OAuth)
    if config_dir:
        env["CLAUDE_CONFIG_DIR"] = config_dir

    argv = ["claude", "-p", "--model", model, "--permission-mode", "bypassPermissions",
            "--input-format", "stream-json", "--output-format", "stream-json", "--verbose"]
    proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, text=True, cwd=worker_cwd,
                            env=env, start_new_session=True)

    state: dict = {"last_event_t": time.monotonic(), "turn_open": True}
    lock = threading.Lock()
    rt = threading.Thread(target=_reader, args=(proc, transcript, state, lock), daemon=True)
    rt.start()

    def send(text: str) -> bool:
        msg = json.dumps({"type": "user",
                          "message": {"role": "user",
                                      "content": [{"type": "text", "text": text}]}})
        try:
            proc.stdin.write(msg + "\n")
            proc.stdin.flush()
            return True
        except (BrokenPipeError, ValueError, OSError):
            return False

    send(goal)
    t0 = time.monotonic()
    nudges = 0
    status, reason = "error", "unknown"

    while True:
        time.sleep(poll_s)
        wall = time.monotonic() - t0
        with lock:
            cost = state.get("cost", 0.0)
            idle = time.monotonic() - state["last_event_t"]
            turn_open = state.get("turn_open", False)
            rate_limited = state.get("rate_limited", False)

        if sent.exists():
            status, reason = "done", f"sentinel {sentinel} present"
            break
        if proc.poll() is not None:
            status, reason = "error", f"worker exited rc={proc.returncode} without sentinel"
            break
        if wall > max_wall_s:
            status, reason = "wall_exhausted", f"wall {wall:.0f}s > {max_wall_s}s"
            break
        # Stall / outage recovery only — NOT a cadence, and NEVER fatal.
        # Exponential backoff (idle_nudge_s * 2^n, capped at 2h): long-running
        # sims with quiet output gaps must not accumulate nudges into a death
        # sentence (the C-009/C-005 rep1 bug, 2026-07-10). Only the wall cap
        # ends a run.
        cur_thresh = min(idle_nudge_s * (2 ** nudges), 7200)
        if idle > cur_thresh and not turn_open:
            nudges += 1
            if not send(NUDGE.format(ws=ws)):
                status, reason = "error", "stdin closed (worker gone)"
                break
            with lock:
                state["last_event_t"] = time.monotonic()
                state["turn_open"] = True
            if rate_limited and nudges >= max_nudges:
                status, reason = "rate_limited", f"persistent rejections after {nudges} nudges"
                break

    try:
        proc.stdin.close()
    except OSError:
        pass
    try:
        proc.wait(timeout=60)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)

    with lock:
        return RunOutcome(status=status, wakes=state.get("turns", 0),
                          wall_s=time.monotonic() - t0,
                          total_cost_usd=state.get("cost", 0.0),
                          session_id=state.get("session_id"), reason=reason)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Native session-holder benchmark runner.")
    ap.add_argument("--goal-file", required=True)
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--worker-cwd", default=os.getcwd(),
                    help="cwd for the worker session (default: current dir)")
    ap.add_argument("--model", default="claude-fable-5")
    ap.add_argument("--config-dir", default=None, help="CLAUDE_CONFIG_DIR for the worker (account pin)")
    ap.add_argument("--max-wall-s", type=int, default=43200)
    ap.add_argument("--idle-nudge-s", type=int, default=900)
    ap.add_argument("--max-nudges", type=int, default=20)
    a = ap.parse_args(argv)
    goal = Path(a.goal_file).read_text()
    out = run(goal, workspace=a.workspace, worker_cwd=a.worker_cwd, model=a.model,
              config_dir=a.config_dir, max_wall_s=a.max_wall_s,
              idle_nudge_s=a.idle_nudge_s, max_nudges=a.max_nudges)
    print(json.dumps(vars(out)))
    return 0 if out.status == "done" else 1


if __name__ == "__main__":
    raise SystemExit(main())
