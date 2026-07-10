#!/usr/bin/env python3
"""
inspect_bridge.py — wrap the ASW executor + scorer as UK-AISI Inspect components.

REBUILD_PLAN §4.5 / PROPOSAL §6: wrap the executor as an Inspect solver so
logging / stats / cost accounting come standard. Inspect is EVAL-SIDE tooling
(Task = dataset + solver + scorer); it does not thicken the agent, so it does
not violate the thin-agent thesis. The executor's `_stream_events` capture seam
is unchanged — Inspect wraps it, it does not replace it.

LAZY DEPENDENCY. `inspect_ai` is NOT a hard requirement (it is not installed on
this machine today). This module imports it only when you actually build the
Inspect Task; everything importable without it is pure mapping logic that we can
test now. When `pip install inspect-ai` lands, the same code lights up unchanged.

Author model: claude-fable-5 (provenance per constitution C1).
"""

from __future__ import annotations

from typing import Any, Optional


class InspectNotInstalled(RuntimeError):
    """Raised when an Inspect-requiring entry point is called but inspect_ai is
    absent. Fail LOUD with a fix, never silently degrade."""
    def __init__(self):
        super().__init__(
            "inspect_ai is not installed. `pip install inspect-ai` to enable the "
            "Inspect bridge (PROPOSAL §6). The pure mapping helpers in this module "
            "(task_to_sample, run_to_inspect_score) work without it.")


def inspect_available() -> bool:
    try:
        import inspect_ai  # noqa: F401
        return True
    except Exception:
        return False


# ==========================================================================
# Pure mapping helpers — testable WITHOUT inspect_ai
# ==========================================================================

def task_to_sample(task: dict) -> dict:
    """Map an ASW task record to an Inspect Sample's fields (dict form, so it is
    testable without importing inspect_ai; the binding below wraps it in the real
    Sample type). ASW task carries id + prompt + optional metadata (band, source
    cluster, canary, anchors-key ref)."""
    if "id" not in task or "prompt" not in task:
        raise ValueError("task needs at least 'id' and 'prompt'")
    return {
        "id": task["id"],
        "input": task["prompt"],
        "metadata": {
            "band": task.get("band"),
            "cluster": task.get("cluster"),      # for clustered SEs
            "canary": task.get("canary"),        # private-tier provenance
            "anchors_ref": task.get("anchors_ref"),  # off-repo sealed-key handle
            "time_limit_s": task.get("time_limit_s"),
        },
    }


def run_to_inspect_score(run_score) -> dict:
    """Map an ASW RunScore (harness/scoring.py) to an Inspect Score's fields.
    VOID maps to a NOANSWER-style value that Inspect metrics can exclude from the
    denominator (F1: infra failure is not a capability score). PASS/FAIL map to
    the canonical Inspect CORRECT/INCORRECT letters ('C'/'I')."""
    verdict = getattr(run_score, "verdict", None)
    if verdict == "VOID":
        value = "N"  # NOANSWER — excluded from capability denominators
    elif verdict == "PASS":
        value = "C"  # CORRECT
    else:
        value = "I"  # INCORRECT
    return {
        "value": value,
        "answer": run_score.detail,
        "explanation": run_score.void_reason or run_score.detail,
        "metadata": {
            "mechanical": run_score.mechanical,
            "judge_score": run_score.judge.score,
            "judge_model": run_score.grader_model,   # frozen, non-Anthropic
            "cost_usd_ti": run_score.cost.cost_usd_time_invariant,
            "cost_usd_reported": run_score.cost.cost_usd_reported,
            "wall_s": run_score.cost.wall_s,
            "over_ceiling": run_score.cost.over_ceiling,
            "model": run_score.model,                 # executor model (pinned)
        },
    }


# ==========================================================================
# Inspect bindings — require inspect_ai (lazy import inside)
# ==========================================================================

def build_samples(tasks: list[dict]):
    """Turn ASW task records into Inspect Samples. Requires inspect_ai."""
    try:
        from inspect_ai.dataset import Sample
    except Exception:
        raise InspectNotInstalled()
    return [Sample(id=s["id"], input=s["input"], metadata=s["metadata"])
            for s in (task_to_sample(t) for t in tasks)]


def asw_solver(cfg=None, workspaces_root=None):
    """An Inspect solver that runs one task through the ASW executor (full-trace
    capture into the evidence store) and stashes the resulting `result` +
    run_context on the Inspect state for the scorer. Requires inspect_ai."""
    try:
        from inspect_ai.solver import solver, TaskState, Generate
    except Exception:
        raise InspectNotInstalled()

    import executor  # local import: harness/ on path

    @solver
    def _asw():
        async def solve(state: "TaskState", generate: "Generate") -> "TaskState":
            prompt = state.input_text
            task_id = str(state.sample_id)
            result = executor.execute_task(
                task_id, prompt, cfg=cfg,
                workspaces_root=workspaces_root or executor.DEFAULT_WORKSPACES)
            state.metadata["asw_result"] = result
            state.metadata["asw_run_context"] = {
                "result": result, "workspace": result.get("run_dir")}
            return state
        return solve
    return _asw()


def asw_scorer(anchors_loader=None, judge=None, pricing=None, per_task_ceiling=None):
    """An Inspect scorer that applies the decomposed ASW scoring contract
    (harness/scoring.py) to the run stashed by asw_solver. Mechanical anchors and
    the frozen judge stay SEPARATE (C8). Requires inspect_ai.

    ``anchors_loader``: (task_id) -> list[AnchorCheck] from the OFF-REPO sealed
    keys — never in the repo (charter §1.3)."""
    try:
        from inspect_ai.scorer import scorer, Score, accuracy, stderr
    except Exception:
        raise InspectNotInstalled()

    import scoring  # local import

    @scorer(metrics=[accuracy(), stderr()])
    def _asw_scorer():
        async def score(state, target) -> "Score":
            result = state.metadata.get("asw_result", {})
            ctx = state.metadata.get("asw_run_context", {"result": result})
            task_id = str(state.sample_id)
            anchors = anchors_loader(task_id) if anchors_loader else []
            rs = scoring.score_run(
                result, ctx, anchors=anchors, judge=judge,
                pricing=pricing, per_task_ceiling=per_task_ceiling)
            mapped = run_to_inspect_score(rs)
            return Score(value=mapped["value"], answer=mapped["answer"],
                         explanation=mapped["explanation"],
                         metadata=mapped["metadata"])
        return score
    return _asw_scorer()


def build_task(tasks: list[dict], *, anchors_loader=None, judge=None,
               pricing=None, per_task_ceiling=None, cfg=None):
    """Assemble the full Inspect Task = dataset + ASW solver + ASW scorer.
    Requires inspect_ai. This is the single entry point a runner calls."""
    try:
        from inspect_ai import Task
        from inspect_ai.dataset import MemoryDataset
    except Exception:
        raise InspectNotInstalled()
    return Task(
        dataset=MemoryDataset(build_samples(tasks)),
        solver=asw_solver(cfg=cfg),
        scorer=asw_scorer(anchors_loader=anchors_loader, judge=judge,
                          pricing=pricing, per_task_ceiling=per_task_ceiling),
    )
