#!/usr/bin/env python3
"""Tests for harness/scoring.py (decomposed VOID-aware scoring) and
harness/inspect_bridge.py (pure mapping helpers, no inspect_ai needed).
Author model: claude-fable-5."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scoring import (  # noqa: E402
    is_void, AnchorCheck, check_anchors, mechanical_subtotal, score_run,
    NullJudge, JudgeVerdict, time_invariant_cost, cost_score,
    PASS, FAIL, VOID,
)
import inspect_bridge as ib  # noqa: E402


# ---- VOID gate (Phase-0 F1) ---------------------------------------------

def test_is_void_on_is_error():
    v, r = is_void({"is_error": True})
    assert v and "infra" in r


def test_is_void_on_invalid():
    v, r = is_void({"invalid": True, "invalid_reason": "empty transcript"})
    assert v and "empty transcript" in r


def test_is_void_on_empty_events():
    assert is_void({"n_events": 0})[0] is True


def test_timeout_is_not_void():
    # a hang is a capability failure, not infra (MISSION); must NOT be voided
    assert is_void({"status": "ok", "timed_out": True, "n_events": 5})[0] is False


def test_clean_run_not_void():
    assert is_void({"status": "ok", "n_events": 10})[0] is False


# ---- mechanical anchors (C2/C8) -----------------------------------------

def _ctx(values):
    return {"values": values}

def _extract(key):
    return lambda ctx: ctx["values"].get(key)


def test_anchor_in_range_passes():
    a = AnchorCheck("Tmean", _extract("T"), lo=0.99, hi=1.01, unit="")
    res = check_anchors(_ctx({"T": 0.9968}), [a])
    assert res[0].passed is True


def test_anchor_out_of_range_fails():
    a = AnchorCheck("Tmean", _extract("T"), lo=0.99, hi=1.01)
    res = check_anchors(_ctx({"T": 1.5}), [a])
    assert res[0].passed is False and "OUT of" in res[0].detail


def test_anchor_missing_value_fails_not_errors():
    a = AnchorCheck("Tmean", _extract("absent"), lo=0, hi=1)
    res = check_anchors(_ctx({}), [a])
    assert res[0].passed is False and "absent" in res[0].detail


def test_broken_extractor_does_not_crash_grading():
    def boom(ctx):
        raise RuntimeError("bad extractor")
    res = check_anchors(_ctx({}), [AnchorCheck("x", boom, 0, 1)])
    assert res[0].passed is False and "extractor error" in res[0].detail


def test_mechanical_subtotal_weighted():
    results = check_anchors(_ctx({"a": 1.0, "b": 5.0}), [
        AnchorCheck("a", _extract("a"), 0, 2, weight=3.0),   # pass
        AnchorCheck("b", _extract("b"), 0, 2, weight=1.0),   # fail
    ])
    # 3 of 4 weight passed
    assert mechanical_subtotal(results) == pytest.approx(0.75)


def test_mechanical_subtotal_none_without_anchors():
    assert mechanical_subtotal([]) is None


# ---- cost axis (F4) ------------------------------------------------------

def test_time_invariant_cost_recomputes_from_tokens():
    usage = {"input_tokens": 1000, "output_tokens": 500}
    pricing = {"input": 3e-6, "output": 15e-6}
    # 1000*3e-6 + 500*15e-6 = 0.003 + 0.0075 = 0.0105
    assert time_invariant_cost(usage, pricing) == pytest.approx(0.0105)


def test_cost_score_flags_over_ceiling():
    cs = cost_score({"cost_usd": 12.0, "wall_s": 4000, "usage": {}},
                    pricing=None, per_task_ceiling=8.0)
    assert cs.over_ceiling is True
    assert cs.cost_usd_reported == 12.0


def test_cost_score_under_ceiling_ok():
    cs = cost_score({"cost_usd": 2.0, "usage": {}}, per_task_ceiling=8.0)
    assert cs.over_ceiling is False


# ---- decomposed score_run -----------------------------------------------

def test_score_run_void_short_circuits():
    rs = score_run({"is_error": True, "task_id": "T1"}, {},
                   anchors=[AnchorCheck("x", lambda c: 1.0, 0, 2)])
    assert rs.verdict == VOID
    assert rs.mechanical is None          # not scored
    assert rs.judge.status == "not_run"


def test_score_run_pass_on_anchors():
    result = {"task_id": "T1", "status": "ok", "n_events": 5,
              "cost_usd": 1.0, "usage": {}, "model": "opus"}
    ctx = {"values": {"T": 0.9968}}
    rs = score_run(result, ctx,
                   anchors=[AnchorCheck("T", _extract("T"), 0.99, 1.01)])
    assert rs.verdict == PASS
    assert rs.mechanical == pytest.approx(1.0)


def test_score_run_fail_on_anchor_judge_cannot_overturn():
    # judge loves it, but a failed anchor is authoritative (C8)
    class LovingJudge:
        model = "frozen-external-x"
        def grade(self, ctx, rubric):
            return JudgeVerdict(model=self.model, score=1.0, status="ok")
    result = {"task_id": "T1", "status": "ok", "n_events": 5, "usage": {}}
    ctx = {"values": {"T": 99.0}}  # wildly out of range
    rs = score_run(result, ctx,
                   anchors=[AnchorCheck("T", _extract("T"), 0.99, 1.01)],
                   judge=LovingJudge())
    assert rs.verdict == FAIL              # anchor wins
    assert rs.judge.score == 1.0           # judge still reported, separately


def test_score_run_defers_to_judge_when_no_anchors():
    class J:
        model = "frozen-external-x"
        def grade(self, ctx, rubric):
            return JudgeVerdict(model=self.model, score=0.8, status="ok")
    result = {"task_id": "T1", "status": "ok", "n_events": 5, "usage": {}}
    rs = score_run(result, {}, anchors=[], judge=J())
    assert rs.verdict == PASS and rs.mechanical is None


def test_score_run_failsafe_when_nothing_scored():
    result = {"task_id": "T1", "status": "ok", "n_events": 5, "usage": {}}
    rs = score_run(result, {}, anchors=[], judge=NullJudge())
    assert rs.verdict == FAIL and "fail-safe" in rs.detail


# ---- inspect_bridge pure mapping (no inspect_ai) ------------------------

def test_task_to_sample_maps_fields():
    s = ib.task_to_sample({"id": "B-001", "prompt": "do X",
                           "band": "B", "cluster": "AgCu", "canary": "TEST-CANARY-x"})
    assert s["id"] == "B-001" and s["input"] == "do X"
    assert s["metadata"]["band"] == "B" and s["metadata"]["cluster"] == "AgCu"


def test_task_to_sample_requires_id_and_prompt():
    with pytest.raises(ValueError):
        ib.task_to_sample({"id": "x"})


def test_run_to_inspect_score_void_is_noanswer():
    rs = score_run({"is_error": True, "task_id": "T1"}, {})
    mapped = ib.run_to_inspect_score(rs)
    assert mapped["value"] == "N"          # excluded from capability denominator


def test_run_to_inspect_score_pass_is_correct():
    result = {"task_id": "T1", "status": "ok", "n_events": 5, "usage": {}}
    rs = score_run(result, {"values": {"T": 1.0}},
                   anchors=[AnchorCheck("T", _extract("T"), 0.9, 1.1)])
    assert ib.run_to_inspect_score(rs)["value"] == "C"


def test_build_task_raises_clear_error_without_inspect():
    if ib.inspect_available():
        pytest.skip("inspect_ai present; the not-installed path is not exercised")
    with pytest.raises(ib.InspectNotInstalled):
        ib.build_task([{"id": "x", "prompt": "y"}])
