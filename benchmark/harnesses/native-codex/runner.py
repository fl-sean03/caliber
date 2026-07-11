#!/usr/bin/env python3
"""
native-codex runner — OpenAI Codex CLI adapter (evidence-contract compliant).

Codex's native headless pattern is `codex exec`: the CLI runs its OWN agentic
loop (tools, edits, commands) in the workspace until the task completes — no
external session-holding or re-invocation needed. This adapter therefore just:
spawns `codex exec` with the goal in the task workspace, streams all output to
`transcript.log` (capture-first), enforces an external wall cap (kill never
lands mid-oracle since oracles are grader-side), detects the TASK_DONE
sentinel, and records harness provenance {name, version, model, config_hash}.

Max-effort discipline: pass the model + reasoning effort explicitly via -c
overrides so "max effort" is REAL and recorded (screening validity depends on
it). STDLIB only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
import time
from pathlib import Path

HARNESS_NAME = "native-codex"


def run(goal: str, *, workspace: str, model: str = "gpt-5.6-terra",
        effort: str = "ultra", max_wall_s: int = 21600,
        sentinel: str = "TASK_DONE") -> dict:
    ws = Path(workspace)
    ws.mkdir(parents=True, exist_ok=True)
    sent = ws / sentinel
    if sent.exists():
        sent.unlink()
    transcript = ws / "transcript.log"

    version = subprocess.run(["codex", "--version"], capture_output=True,
                             text=True).stdout.strip()
    argv = ["codex", "exec",
            "--dangerously-bypass-approvals-and-sandbox",
            "-c", f"model={model}",
            "-c", f"model_reasoning_effort={effort}",
            "--cd", str(ws),
            goal]
    config = {"model": model, "reasoning_effort": effort, "argv": argv[:-1]}
    config_hash = hashlib.sha256(
        json.dumps(config, sort_keys=True).encode()).hexdigest()[:12]

    t0 = time.monotonic()
    with transcript.open("a") as out:
        out.write(json.dumps({"harness": HARNESS_NAME, "version": version,
                              "config": config, "config_hash": config_hash,
                              "goal_sha": hashlib.sha256(goal.encode()).hexdigest()[:12]}) + "\n")
        out.flush()
        proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=out,
                                stderr=subprocess.STDOUT, text=True,
                                start_new_session=True)
        while True:
            rc = proc.poll()
            if rc is not None:
                break
            if time.monotonic() - t0 > max_wall_s:
                os.killpg(proc.pid, signal.SIGKILL)
                rc = -9
                break
            time.sleep(10)

    wall = time.monotonic() - t0
    status = "done" if sent.exists() else ("wall_exhausted" if rc == -9 else "ended_without_sentinel")
    return {"harness": HARNESS_NAME, "harness_version": version,
            "config_hash": config_hash, "model": model, "effort": effort,
            "status": status, "rc": rc, "wall_s": round(wall, 1)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--goal-file", required=True)
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--model", default="gpt-5.6-terra")
    ap.add_argument("--effort", default="ultra")
    ap.add_argument("--max-wall-s", type=int, default=21600)
    a = ap.parse_args()
    out = run(Path(a.goal_file).read_text(), workspace=a.workspace,
              model=a.model, effort=a.effort, max_wall_s=a.max_wall_s)
    print(json.dumps(out))
    return 0 if out["status"] == "done" else 1


if __name__ == "__main__":
    raise SystemExit(main())
