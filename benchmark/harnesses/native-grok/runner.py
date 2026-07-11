#!/usr/bin/env python3
"""
native-grok runner — xAI Grok CLI adapter (evidence-contract compliant).

Grok's native headless pattern is `grok -p "<goal>"`: the CLI runs its own
agentic loop in the cwd until completion. The adapter spawns it in the task
workspace, streams output to `transcript.log`, enforces an external wall cap,
detects the TASK_DONE sentinel, and records harness provenance
{name, version, model, config_hash}. Max-effort settings are passed explicitly
and recorded. STDLIB only.
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

HARNESS_NAME = "native-grok"


def run(goal: str, *, workspace: str, model: str = "grok-4.5",
        max_wall_s: int = 21600, sentinel: str = "TASK_DONE") -> dict:
    ws = Path(workspace)
    ws.mkdir(parents=True, exist_ok=True)
    sent = ws / sentinel
    if sent.exists():
        sent.unlink()
    transcript = ws / "transcript.log"

    version = subprocess.run(["grok", "--version"], capture_output=True,
                             text=True).stdout.strip()
    argv = ["grok", "-p", goal, "--model", model, "--yolo"]
    config = {"model": model, "argv": argv[:1] + argv[2:]}  # goal elided
    config_hash = hashlib.sha256(
        json.dumps(config, sort_keys=True).encode()).hexdigest()[:12]

    t0 = time.monotonic()
    with transcript.open("a") as out:
        out.write(json.dumps({"harness": HARNESS_NAME, "version": version,
                              "config": config, "config_hash": config_hash,
                              "goal_sha": hashlib.sha256(goal.encode()).hexdigest()[:12]}) + "\n")
        out.flush()
        proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=out,
                                stderr=subprocess.STDOUT, text=True, cwd=str(ws),
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
            "config_hash": config_hash, "model": model,
            "status": status, "rc": rc, "wall_s": round(wall, 1)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--goal-file", required=True)
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--model", default="grok-4.5")
    ap.add_argument("--max-wall-s", type=int, default=21600)
    a = ap.parse_args()
    out = run(Path(a.goal_file).read_text(), workspace=a.workspace,
              model=a.model, max_wall_s=a.max_wall_s)
    print(json.dumps(out))
    return 0 if out["status"] == "done" else 1


if __name__ == "__main__":
    raise SystemExit(main())
