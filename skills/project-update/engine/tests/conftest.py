"""Shared fixtures — a throwaway git repo + manifest so tests need no live repo."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

# Make the engine package importable without an install.
ENGINE = Path(__file__).resolve().parents[1]
if str(ENGINE) not in sys.path:
    sys.path.insert(0, str(ENGINE))


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, check=True,
    ).stdout


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.name", "fl-sean03")
    _git(repo, "config", "user.email", "test@example.com")


_MANIFEST = """project:
  id: testproj
  name: Test Project
  pi: Hendrik Heinz
  cadence: weekly
docs:
  status: STATUS.md
  tracker: TRACKER.md
  changelog: CHANGELOG.md
  agents: AGENTS.md
tracker_format:
  workstreams: true
  pi_decision_queue: true
  pi_flag_markers: ["\U0001F534", "flag to hendrik", "needs pi confirm", "pi confirm", "sign-off", "flag to pi"]
evidence_globs:
  - analysis/*.py
bundle:
  root: updates/pi-meetings
  contract_version: 1
conventional_prefixes: [feat, fix, docs, compute, refactor, polish, chore]
"""


def _write_manifest(repo: Path, body: str = _MANIFEST) -> None:
    (repo / ".sync").mkdir(parents=True, exist_ok=True)
    (repo / ".sync" / "manifest.yaml").write_text(body, encoding="utf-8")


@pytest.fixture
def fake_repo(tmp_path):
    """A git repo with the quad docs + a manifest + a couple commits."""
    repo = tmp_path / "proj"
    _init_repo(repo)
    _write_manifest(repo)

    tracker = repo / "TRACKER.md"
    tracker.write_text(
        "# TRACKER\n\n"
        "## PI decisions\n\n"
        "| | Decision | Status |\n|---|---|---|\n"
        "| D.1 | pick a venue | ⏸ open |\n"
        "| D.2 | sizing call | ✅ CLOSED autonomous |\n\n"
        "## Active workstreams\n\n"
        "| W4 | manuscript figures | 🟡 |\n",
        encoding="utf-8",
    )
    (repo / "STATUS.md").write_text("# STATUS\n\nbaseline\n", encoding="utf-8")
    (repo / "CHANGELOG.md").write_text("# CHANGELOG\n\n- init\n", encoding="utf-8")
    (repo / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
    src = repo / "analysis"
    src.mkdir()
    (src / "fig.py").write_text("print('fig')\n", encoding="utf-8")

    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "feat: paired residence figure prototype")

    tracker.write_text(
        tracker.read_text(encoding="utf-8")
        + "| W4.10b | paired residence figure | ✅ done |\n",
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "docs: log W4.10b figure")
    return repo


@pytest.fixture
def load_project():
    from project_update import manifest

    def _load(repo: Path):
        return manifest.load(repo)

    return _load
