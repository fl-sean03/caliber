#!/usr/bin/env python3
"""
grade.py — Band B grading bridge (GENERIC tooling; no task content).

Loads a task's SEALED KEY from the off-repo store, builds the decomposed scoring
inputs (mechanical AnchorChecks from the sealed ranges + the judge rubric), and
scores a run bundle via harness/scoring.score_run with the frozen OpenAI judge.

Decomposition is enforced upstream (scoring.py): the mechanical anchors are
judge-INDEPENDENT and AUTHORITATIVE — the judge cannot overturn a failed anchor
(C8). Mechanical value EXTRACTION is also judge-independent: the worker is
expected to surface its load-bearing numbers as a structured `reported_values`
map (same convention as v1 `expected_outputs.values`); the extractor reads that
map, never the judge (C2 — no number is produced by the grader).

STDLIB + the sibling harness modules. Author model: claude-fable-5 (C1).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_HARNESS = Path(__file__).resolve().parents[2] / "harness"
sys.path.insert(0, str(_HARNESS))
from scoring import AnchorCheck, score_run  # noqa: E402


def _make_extractor(anchor_name: str):
    """Judge-independent extractor: read the worker's reported value for this
    anchor from run_context['reported_values'][anchor_name]. Returns None if the
    worker never surfaced it (=> anchor FAILs: the load-bearing number is absent)."""
    def extract(ctx: dict):
        vals = ctx.get("reported_values") or {}
        v = vals.get(anchor_name)
        return float(v) if v is not None else None
    return extract


def load_key(task_id: str, private_root) -> dict:
    kf = Path(private_root) / "keys" / "bandB" / f"{task_id}.json"
    if not kf.is_file():
        raise FileNotFoundError(f"no sealed key for {task_id} at {kf}")
    return json.loads(kf.read_text())


def anchors_from_key(key: dict) -> list[AnchorCheck]:
    out = []
    for a in key.get("anchors", []) or []:
        out.append(AnchorCheck(
            name=a["name"], extractor=_make_extractor(a["name"]),
            lo=float(a["lo"]), hi=float(a["hi"]),
            weight=float(a.get("weight", 1.0)), unit=a.get("unit", "")))
    return out


def rubric_from_key(key: dict) -> dict:
    return key.get("judge_rubric", {"criteria": []})


def grade_bandB(task_id: str, result: dict, run_context: dict, *,
                private_root, judge=None, pricing=None, per_task_ceiling=8.0,
                pass_judge_min=0.5):
    """Grade one Band B run. ``result`` = executor result.json dict; ``run_context``
    carries reported_values + artifacts_text + trace_digest for the judge. Returns
    a decomposed RunScore (mechanical ⊕ judge, kept separate).

    ``pass_judge_min`` defaults to 0.5: Band B's whole point is method RIGOR, so a
    correct-but-hollow run (right number, no justification/uncertainty/provenance)
    does NOT pass. The floor only tightens a passing anchor; it never overturns a
    failed one (C8). Set to None to score anchors-only."""
    key = load_key(task_id, private_root)
    return score_run(
        result, run_context,
        anchors=anchors_from_key(key), judge=judge, rubric=rubric_from_key(key),
        pricing=pricing, per_task_ceiling=per_task_ceiling,
        pass_judge_min=pass_judge_min)
