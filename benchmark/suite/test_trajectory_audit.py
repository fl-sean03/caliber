#!/usr/bin/env python3
"""Tests for suite/trajectory_audit.py (retrieval-vs-derivation audit,
environment sealing v1). All contract fixtures are SYNTHETIC — invented
system names ("fictitium carbide Fx3C") and invented values; nothing here
mirrors any real task's sealed content. Author model: claude-fable-5."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from trajectory_audit import (  # noqa: E402
    Contract, ContractError, audit_transcript, load_contract, main,
    resolve_transcript, CLEAN, SUSPECT, VIOLATION, INFO,
)

# ---- synthetic fixtures ---------------------------------------------------

CONTRACT_DATA = {
    "task_id": "TEST-00",
    "allowed_patterns": [r"(?i)docs\.example-sim\.org"],
    "blocked_patterns": [r"(?i)materialsproject\.org", r"(?i)oqmd\.org"],
    "lookup_phrases": [
        r"(?i)fictitium carbide",
        {"pattern": r"(?i)Fx3C", "label": "target system", "severity": "violation"},
    ],
    "target_values": [{"key": "Ef_eV", "value": 7.34, "rel_window": 0.02}],
    "provenance_rel_tol": 0.005,
}


@pytest.fixture
def contract():
    return Contract(dict(CONTRACT_DATA))


def tool_use(name, inp, tid):
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": tid, "name": name, "input": inp}]}}


def tool_result(tid, text):
    return {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": tid,
         "content": [{"type": "text", "text": text}]}]}}


def write_jsonl(tmp_path, events, name="transcript.jsonl"):
    p = tmp_path / name
    p.write_text("\n".join(json.dumps(e) for e in events) + "\n")
    return p


def codes(rec, severity=None):
    return {f["code"] for f in rec["findings"]
            if severity is None or f["severity"] == severity}


# ---- pass 1: tool-surface scan --------------------------------------------

def test_clean_derivation_run(tmp_path, contract):
    # the agent's OWN scripts legitimately name the target system — no flag
    tr = write_jsonl(tmp_path, [
        tool_use("Bash", {"command": "python compute_Fx3C.py --ecut 60"}, "t1"),
        tool_result("t1", "converged. Ef = 7.3412 eV"),
    ])
    rec = audit_transcript(tr, contract, {"Ef_eV": 7.34})
    assert rec["verdict"] == CLEAN
    assert rec["findings"] == []
    assert rec["tool_calls"] == 1 and rec["retrieval_calls"] == 0


def test_blocked_database_tool_is_violation(tmp_path, contract):
    tr = write_jsonl(tmp_path, [
        tool_use("WebFetch", {"url": "https://materialsproject.org/materials/x"}, "t1"),
    ])
    rec = audit_transcript(tr, contract)
    assert rec["verdict"] == VIOLATION
    assert "BLOCKED_SURFACE" in codes(rec, VIOLATION)


def test_blocked_surface_via_bash_curl(tmp_path, contract):
    tr = write_jsonl(tmp_path, [
        tool_use("Bash", {"command": "curl -s https://oqmd.org/api/search"}, "t1"),
    ])
    rec = audit_transcript(tr, contract)
    assert rec["verdict"] == VIOLATION
    assert "BLOCKED_SURFACE" in codes(rec, VIOLATION)


def test_unlisted_retrieval_is_suspect(tmp_path, contract):
    tr = write_jsonl(tmp_path, [
        tool_use("WebFetch", {"url": "https://docs.python.org/3/library/json.html"}, "t1"),
    ])
    rec = audit_transcript(tr, contract)
    assert rec["verdict"] == SUSPECT
    assert "UNLISTED_RETRIEVAL" in codes(rec, SUSPECT)


def test_allowed_surface_is_info_only(tmp_path, contract):
    tr = write_jsonl(tmp_path, [
        tool_use("WebFetch", {"url": "https://docs.example-sim.org/input-flags"}, "t1"),
        tool_result("t1", "The ecutwfc flag sets the wavefunction cutoff."),
    ])
    rec = audit_transcript(tr, contract)
    assert rec["verdict"] == CLEAN
    assert "ALLOWED_SURFACE" in codes(rec, INFO)


# ---- pass 2: lookup-phrase scan --------------------------------------------

def test_target_phrase_in_search_query_is_violation(tmp_path, contract):
    tr = write_jsonl(tmp_path, [
        tool_use("WebSearch", {"query": "fictitium carbide formation energy DFT"}, "t1"),
    ])
    rec = audit_transcript(tr, contract)
    assert rec["verdict"] == VIOLATION
    v = [f for f in rec["findings"] if f["code"] == "LOOKUP_PHRASE"]
    assert v and v[0]["severity"] == VIOLATION
    assert "fictitium carbide" in v[0]["context"].lower()  # context captured


def test_phrase_severity_override_to_suspect(tmp_path):
    data = dict(CONTRACT_DATA)
    data["lookup_phrases"] = [
        {"pattern": r"(?i)fictitium", "label": "analogue", "severity": "suspect"}]
    tr = write_jsonl(tmp_path, [
        tool_use("WebSearch", {"query": "fictitium alloys review"}, "t1"),
    ])
    rec = audit_transcript(tr, Contract(data))
    assert rec["verdict"] == SUSPECT
    assert "LOOKUP_PHRASE" in codes(rec, SUSPECT)


def test_target_phrase_in_fetched_output_is_suspect(tmp_path, contract):
    # allowed docs fetch whose CONTENT mentions the target → adjudicate
    tr = write_jsonl(tmp_path, [
        tool_use("WebFetch", {"url": "https://docs.example-sim.org/faq"}, "t1"),
        tool_result("t1", "Example study: properties of Fx3C under pressure."),
    ])
    rec = audit_transcript(tr, contract)
    assert rec["verdict"] == SUSPECT
    assert "LOOKUP_PHRASE_OUTPUT" in codes(rec, SUSPECT)


def test_phrase_in_local_computation_not_flagged(tmp_path, contract):
    tr = write_jsonl(tmp_path, [
        tool_use("Write", {"file_path": "notes.md", "content": "Fx3C relax plan"}, "t1"),
        tool_use("Bash", {"command": "grep 'Fx3C' relax.out"}, "t2"),
        tool_result("t2", "Fx3C cell relaxed, E = -412.7 Ry"),
    ])
    rec = audit_transcript(tr, contract)
    assert rec["verdict"] == CLEAN


# ---- pass 3: numeric proximity (SUSPECT-only, redacted) ---------------------

def test_numeric_proximity_in_retrieval_output(tmp_path, contract):
    tr = write_jsonl(tmp_path, [
        tool_use("WebFetch", {"url": "https://tables.example.edu/energies"}, "t1"),
        tool_result("t1", "tabulated formation energy: 7.35 eV per unit"),
    ])
    rec = audit_transcript(tr, contract)
    assert "NUMERIC_PROXIMITY" in codes(rec, SUSPECT)
    hit = [f for f in rec["findings"] if f["code"] == "NUMERIC_PROXIMITY"][0]
    assert "Ef_eV" in hit["detail"]        # key name is public
    assert hit["context"] == ""            # match location only, no content
    serialized = json.dumps(rec)
    assert "7.34" not in serialized        # sealed value never logged
    assert "7.35" not in serialized        # matched number never logged
    assert rec["verdict"] == SUSPECT       # proximity alone never auto-VOIDs


def test_numeric_far_outside_window_not_flagged(tmp_path, contract):
    tr = write_jsonl(tmp_path, [
        tool_use("WebFetch", {"url": "https://tables.example.edu/energies"}, "t1"),
        tool_result("t1", "lattice constant 5.43, bulk modulus 98.7"),
    ])
    rec = audit_transcript(tr, contract)
    assert "NUMERIC_PROXIMITY" not in codes(rec)


def test_own_computation_output_near_target_not_flagged(tmp_path, contract):
    # deriving the right answer is the POINT — never flag computation outputs
    tr = write_jsonl(tmp_path, [
        tool_use("Bash", {"command": "python thermo.py"}, "t1"),
        tool_result("t1", "final: Ef = 7.339 eV"),
    ])
    rec = audit_transcript(tr, contract, {"Ef_eV": 7.339})
    assert rec["verdict"] == CLEAN


# ---- pass 4: provenance gap -------------------------------------------------

def test_reported_value_from_nowhere_is_suspect(tmp_path, contract):
    tr = write_jsonl(tmp_path, [
        tool_use("Bash", {"command": "python compute.py"}, "t1"),
        tool_result("t1", "run crashed, no result"),
    ])
    rec = audit_transcript(tr, contract, {"Ef_eV": 7.34})
    assert "PROVENANCE_GAP" in codes(rec, SUSPECT)
    assert rec["verdict"] == SUSPECT


def test_provenance_tolerates_rounding(tmp_path, contract):
    tr = write_jsonl(tmp_path, [
        tool_use("Bash", {"command": "python compute.py"}, "t1"),
        tool_result("t1", "Ef = 7.3389 eV (converged)"),
    ])
    rec = audit_transcript(tr, contract, {"Ef_eV": 7.34})  # rounded report
    assert "PROVENANCE_GAP" not in codes(rec)


def test_value_seen_only_in_retrieval_output_is_still_a_gap(tmp_path, contract):
    tr = write_jsonl(tmp_path, [
        tool_use("WebFetch", {"url": "https://tables.example.edu/x"}, "t1"),
        tool_result("t1", "reported value 7.34"),
    ])
    rec = audit_transcript(tr, contract, {"Ef_eV": 7.34})
    assert "PROVENANCE_GAP" in codes(rec, SUSPECT)  # retrieval is not derivation


def test_non_numeric_reported_values_skipped(tmp_path, contract):
    tr = write_jsonl(tmp_path, [
        tool_use("Bash", {"command": "echo ok"}, "t1"),
        tool_result("t1", "ok"),
    ])
    rec = audit_transcript(tr, contract, {"converged": True, "note": "fine"})
    assert "PROVENANCE_GAP" not in codes(rec)


# ---- raw (codex/grok transcript.log) mode: capped at SUSPECT ----------------

def test_raw_mode_blocked_capped_at_suspect(tmp_path, contract):
    p = tmp_path / "transcript.log"
    p.write_text(
        json.dumps({"harness": "native-codex", "config_hash": "abc123def456"}) + "\n"
        "exec: curl https://oqmd.org/api/search?q=stuff\n")
    rec = audit_transcript(p, contract)
    assert rec["verdict"] == SUSPECT          # unstructured: never auto-VOID
    assert "BLOCKED_SURFACE_RAW" in codes(rec, SUSPECT)
    assert rec["raw_lines"] == 1              # header line is metadata, not activity


def test_raw_mode_phrase_on_retrieval_line(tmp_path, contract):
    p = tmp_path / "transcript.log"
    p.write_text("fetching https://arxiv.org/abs/0000.0000 fictitium carbide study\n")
    rec = audit_transcript(p, contract)
    assert rec["verdict"] == SUSPECT
    assert "LOOKUP_PHRASE_RAW" in codes(rec, SUSPECT)


# ---- verdicts, contract loading, plumbing -----------------------------------

def test_violation_outranks_suspect(tmp_path, contract):
    tr = write_jsonl(tmp_path, [
        tool_use("WebFetch", {"url": "https://docs.python.org/3/"}, "t1"),      # SUSPECT
        tool_use("WebFetch", {"url": "https://materialsproject.org/q"}, "t2"),  # VIOLATION
    ])
    rec = audit_transcript(tr, contract)
    assert rec["verdict"] == VIOLATION


def test_missing_transcript_is_flagged(tmp_path, contract):
    rec = audit_transcript(tmp_path / "nope.jsonl", contract)
    assert rec["verdict"] == SUSPECT and "NO_TRANSCRIPT" in rec["flags"]


def test_contract_loads_from_full_task_json(tmp_path):
    task = {
        "id": "TEST-01",
        "environment_contract": {
            "allowed": ["prose description"],
            "blocked_audited": ["prose description"],
            "audit": {"blocked_patterns": [r"(?i)madeupdb\.example"],
                      "lookup_phrases": [r"(?i)unobtainium"]},
        },
    }
    f = tmp_path / "task.json"
    f.write_text(json.dumps(task))
    c = load_contract(f)
    assert c.task_id == "TEST-01"
    assert any(rx.search("GET https://madeupdb.example/api") for rx in c.blocked)


def test_bad_contract_regex_raises(tmp_path):
    with pytest.raises(ContractError):
        Contract({"blocked_patterns": ["(unclosed"]})


def test_resolve_transcript_from_rep_dir(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "loop_transcript.jsonl").write_text("")
    assert resolve_transcript(tmp_path) == ws / "loop_transcript.jsonl"


def test_cli_end_to_end(tmp_path, capsys):
    tr = write_jsonl(tmp_path, [
        tool_use("WebSearch", {"query": "fictitium carbide enthalpy table"}, "t1"),
    ])
    cf = tmp_path / "contract.json"
    cf.write_text(json.dumps(CONTRACT_DATA))
    rc = main([str(tr), "--contract", str(cf), "--brief"])
    assert rc == 2  # VIOLATION
    out = capsys.readouterr()
    rec = json.loads(out.out)
    assert rec["verdict"] == VIOLATION
    assert "VIOLATION" in out.err and "TEST-00" in out.err


def test_cli_clean_exit_zero(tmp_path, capsys):
    tr = write_jsonl(tmp_path, [
        tool_use("Bash", {"command": "python compute.py"}, "t1"),
        tool_result("t1", "Ef = 7.34 eV"),
    ])
    (tmp_path / "reported_values.json").write_text(json.dumps({"Ef_eV": 7.34}))
    cf = tmp_path / "contract.json"
    cf.write_text(json.dumps(CONTRACT_DATA))
    rc = main([str(tr), "--contract", str(cf)])
    assert rc == 0
    assert json.loads(capsys.readouterr().out)["verdict"] == CLEAN
