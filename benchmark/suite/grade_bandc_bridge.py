#!/usr/bin/env python3
"""
grade.py — Band C grading bridge (GENERIC tooling; no task content).

Same decomposed contract as Band B (mechanical anchors authoritative, judge
separate, C8) with the Band-C policy differences:

  * CONJUNCTIVE anchors: pass_mechanical_min comes from the sealed key's
    pass_policy (authored 1.0 — every anchor must land). A research commission
    with one wrong load-bearing number is a failed commission.
  * Process floor pass_judge_min also comes from the key (authored 0.6, higher
    than Band B's 0.5): a correct-but-hollow commission does not pass. The
    floor only tightens a passing anchor set; it never overturns a failed one.
  * Per-task spend ceiling defaults to the TASK's compute_budget (cost is a
    scored axis and every commission is budgeted), falling back to 15 USD.

Mechanical value EXTRACTION is judge-independent: the worker surfaces its
load-bearing numbers as the structured `reported_values` map whose keys the
task declares in `reporting_keys` (C2 — no number is produced by the grader).

STDLIB + the sibling harness modules. Author model: claude-fable-5 (C1).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_HARNESS = Path(__file__).resolve().parents[1] / "scoring"
sys.path.insert(0, str(_HARNESS))
from scoring import AnchorCheck, score_run  # noqa: E402

_DEFAULT_CEILING_USD = 15.0


def _make_extractor(anchor_name: str):
    """Judge-independent extractor: read the worker's reported value for this
    anchor from run_context['reported_values'][anchor_name]. Returns None if the
    worker never surfaced it (=> anchor FAILs: the load-bearing number is absent)."""
    def extract(ctx: dict):
        vals = ctx.get("reported_values") or {}
        v = vals.get(anchor_name)
        return float(v) if v is not None else None
    return extract


def load_task(task_id: str, private_root) -> dict:
    tf = Path(private_root) / "tasks" / "bandC" / f"{task_id}.json"
    if not tf.is_file():
        raise FileNotFoundError(f"no private task for {task_id} at {tf}")
    return json.loads(tf.read_text())


def load_key(task_id: str, private_root) -> dict:
    kf = Path(private_root) / "keys" / "bandC" / f"{task_id}.json"
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


def grade_bandC(task_id: str, result: dict, run_context: dict, *,
                private_root, judge=None, pricing=None,
                per_task_ceiling=None):
    """Grade one Band C run. ``result`` = executor result.json dict;
    ``run_context`` carries reported_values + artifacts_text + trace_digest for
    the judge. Pass thresholds come from the SEALED key's pass_policy (the
    authored conjunctive contract); the spend ceiling from the task's
    compute_budget unless overridden. Returns a decomposed RunScore."""
    key = load_key(task_id, private_root)
    policy = key.get("pass_policy") or {}
    if per_task_ceiling is None:
        try:
            per_task_ceiling = float(
                load_task(task_id, private_root)["compute_budget"]["spend_ceiling_usd"])
        except (FileNotFoundError, KeyError, TypeError, ValueError):
            per_task_ceiling = _DEFAULT_CEILING_USD
    return score_run(
        result, run_context,
        anchors=anchors_from_key(key), judge=judge, rubric=rubric_from_key(key),
        pricing=pricing, per_task_ceiling=per_task_ceiling,
        pass_mechanical_min=float(policy.get("pass_mechanical_min", 1.0)),
        pass_judge_min=(float(policy["pass_judge_min"])
                        if policy.get("pass_judge_min") is not None else 0.6))
