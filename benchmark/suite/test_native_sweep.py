#!/usr/bin/env python3
"""Tests for suite/native_sweep.py per-task wall-clock resolution.

All fixtures are SYNTHETIC — invented task ids ("TEST-W-00") and invented
wall values; nothing here mirrors any real task's sealed content.
Author model: claude-fable-5."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_sweep import (  # noqa: E402
    DEFAULT_WALL_S, manifest_wall_h, resolve_wall_s,
)


def task(**kw):
    base = {"id": "TEST-W-00", "band": "C", "prompt": "synthetic"}
    base.update(kw)
    return base


# ---- manifest_wall_h: the shapes that exist in the wild --------------------

def test_canonical_environment_contract_shape():
    # The shape every real Caliber-1 task manifest uses (verified 2026-07-15).
    t = task(environment_contract={"allowed": [], "wall_clock_h": 42})
    assert manifest_wall_h(t) == (42.0, "environment_contract.wall_clock_h")


def test_top_level_shape():
    t = task(wall_clock_h=7)
    assert manifest_wall_h(t) == (7.0, "wall_clock_h")


def test_environment_contract_budget_nested_shape():
    t = task(environment_contract={"budget": {"type": "x", "wall_clock_h": 11}})
    assert manifest_wall_h(t) == (11.0, "environment_contract.budget.wall_clock_h")


def test_top_level_budget_nested_shape():
    t = task(budget={"wall_clock_h": 13})
    assert manifest_wall_h(t) == (13.0, "budget.wall_clock_h")


def test_canonical_shape_wins_over_others():
    t = task(wall_clock_h=1,
             environment_contract={"wall_clock_h": 42,
                                   "budget": {"wall_clock_h": 2}},
             budget={"wall_clock_h": 3})
    assert manifest_wall_h(t) == (42.0, "environment_contract.wall_clock_h")


def test_absent_field():
    assert manifest_wall_h(task()) == (None, "")


def test_fractional_and_string_numeric_hours_accepted():
    assert manifest_wall_h(task(environment_contract={"wall_clock_h": 0.5}))[0] == 0.5
    assert manifest_wall_h(task(environment_contract={"wall_clock_h": "36"}))[0] == 36.0


def test_unparseable_values_flagged_not_crashed():
    for bad in ("soon", None, [96], 0, -4, float("nan")):
        hours, path = manifest_wall_h(task(environment_contract={"wall_clock_h": bad}))
        assert hours is None
        assert path == "environment_contract.wall_clock_h"


def test_non_dict_containers_tolerated():
    # environment_contract / budget may be malformed entirely.
    assert manifest_wall_h(task(environment_contract="broken")) == (None, "")
    assert manifest_wall_h(task(environment_contract={"budget": "broken"})) == (None, "")
    assert manifest_wall_h(task(budget=[1, 2])) == (None, "")


# ---- resolve_wall_s: precedence CLI > manifest > default -------------------

def test_cli_override_beats_manifest():
    t = task(environment_contract={"wall_clock_h": 96})
    wall, why = resolve_wall_s(1234, t)
    assert wall == 1234
    assert why == "cli --max-wall-s"


def test_manifest_beats_default():
    t = task(environment_contract={"wall_clock_h": 96})
    wall, why = resolve_wall_s(None, t)
    assert wall == 96 * 3600
    assert why == "manifest environment_contract.wall_clock_h=96h"


def test_default_when_manifest_silent():
    wall, why = resolve_wall_s(None, task())
    assert wall == DEFAULT_WALL_S
    assert "no wall_clock_h" in why


def test_default_when_manifest_unparseable():
    wall, why = resolve_wall_s(None, task(environment_contract={"wall_clock_h": "soon"}))
    assert wall == DEFAULT_WALL_S
    assert "unparseable" in why
    assert "environment_contract.wall_clock_h" in why


def test_fractional_hours_round_to_int_seconds():
    wall, _ = resolve_wall_s(None, task(wall_clock_h=1.5))
    assert wall == 5400
    assert isinstance(wall, int)
