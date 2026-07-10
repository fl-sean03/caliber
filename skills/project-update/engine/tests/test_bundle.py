"""Bundle build: file set, meeting.yaml provenance, idempotency, reserved-file
protection, graceful deck degrade."""
from __future__ import annotations

import subprocess

from project_update import __version__
from project_update.bundle import build


def _git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True, check=True).stdout


def test_build_writes_full_file_set(fake_repo, load_project):
    res = build(load_project(fake_repo), "2026-05-29", since="2026-05-21",
                kind="pi-meeting", build_deck_flag=False)
    assert res.bundle_dir == fake_repo / "updates" / "pi-meetings" / "2026-05-29"
    assert res.meeting_yaml.exists()
    assert res.prep.exists()
    assert res.synthesis.exists()
    assert (res.bundle_dir / "artifacts").exists() or not res.artifacts


def test_meeting_yaml_carries_provenance(fake_repo, load_project):
    from project_update import yaml_lite
    res = build(load_project(fake_repo), "2026-05-29", since="2026-05-22",
                kind="pi-meeting", build_deck_flag=False)
    data = yaml_lite.load_file(res.meeting_yaml)
    assert data["contract_version"] == 1
    assert data["project"] == "testproj"
    assert data["date"] == "2026-05-29"
    assert data["kind"] == "pi-meeting"
    assert data["status"] == "prepped"
    assert data["generated_by"] == f"project-update@{__version__}"
    assert data["window"]["since"] == "2026-05-22"
    assert data["window"]["until"] == "2026-05-29"
    head = _git(fake_repo, "rev-parse", "HEAD").strip()[:10]
    assert data["source_head"] == head


def test_build_is_idempotent_and_protects_reserved_files(fake_repo, load_project):
    p = load_project(fake_repo)
    res = build(p, "2026-05-29", since="2026-05-21", build_deck_flag=False)
    # a human drops a transcript + LabSync drops feedback
    (res.bundle_dir / "TRANSCRIPT.md").write_text("raw transcript\n", encoding="utf-8")
    (res.bundle_dir / "feedback-extracted.md").write_text("directives\n", encoding="utf-8")
    # rebuild for the same date
    build(p, "2026-05-29", since="2026-05-21", build_deck_flag=False)
    # engine-owned files regenerated; human/LabSync files untouched
    assert (res.bundle_dir / "TRANSCRIPT.md").read_text(encoding="utf-8") == "raw transcript\n"
    assert (res.bundle_dir / "feedback-extracted.md").read_text(encoding="utf-8") == "directives\n"
    assert res.synthesis.exists()


def test_deck_degrades_gracefully_when_no_builder(tmp_path, load_project):
    repo = tmp_path / "nodeck"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.name", "fl-sean03")
    _git(repo, "config", "user.email", "x@y.z")
    (repo / ".sync").mkdir()
    (repo / ".sync" / "manifest.yaml").write_text(
        "project:\n  id: nd\n  name: ND\ndocs:\n  status: STATUS.md\n"
        "bundle:\n  root: updates/pi-meetings\n", encoding="utf-8")
    (repo / "STATUS.md").write_text("# STATUS\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "feat: seed")
    res = build(load_project(repo), "2026-05-29", since="2026-01-01",
                build_deck_flag=True)
    assert "No deck builder registered" in res.deck.message
    assert res.synthesis.exists()  # synthesis still builds
