#!/usr/bin/env python3
"""
judge_openai.py — the frozen non-Anthropic judge (constitution C8).

Owner ruling (2026-07-06): the judge is OpenAI (non-Anthropic => satisfies the
anti-self-preference requirement; the author family here is Claude/Anthropic).
This module implements the `Judge` protocol from harness/scoring.py so it drops
straight into the decomposed scoring contract, with the mechanical anchors kept
SEPARATE and authoritative — the judge only scores rubric criteria the mechanical
layer cannot, and can NEVER overturn a failed anchor (enforced in scoring.py).

PINNED MODEL — recorded as provenance (C1: judge model pinned + recorded):

    JUDGE_MODEL = "gpt-5.5-2026-04-23"

Selection (2026-07-06, by querying the live OpenAI /v1/models with the owner's
key): the strongest STABLE, DATED (frozen — the bare `gpt-5.5` alias floats),
NON-preview, NON-pro GPT-5-class snapshot. The -pro tier (gpt-5.5-pro-2026-04-23)
is stronger still but is a reasoning-heavy, high-latency/cost product tier ill-
suited to a HIGH-VOLUME grading role (every run, two-judge panel on Band C); it
is recorded as the optional max-capability panel member, pending a cost check.
Smoke-verified via a grading-shaped call before first use (see JUDGE_PROVENANCE.md).

KEY HANDLING — the repo is PUBLIC. The API key is NEVER written into any repo
file, config, test, or commit. It is read at RUNTIME from OPENAI_API_KEY, else
from the owner's off-repo path (default ~/.config/asw/openai_judge.key or $ASW_JUDGE_KEY_PATH,
perms 600). Only the PATH/env name ever appears in code — never the value.

GRADING SURFACE — artifacts + trace only. Unlike v1's grader (which roamed the
agent's workspace WITH tool access — an un-audited prompt-injection surface,
RD-05), this judge receives a bounded text bundle (the final result + selected
artifacts + a trace digest) and returns a JSON verdict. No tools, no filesystem.

STDLIB + requests only. Author model: claude-fable-5 (provenance per C1).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

import requests

# Import the contract types (JudgeVerdict) from the sibling scoring module.
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from scoring import JudgeVerdict  # noqa: E402

# --- PINNED JUDGE PROVENANCE (constitution C1) ----------------------------
JUDGE_MODEL = "gpt-5.5-2026-04-23"
JUDGE_PANEL_PRO = "gpt-5.5-pro-2026-04-23"  # optional max-capability panel member
DEFAULT_KEY_PATH = os.path.expanduser(
    os.environ.get("ASW_JUDGE_KEY_PATH", "~/.config/asw/openai_judge.key"))
_API_URL = "https://api.openai.com/v1/chat/completions"


def load_judge_key(key_path: str | None = None) -> str:
    """Return the judge API key. Prefers OPENAI_API_KEY (runtime env), else reads
    the off-repo key file. NEVER logs or returns anything derived that could echo
    the value elsewhere. Raises a clear error (no value) if unavailable."""
    env = os.environ.get("OPENAI_API_KEY")
    if env:
        return env.strip()
    path = Path(key_path or DEFAULT_KEY_PATH)
    if path.is_file():
        return path.read_text().strip()
    raise RuntimeError(
        "judge key not found: set OPENAI_API_KEY or place it at "
        f"{path} (perms 600). The key is never stored in the repo.")


def build_grading_prompt(run_context: dict, rubric: dict) -> tuple[str, str]:
    """Compose (system, user) messages from the run bundle + rubric. The bundle
    is bounded text: the worker's final result, selected artifact excerpts, and a
    trace digest. Returns messages; the model must reply with strict JSON."""
    criteria = rubric.get("criteria", [])
    crit_lines = "\n".join(
        f"  - [{c.get('id','?')}] (weight {c.get('weight',1)}) {c.get('text','')}"
        for c in criteria) or "  (no criteria provided)"

    result = run_context.get("result", {})
    final = result.get("final_result") or run_context.get("final_result") or ""
    artifacts = run_context.get("artifacts_text", "")
    trace_digest = run_context.get("trace_digest", "")

    system = (
        "You are a STRICT, impartial scientific grader for an autonomous "
        "computational-materials researcher. You grade ONLY the rubric criteria "
        "given, using ONLY the evidence bundle provided (final answer, artifact "
        "excerpts, trace digest). You do not have tools and must not assume "
        "anything not in the bundle. Reward correct science and honest "
        "uncertainty; penalize unsupported claims, missing provenance, and "
        "right-answer-wrong-path. Reply with STRICT JSON only, no prose outside "
        "it: {\"score\": <0..1>, \"per_criterion\": {<id>: <0..1>, ...}, "
        "\"reason\": \"<=80 words\"}. score is the weighted mean of per_criterion.")

    user = (
        f"RUBRIC CRITERIA:\n{crit_lines}\n\n"
        f"=== WORKER FINAL ANSWER ===\n{final[:6000]}\n\n"
        f"=== ARTIFACT EXCERPTS ===\n{artifacts[:8000]}\n\n"
        f"=== TRACE DIGEST (tool calls / method path) ===\n{trace_digest[:4000]}\n\n"
        "Grade now. STRICT JSON only.")
    return system, user


@dataclass
class OpenAIJudge:
    """Frozen OpenAI judge implementing the Judge protocol (scoring.Judge)."""
    model: str = JUDGE_MODEL
    key_path: str | None = None
    timeout_s: int = 180
    _post = staticmethod(requests.post)  # injectable for tests

    def grade(self, run_context: dict, rubric: dict) -> JudgeVerdict:
        try:
            key = load_judge_key(self.key_path)
        except Exception as e:
            return JudgeVerdict(model=self.model, score=None, status="error",
                                reasoning=f"key unavailable: {e}")
        system, user = build_grading_prompt(run_context, rubric)
        body = {"model": self.model,
                "messages": [{"role": "system", "content": system},
                             {"role": "user", "content": user}]}
        try:
            r = self._post(_API_URL, headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"}, json=body,
                timeout=self.timeout_s)
        except Exception as e:
            return JudgeVerdict(model=self.model, score=None, status="error",
                                reasoning=f"request failed: {e!r}")
        if getattr(r, "status_code", None) != 200:
            body_txt = getattr(r, "text", "")[:300]
            return JudgeVerdict(model=self.model, score=None, status="error",
                                reasoning=f"HTTP {getattr(r,'status_code','?')}: {body_txt}")
        try:
            content = r.json()["choices"][0]["message"]["content"]
            parsed = _parse_json(content)
            score = float(parsed["score"])
            if not (0.0 <= score <= 1.0):
                raise ValueError(f"score {score} out of [0,1]")
        except Exception as e:
            return JudgeVerdict(model=self.model, score=None, status="error",
                                reasoning=f"unparseable judge reply: {e!r}")
        return JudgeVerdict(
            model=self.model, score=score, status="ok",
            reasoning=str(parsed.get("reason", ""))[:500],
            panel=[{"id": k, "score": v}
                   for k, v in (parsed.get("per_criterion", {}) or {}).items()])


def _parse_json(text: str) -> dict:
    """Parse a JSON object from a model reply, tolerating code fences / stray
    prose by extracting the first {...} block."""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        i, j = text.find("{"), text.rfind("}")
        if i != -1 and j != -1 and j > i:
            return json.loads(text[i:j + 1])
        raise
