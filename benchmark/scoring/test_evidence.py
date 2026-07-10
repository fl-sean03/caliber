"""Tests for harness/evidence.py — the append-only evidence store.

Run: pytest harness/test_evidence.py
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence import (  # noqa: E402
    COMPLETE, CORRUPT, INCOMPLETE, MANIFEST_NAME,
    EvidenceError, EvidenceStore, new_run_id, verify_run,
)


@pytest.fixture()
def store(tmp_path):
    return EvidenceStore(tmp_path / "runs")


# ---------------------------------------------------------------------------
# Run-id + allocation
# ---------------------------------------------------------------------------

def test_run_id_shape():
    fixed = datetime(2026, 7, 5, 13, 45, 7, tzinfo=timezone.utc)
    rid = new_run_id("BENCH-T1-001", now=fixed)
    assert rid.startswith("BENCH-T1-001-20260705-134507-")
    assert len(rid.rsplit("-", 1)[1]) == 4  # rand4 suffix


def test_allocate_creates_nested_run_dir(store):
    run = store.allocate("BENCH-T1-001")
    assert run.path.is_dir()
    assert run.path.parent.name == "BENCH-T1-001"
    assert run.run_id in run.path.name


def test_allocate_never_reuses_or_overwrites(store):
    fixed = datetime(2026, 7, 5, 13, 45, 7, tzinfo=timezone.utc)
    # Same task, same timestamp — only the rand4 differs; must get distinct dirs.
    dirs = {store.allocate("T", now=fixed).path for _ in range(50)}
    assert len(dirs) == 50


def test_allocate_rejects_unsafe_task_id(store):
    for bad in ("../escape", "a/b", ".hidden", ""):
        with pytest.raises(EvidenceError):
            store.allocate(bad)


def test_existing_run_dir_is_never_clobbered(store, tmp_path):
    run = store.allocate("T")
    (run.path / "sentinel.txt").write_text("do-not-delete")
    # A fresh allocation for the same task must not touch the old dir.
    store.allocate("T")
    assert (run.path / "sentinel.txt").read_text() == "do-not-delete"


# ---------------------------------------------------------------------------
# Atomic result.json
# ---------------------------------------------------------------------------

def test_write_result_is_valid_json_roundtrip(store):
    run = store.allocate("T")
    payload = {"model": "opus-4.8", "usage": {"input_tokens": 5}, "cost_usd": 0.01}
    p = run.write_result(payload)
    assert p.name == "result.json"
    assert json.loads(p.read_text()) == payload


def test_write_result_leaves_no_tmp_files(store):
    run = store.allocate("T")
    run.write_result({"a": 1})
    assert [p.name for p in run.path.iterdir()] == ["result.json"]  # no .tmp debris


# ---------------------------------------------------------------------------
# Manifest + verify
# ---------------------------------------------------------------------------

def _complete_run(store, task="T"):
    run = store.allocate(task)
    run.write_result({"model": "opus-4.8", "cost_usd": 0.02})
    with run.open_transcript() as fh:
        fh.write(json.dumps({"type": "system"}) + "\n")
        fh.write(json.dumps({"type": "result"}) + "\n")
    (run.subpath("workspace", "hello.txt")).write_text("v2-smoke")
    run.write_manifest()
    return run


def test_manifest_covers_every_artifact_and_verifies(store):
    run = _complete_run(store)
    manifest = (run.path / MANIFEST_NAME).read_text()
    rels = {line.split("  ", 1)[1] for line in manifest.splitlines()}
    assert rels == {"result.json", "transcript.jsonl", "workspace/hello.txt"}
    assert MANIFEST_NAME not in rels  # manifest never hashes itself
    rep = verify_run(run.path)
    assert rep.ok and rep.status == COMPLETE


def test_missing_manifest_is_incomplete_not_corrupt(store):
    run = store.allocate("T")
    run.write_result({"a": 1})  # no manifest written -> crash-mid-write shape
    rep = verify_run(run.path)
    assert rep.status == INCOMPLETE and not rep.ok
    assert "quarantine" in rep.reason


def test_tampered_file_is_corrupt(store):
    run = _complete_run(store)
    (run.path / "result.json").write_text('{"model": "TAMPERED"}\n')
    rep = verify_run(run.path)
    assert rep.status == CORRUPT and rep.mismatched == ["result.json"]


def test_added_file_after_manifest_is_corrupt(store):
    run = _complete_run(store)
    (run.path / "snuck_in.txt").write_text("added after manifest")
    rep = verify_run(run.path)
    assert rep.status == CORRUPT and "snuck_in.txt" in rep.extra


def test_deleted_file_is_corrupt(store):
    run = _complete_run(store)
    (run.path / "workspace" / "hello.txt").unlink()
    rep = verify_run(run.path)
    assert rep.status == CORRUPT and "workspace/hello.txt" in rep.missing


def test_verify_nonexistent_dir_is_incomplete(tmp_path):
    rep = verify_run(tmp_path / "nope")
    assert rep.status == INCOMPLETE and not rep.ok


def test_kill_mid_run_leaves_quarantinable_not_corrupt(store):
    """EVIDENCE_STORE Phase-2 acceptance: a kill mid-run (transcript started,
    no manifest) is INCOMPLETE — quarantinable, not silently trusted."""
    run = store.allocate("T")
    with run.open_transcript() as fh:
        fh.write(json.dumps({"type": "system", "subtype": "init"}) + "\n")
        # process 'killed' here — no result.json, no manifest
    rep = verify_run(run.path)
    assert rep.status == INCOMPLETE
    assert (run.path / "transcript.jsonl").exists()  # partial trace survives
