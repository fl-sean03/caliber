"""Manifest parse + resolution + auto-adapter selection."""
from __future__ import annotations

import subprocess

import pytest

from project_update import manifest


def _git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True, check=True).stdout


def test_manifest_parses_identity_and_docs(fake_repo, load_project):
    p = load_project(fake_repo)
    assert p.id == "testproj"
    assert p.name == "Test Project"
    assert p.pi == "Hendrik Heinz"
    assert p.cadence == "weekly"
    assert p.docs["tracker"] == "TRACKER.md"
    assert p.doc_path("status").name == "STATUS.md"


def test_manifest_pi_flag_markers_include_red_and_phrases(fake_repo, load_project):
    p = load_project(fake_repo)
    markers = p.pi_flag_markers()
    assert "🔴" in markers
    assert "flag to hendrik" in markers
    assert "needs pi confirm" in markers


def test_auto_doc_adapter_is_quad_with_tracker(fake_repo, load_project):
    p = load_project(fake_repo)
    assert p.doc_adapter == "quad"


def test_auto_doc_adapter_degrades(tmp_path):
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / ".sync").mkdir()
    (repo / ".sync" / "manifest.yaml").write_text(
        "project:\n  id: x\n  name: X\ndocs:\n  readme: README.md\n"
        "bundle:\n  root: updates/pi-meetings\n", encoding="utf-8")
    (repo / "README.md").write_text("# x\n", encoding="utf-8")
    p = manifest.load(repo)
    assert p.doc_adapter == "readme_only"


def test_bundle_dir_uses_root_and_date(fake_repo, load_project):
    p = load_project(fake_repo)
    bdir = p.bundle_dir("2026-05-29")
    assert bdir == fake_repo / "updates" / "pi-meetings" / "2026-05-29"
    assert p.contract_version() == 1


def test_missing_manifest_raises_clear_error(tmp_path):
    repo = tmp_path / "nomanifest"
    repo.mkdir()
    _git(repo, "init", "-q")
    with pytest.raises(FileNotFoundError):
        manifest.load(repo)


def test_resolve_repo_finds_toplevel_from_subdir(fake_repo):
    sub = fake_repo / "analysis"
    root = manifest.resolve_repo(str(sub))
    assert root == fake_repo
