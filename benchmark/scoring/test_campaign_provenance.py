#!/usr/bin/env python3
"""Tests for campaign_provenance (G2 grading fusion)."""
import importlib.util
import json
import sys
from pathlib import Path

_p = Path(__file__).resolve().parent / "campaign_provenance.py"
_spec = importlib.util.spec_from_file_location("campaign_provenance_mod", _p)
_m = importlib.util.module_from_spec(_spec)
sys.modules["campaign_provenance_mod"] = _m
_spec.loader.exec_module(_m)
fuse_campaign = _m.fuse_campaign
backfill_from_score = _m.backfill_from_score
ProvenanceGraph = _m._agm.ProvenanceGraph


def _fake_campaign(ws: Path):
    (ws / "runs" / "diamond").mkdir(parents=True)
    (ws / "runs" / "diamond" / "espresso.pwi").write_text("&control\ncalculation='vc-relax'\n/")
    (ws / "runs" / "diamond" / "espresso.pwo").write_text("Quantum ESPRESSO\n!  total energy = -635.7 Ry")
    (ws / "report.md").write_text("# Methods\nDFT via QE.")
    (ws / "reported_values.json").write_text(json.dumps({"reported_values": {"V0": 20.47}}))


def test_fuse_builds_claim_to_input_chain(tmp_path):
    ws = tmp_path / "ws"; ws.mkdir()
    _fake_campaign(ws)
    summ = fuse_campaign(ws, model="claude-opus-4-8", task_id="T",
                         reported_values={"V0": 20.47}, units={"V0": "A^3/atom"},
                         anchors_passed={"V0": True})
    assert summ["claims"] == 1 and summ["runs"] == 1
    g = ProvenanceGraph(ws / "graph.jsonl")
    nodes, _ = g._load()
    claim = next(n for n in nodes.values() if n.get("@type") == "asw:Claim")
    res = g.query(claim["@id"])
    inputs = [a["node"] for a in res["ancestry"] if a["node"].get("role") == "input"]
    assert any(Path(i["path"]).name == "espresso.pwi" for i in inputs)   # walks to QE input
    runs = [a["node"] for a in res["ancestry"] if a["node"].get("@type") == "prov:Activity"]
    assert runs and runs[0]["tool"] == "quantum-espresso"                # tool inferred


def test_idempotent_rebuild(tmp_path):
    ws = tmp_path / "ws"; ws.mkdir()
    _fake_campaign(ws)
    a = fuse_campaign(ws, model="m", task_id="T", reported_values={"V0": 20.47})
    b = fuse_campaign(ws, model="m", task_id="T", reported_values={"V0": 20.47})
    assert a["nodes"] == b["nodes"] and a["edges"] == b["edges"]          # content-addressed dedup


def test_backfill_from_score(tmp_path):
    runroot = tmp_path / "rep1"; ws = runroot / "ws"; ws.mkdir(parents=True)
    _fake_campaign(ws)
    (runroot / "score.json").write_text(json.dumps(
        {"task_id": "T", "model": "claude-opus-4-8", "reported_values": {"V0": 20.47}}))
    summ = backfill_from_score(runroot)
    assert summ["claims"] == 1 and (ws / "graph.jsonl").exists()
