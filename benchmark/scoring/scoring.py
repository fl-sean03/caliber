#!/usr/bin/env python3
"""
scoring.py — the decomposed, VOID-aware scoring contract (grader seam).

This is the SEAM the executor left open (build_result: `grader` stub,
`grader_model: null`; RD-203). It does NOT decide scientific content (rubrics,
anchor ranges, the judge's identity) — those wait on the owner ruling
(PROPOSAL §8). It defines the CONTRACT every grader must honor, enforced by the
constitution:

  * C8 — grading DECOMPOSED: the mechanical-anchor verdict is computed and
    reported SEPARATELY from any LLM judge; the judge is NOT of the author family.
  * C2 — no load-bearing number hand-transcribed: mechanical anchors read the
    value from the run's own artifacts.
  * Phase-0 F1 — infra failure is never a capability score: an is_error/invalid
    run is VOID on every axis, excluded from denominators.
  * F4 — cost is a first-class axis, priced time-invariantly so it is comparable
    across models and over time.

The frozen non-Anthropic judge is a PROTOCOL here (Judge) with a NullJudge
default; the real judge is wired once the owner pins the model (§8.1) and it is
calibrated to the human gold set at kappa>=0.8.

STDLIB ONLY. Author model: claude-fable-5 (provenance per constitution C1).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional, Protocol


# Verdicts. VOID is not a capability outcome — it means "this run does not count."
PASS, FAIL, VOID, DNF = "PASS", "FAIL", "VOID", "DNF"


# ==========================================================================
# VOID gate — infra failure is never a capability score (Phase-0 F1)
# ==========================================================================

def is_void(result: dict) -> tuple[bool, str]:
    """True iff a run must be VOIDed (infra failure, not capability). Mirrors the
    generator fix (generate_status.py): is_error/invalid runs are unscored, never
    score-0. Timeout is NOT void — a hang is a capability failure (MISSION), a
    distinct bucket. Returns (void, reason)."""
    if result.get("is_error") is True:
        return True, "is_error: session errored (infra), not a capability outcome"
    if result.get("invalid") is True:
        return True, f"invalid run: {result.get('invalid_reason', 'unspecified')}"
    if result.get("status") in ("error", "crashed"):
        return True, f"status={result.get('status')}: infra failure"
    if result.get("n_events", 1) == 0:
        return True, "empty transcript: nothing captured (rule 2)"
    return False, ""


# ==========================================================================
# Mechanical anchors — judge-independent numeric checks (C2, C8)
# ==========================================================================

@dataclass
class AnchorCheck:
    """One mechanical anchor: a load-bearing quantity extracted from the run's
    artifacts, checked against a sealed range. The extractor reads the value from
    the workspace/result (NEVER hand-transcribed, C2); the range is the sealed
    key (off-repo). weight lets a task's anchors sum to its mechanical subtotal."""
    name: str
    extractor: Callable[[dict], Optional[float]]  # (run_context) -> value or None
    lo: float
    hi: float
    weight: float = 1.0
    unit: str = ""


@dataclass
class AnchorResult:
    name: str
    value: Optional[float]
    lo: float
    hi: float
    passed: bool
    weight: float
    detail: str


def check_anchors(run_context: dict, anchors: list[AnchorCheck]) -> list[AnchorResult]:
    """Evaluate each anchor against the run context (artifacts/result). A missing
    value (extractor returns None) is a FAIL, not an error — the worker failed to
    produce the load-bearing number."""
    out = []
    for a in anchors:
        try:
            v = a.extractor(run_context)
        except Exception as e:  # a broken extractor must not crash grading
            out.append(AnchorResult(a.name, None, a.lo, a.hi, False, a.weight,
                                    f"extractor error: {e!r}"))
            continue
        if v is None:
            out.append(AnchorResult(a.name, None, a.lo, a.hi, False, a.weight,
                                    "value absent from artifacts"))
            continue
        ok = a.lo <= v <= a.hi
        out.append(AnchorResult(a.name, v, a.lo, a.hi, ok, a.weight,
                                f"{v}{(' '+a.unit) if a.unit else ''} "
                                f"{'in' if ok else 'OUT of'} [{a.lo}, {a.hi}]"))
    return out


def mechanical_subtotal(results: list[AnchorResult]) -> Optional[float]:
    """Weighted fraction of anchors passed, in [0,1]. None if there are no
    anchors (a task may be judge-only). Reported SEPARATELY from the judge (C8)."""
    if not results:
        return None
    total_w = sum(r.weight for r in results)
    if total_w == 0:
        return None
    return sum(r.weight for r in results if r.passed) / total_w


# ==========================================================================
# Frozen non-Anthropic judge — protocol + null default (C8, §8.1)
# ==========================================================================

@dataclass
class JudgeVerdict:
    model: Optional[str]       # the frozen judge's exact pinned id (or None)
    score: Optional[float]     # rubric score in [0,1], or None if not run
    status: str                # "not_run" | "ok" | "error"
    reasoning: str = ""
    panel: list = field(default_factory=list)  # per-judge scores if a panel


class Judge(Protocol):
    """A grader that scores rubric criteria the mechanical layer cannot. MUST NOT
    be of the author family (C8 — here the author is Claude/Anthropic, so the
    judge must be non-Anthropic). Grades artifacts + trace."""
    model: str
    def grade(self, run_context: dict, rubric: dict) -> JudgeVerdict: ...


class NullJudge:
    """Default judge: runs nothing. Keeps grading honest before the real frozen
    judge is pinned (§8.1) — a run scored with NullJudge carries score=None and
    status=not_run, never a fabricated number."""
    model = None
    def grade(self, run_context: dict, rubric: dict) -> JudgeVerdict:
        return JudgeVerdict(model=None, score=None, status="not_run",
                            reasoning="no frozen judge pinned yet (PROPOSAL §8.1)")


# ==========================================================================
# Cost axis — time-invariant pricing (F4)
# ==========================================================================

@dataclass
class CostScore:
    cost_usd_reported: Optional[float]     # what the CLI reported (not time-invariant)
    cost_usd_time_invariant: Optional[float]  # recomputed under the frozen table
    wall_s: Optional[float]
    over_ceiling: bool                     # did it breach the per-task spend ceiling?
    reference_usd: Optional[float] = None  # sealed per-task reference budget (median)
    efficiency: Optional[float] = None     # min(1, reference/actual) in [0,1]; mechanical (F4)


def cost_efficiency(actual: Optional[float],
                    reference: Optional[float]) -> Optional[float]:
    """Mechanical cost-efficiency (F4): ``min(1, reference/actual)`` in [0,1].
    1.0 = at or under the sealed reference budget; 0.5 = 2x budget; 0.25 = 4x.
    Judge-independent by construction (rep1 proved the judge won't penalize a $19
    run). None if either value is unknown."""
    if actual is None or reference is None or actual <= 0:
        return None
    return min(1.0, reference / actual)


def time_invariant_cost(usage: dict, pricing: dict) -> Optional[float]:
    """Recompute $ from token usage under a FROZEN pricing table so cost is
    comparable across models and over time (F4). ``pricing`` maps a token class
    to $/token, e.g. {"input": 3e-6, "output": 15e-6, "cache_read": 3e-7}. Tokens
    absent from usage contribute 0. Returns None if usage is empty."""
    if not usage:
        return None
    total = 0.0
    matched = False
    for cls, rate in pricing.items():
        toks = usage.get(cls) or usage.get(f"{cls}_tokens")
        if toks is not None:
            total += float(toks) * float(rate)
            matched = True
    return total if matched else None


def cost_score(result: dict, pricing: Optional[dict] = None,
               per_task_ceiling: Optional[float] = None,
               reference_usd: Optional[float] = None) -> CostScore:
    reported = result.get("cost_usd")
    ti = time_invariant_cost(result.get("usage") or {}, pricing) if pricing else None
    basis = ti if ti is not None else reported
    over = bool(per_task_ceiling is not None and basis is not None
                and basis > per_task_ceiling)
    eff = cost_efficiency(basis, reference_usd)
    return CostScore(reported, ti, result.get("wall_s"), over, reference_usd, eff)


# ==========================================================================
# The decomposed run score — the single object a grader returns
# ==========================================================================

@dataclass
class RunScore:
    task_id: str
    run_id: Optional[str]
    verdict: str                       # PASS | FAIL | VOID
    void_reason: str
    mechanical: Optional[float]        # weighted anchor fraction [0,1] or None
    anchors: list                      # list[AnchorResult]
    judge: JudgeVerdict                # kept SEPARATE from mechanical (C8)
    cost: CostScore
    model: Optional[str]               # executor model (pinned)
    grader_model: Optional[str]        # judge model (frozen, non-Anthropic)
    detail: str = ""

    def as_dict(self) -> dict:
        return {
            "task_id": self.task_id, "run_id": self.run_id,
            "verdict": self.verdict, "void_reason": self.void_reason,
            "mechanical": self.mechanical,
            "anchors": [vars(a) for a in self.anchors],
            "judge": vars(self.judge),
            "cost": vars(self.cost),
            "model": self.model, "grader_model": self.grader_model,
            "detail": self.detail,
        }


def score_run(result: dict, run_context: dict,
              anchors: Optional[list[AnchorCheck]] = None,
              judge: Optional[Judge] = None,
              rubric: Optional[dict] = None,
              pricing: Optional[dict] = None,
              per_task_ceiling: Optional[float] = None,
              pass_mechanical_min: float = 1.0,
              pass_judge_min: Optional[float] = None,
              reference_cost: Optional[float] = None) -> RunScore:
    """Produce the decomposed score for one run.

    Order matters: (1) VOID gate FIRST — an infra failure never gets a capability
    verdict (F1). (2) mechanical anchors (C2/C8), reported separately. (3) frozen
    judge (C8), separately. (4) cost axis (F4).

    ``pass_mechanical_min``: fraction of mechanical weight required to PASS on the
    mechanical component (default 1.0 = every anchor must land). The judge score
    is reported but the mechanical PASS/FAIL is judge-INDEPENDENT by design — a
    task with no anchors defers its verdict to the judge (verdict reflects judge
    score>=0.5 as a placeholder threshold the owner can override per rubric).

    ``pass_judge_min``: OPTIONAL process floor (default None = off). When set and a
    judge ran, a run that cleared its anchors STILL fails unless the judge process
    score >= this floor. This encodes "grade != effort": a correct-but-hollow run
    (right number, no verification/uncertainty/provenance) is caught. Crucially
    this only ever makes grading STRICTER — it NEVER lets the judge overturn a
    FAILED anchor (C8): the floor is applied on top of an already-passing anchor.

    This function computes the SEPARATED components; a suite-level policy decides
    how to combine them, but never by letting the judge overturn a failed anchor.
    """
    void, reason = is_void(result)
    judge = judge or NullJudge()
    cost = cost_score(result, pricing, per_task_ceiling, reference_usd=reference_cost)

    if void:
        return RunScore(
            task_id=result.get("task_id", "?"), run_id=result.get("run_id"),
            verdict=VOID, void_reason=reason, mechanical=None, anchors=[],
            judge=JudgeVerdict(model=judge.model, score=None, status="not_run",
                               reasoning="run VOID — not graded"),
            cost=cost, model=result.get("model"), grader_model=judge.model,
            detail="VOID: infra failure excluded from denominators (F1)")

    # DNF gate: a run that RAN but did not COMPLETE in budget/wall (loop
    # budget_exhausted / no TASK_DONE) is a distinct RELIABILITY failure — a real
    # capability signal (the model over-spent and never finished), NOT a wrong-answer
    # FAIL and NOT an infra VOID. Counts against pass^k but is labelled distinctly.
    if result.get("did_not_finish") is True:
        dnf_anchors = check_anchors(run_context, anchors or [])
        return RunScore(
            task_id=result.get("task_id", "?"), run_id=result.get("run_id"),
            verdict=DNF, void_reason="", mechanical=mechanical_subtotal(dnf_anchors),
            anchors=dnf_anchors,
            judge=JudgeVerdict(model=judge.model, score=None, status="not_run",
                               reasoning="run DNF — did not finish in budget"),
            cost=cost, model=result.get("model"), grader_model=judge.model,
            detail="DNF: did not finish in budget (loop budget_exhausted) — "
                   "reliability/cost failure, distinct from a correctness FAIL")

    anchor_results = check_anchors(run_context, anchors or [])
    mech = mechanical_subtotal(anchor_results)
    jv = judge.grade(run_context, rubric or {})

    # verdict: mechanical is authoritative when present (judge cannot overturn a
    # failed anchor, C8); else defer to judge; else UNGRADED->FAIL-safe.
    if mech is not None:
        verdict = PASS if mech >= pass_mechanical_min else FAIL
        detail = f"mechanical {mech:.3f} vs min {pass_mechanical_min}"
        # process floor: only tightens a PASS, never rescues a failed anchor (C8)
        if (verdict == PASS and pass_judge_min is not None
                and jv.status == "ok" and jv.score is not None
                and jv.score < pass_judge_min):
            verdict = FAIL
            detail += (f"; FAILED process floor (judge {jv.score:.3f} "
                       f"< {pass_judge_min}) — correct-but-hollow")
    elif jv.score is not None:
        verdict = PASS if jv.score >= 0.5 else FAIL
        detail = f"judge-only {jv.score:.3f} (no anchors); owner sets threshold per rubric"
    else:
        verdict = FAIL
        detail = "no anchors and no judge score — nothing scored (fail-safe)"

    return RunScore(
        task_id=result.get("task_id", "?"), run_id=result.get("run_id"),
        verdict=verdict, void_reason="", mechanical=mech, anchors=anchor_results,
        judge=jv, cost=cost, model=result.get("model"), grader_model=judge.model,
        detail=detail)
