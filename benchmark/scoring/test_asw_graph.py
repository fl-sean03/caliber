#!/usr/bin/env python3
"""Tests for asw_graph — the provenance write-path (G1)."""
import importlib.util
import json
import sys
from pathlib import Path

_p = Path(__file__).resolve().parent / "asw_graph.py"
_spec = importlib.util.spec_from_file_location("asw_graph_mod", _p)
_m = importlib.util.module_from_spec(_spec)
sys.modules["asw_graph_mod"] = _m
_spec.loader.exec_module(_m)
ProvenanceGraph = _m.ProvenanceGraph


def test_artifact_content_addressed_and_dedup(tmp_path):
    f = tmp_path / "scf.in"; f.write_text("&control\n calculation='scf'\n/")
    g = ProvenanceGraph(tmp_path / "graph.jsonl")
    a1 = g.artifact(f, role="qe-input")
    a2 = g.artifact(f, role="qe-input")          # same content → same id, no dup line
    assert a1 == a2 and a1.startswith("art:")
    lines = (tmp_path / "graph.jsonl").read_text().splitlines()
    assert sum(1 for L in lines if json.loads(L).get("@id") == a1) == 1
    # different content → different id
    f2 = tmp_path / "other.in"; f2.write_text("different")
    assert g.artifact(f2) != a1


def test_claim_derives_from_run_which_used_input(tmp_path):
    """ACCEPTANCE (Fable G2): from a graded Claim, walk mechanically to the exact
    QE input artifact that produced it."""
    ws = tmp_path
    (ws / "scf.in").write_text("ecutwfc=50\nK_POINTS 12 12 12")
    (ws / "scf.out").write_text("!    total energy = -635.75 Ry")
    g = ProvenanceGraph(ws / "graph.jsonl")
    agent = g.agent("claude-opus-4-8", harness="asw_loop", config_hash="abc123")
    in_id = g.artifact(ws / "scf.in", role="qe-input")
    out_id = g.artifact(ws / "scf.out", role="qe-output")
    run_id = g.run("quantum-espresso", label="diamond-scf", used=[in_id],
                   agent=agent, cost_usd=0.1, wall_s=30, exit_code=0)
    g.edge(out_id, "prov:wasGeneratedBy", run_id)
    claim_id = g.claim("V0_diamond_A3", 20.47, units="A^3/atom",
                       method="Birch-Murnaghan EOS", derived_from=[out_id, run_id])

    res = g.query(claim_id)
    anc_ids = {a["node"]["@id"] for a in res["ancestry"]}
    # the walk must reach the run, its output, AND the exact input file + the agent
    assert run_id in anc_ids
    assert out_id in anc_ids
    assert in_id in anc_ids          # ← the exact QE input, reached mechanically
    assert agent in anc_ids
    # and the input node carries its sha256 (verifiable)
    in_node = next(a["node"] for a in res["ancestry"] if a["node"]["@id"] == in_id)
    assert len(in_node["sha256"]) == 64


def test_persistence_and_reload(tmp_path):
    gp = tmp_path / "g.jsonl"
    g = ProvenanceGraph(gp)
    h = g.hypothesis("beta-tin is denser than diamond Si")
    g2 = ProvenanceGraph(gp)                     # reload from disk
    assert h in g2._ids                          # id index rebuilt
    g2.claim("dE", 289.9, units="meV/atom")      # append continues cleanly
    assert g2.summary()["nodes"] >= 2


def test_summary_counts_by_type(tmp_path):
    g = ProvenanceGraph(tmp_path / "g.jsonl")
    (tmp_path / "x").write_text("a")
    g.artifact(tmp_path / "x")
    g.run("qe")
    g.claim("k", 1.0)
    s = g.summary()
    assert s["by_type"]["prov:Entity"] == 1
    assert s["by_type"]["prov:Activity"] == 1
    assert s["by_type"]["asw:Claim"] == 1


def test_bad_types_rejected(tmp_path):
    g = ProvenanceGraph(tmp_path / "g.jsonl")
    try:
        g.edge("a", "prov:bogusRel", "b"); assert False
    except ValueError:
        pass


def test_cli_roundtrip(tmp_path):
    gp = str(tmp_path / "g.jsonl")
    (tmp_path / "out.dat").write_text("result")
    main = _m.main
    assert main(["--graph", gp, "artifact", str(tmp_path / "out.dat"), "--role", "output"]) == 0
    assert main(["--graph", gp, "run", "--tool", "lammps", "--label", "md"]) == 0
    assert main(["--graph", gp, "claim", "--key", "kappa", "--value", "1.5", "--units", "W/mK"]) == 0
    assert main(["--graph", gp, "summary"]) == 0
    recs = [json.loads(L) for L in Path(gp).read_text().splitlines()]
    assert any(r.get("@type") == "asw:Claim" and r.get("value") == 1.5 for r in recs)
