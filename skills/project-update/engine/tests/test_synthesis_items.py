"""Synthesis-quality features ported from LabSync v1 (single-repo subset):
  - headline ranks by conventional-commit prefix priority (science > tooling)
  - doc-only milestones bucketed separately from suspect drift
  - scientific-focus lead from STATUS.md
  - this-week CHANGELOG window-news + prep opening
  - 🔴 PI-flagged workstream ask surfacing (manifest pi_flag_markers)
  - drift pre-window-date exclusion
"""
from __future__ import annotations

import subprocess

import pytest

from project_update.aggregate import _is_doc_only_milestone
from project_update.synthesize import rank_commits_for_headline


def _git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True, check=True).stdout


def _seed_repo(tmp_path, name="proj"):
    repo = tmp_path / name
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.name", "fl-sean03")
    _git(repo, "config", "user.email", "x@y.z")
    return repo


def _manifest(repo, *, pi_decision_queue="false"):
    (repo / ".sync").mkdir(exist_ok=True)
    (repo / ".sync" / "manifest.yaml").write_text(
        "project:\n  id: t\n  name: T\ndocs:\n  status: STATUS.md\n"
        "  tracker: TRACKER.md\n  changelog: CHANGELOG.md\n"
        "tracker_format:\n  workstreams: true\n"
        f"  pi_decision_queue: {pi_decision_queue}\n"
        '  pi_flag_markers: ["\\U0001F534", "flag to hendrik", "needs pi confirm", "pi confirm", "sign-off"]\n'
        "bundle:\n  root: updates/pi-meetings\n", encoding="utf-8")


# ---------------------------------------------------------------- headline rank

def test_headline_ranks_science_over_tooling():
    commits = [
        {"sha": "a", "prefix": "refactor", "subject": "migrate fig build", "n_files": 50},
        {"sha": "b", "prefix": "feat", "subject": "new figure 3", "n_files": 3},
        {"sha": "c", "prefix": "compute", "subject": "prod fan-out", "n_files": 7},
        {"sha": "d", "prefix": "docs", "subject": "log it", "n_files": 1},
        {"sha": "e", "prefix": "polish", "subject": "tweak layout", "n_files": 2},
    ]
    ranked = rank_commits_for_headline(commits)
    assert all(c["prefix"] != "docs" for c in ranked)
    assert ranked[0]["prefix"] in {"feat", "compute"}
    assert ranked[-1]["prefix"] == "refactor"


def test_headline_tiebreak_prefers_more_files():
    commits = [
        {"sha": "a", "prefix": "feat", "subject": "small", "n_files": 1},
        {"sha": "b", "prefix": "feat", "subject": "big", "n_files": 20},
    ]
    assert rank_commits_for_headline(commits)[0]["sha"] == "b"


# ---------------------------------------------------------------- milestones

@pytest.mark.parametrize("text", [
    "ALCF allocation approved 2026-05-28 ~26,150 node-hr",
    "DD project HydrogenStorage awarded",
    "Sean + Leo request ALCF accounts",
    "INCITE proposal accepted",
])
def test_milestone_tokens_match(text):
    assert _is_doc_only_milestone(text)


@pytest.mark.parametrize("text", [
    "added the paired residence figure",
    "fixed odd numerical drift in analysis",
    "refactor figure build code",
])
def test_non_milestone_text_does_not_match(text):
    assert not _is_doc_only_milestone(text)


def test_milestone_split_out_of_drift(tmp_path):
    from project_update.aggregate import aggregate
    from project_update.manifest import load

    repo = _seed_repo(tmp_path)
    _manifest(repo)
    (repo / "TRACKER.md").write_text("# TRACKER\n\n## Active workstreams\n\n", encoding="utf-8")
    (repo / "STATUS.md").write_text("# STATUS\n", encoding="utf-8")
    (repo / "CHANGELOG.md").write_text("# CHANGELOG\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "feat: seed")
    (repo / "TRACKER.md").write_text(
        (repo / "TRACKER.md").read_text(encoding="utf-8")
        + "| W5 | ALCF allocation | ✅ approved 2026-05-28 ~26,150 node-hr |\n"
        + "| W9 | quantum widget refactor | ✅ done 2026-05-28 |\n",
        encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "docs: log W5 + W9")

    led = aggregate(load(repo), "2000-01-01")
    milestone_text = " ".join(r["text"] for r in led.doc_only_milestones)
    drift_text = " ".join(r["text"] for r in led.claimed_not_evidenced)
    assert "ALCF allocation" in milestone_text
    assert "ALCF allocation" not in drift_text
    assert "quantum widget" in drift_text


def test_synthesis_renders_milestone_section_not_drift():
    from project_update.aggregate import WorkLedger
    from project_update.manifest import Project
    from project_update.synthesize import synthesize

    led = WorkLedger(project="t", repo="/x", since="2026-05-21", until=None,
                     generated="2026-05-29T00:00:00")
    led.doc_only_milestones = [
        {"workstream": "W5", "kind": "status-flip",
         "text": "ALCF allocation approved 2026-05-28 ~26,150 node-hr"}]
    p = Project.from_manifest({"project": {"id": "t", "name": "T"}}, "/x")
    out = synthesize(p, led)
    assert "Milestones (doc-only, externally evidenced)" in out
    assert "Milestone win:" in out


# ---------------------------------------------------------------- scientific focus

_STATUS_SAMPLE = """# STATUS — Demo

## Current focus (scientific framing)

**Paper 1** is the canonical story. Core finding: privileged at low-coordination sites.

---

## Canonical headline numbers

| Metric | Value |
|---|---:|
| Total reactive configs | **397** |
| Relative SE | 2.1% |

## Thrusts

other stuff.
"""


def test_extract_status_focus_pulls_prose_and_table():
    from project_update.adapters.doc_adapters import extract_status_focus
    sf = extract_status_focus(_STATUS_SAMPLE)
    assert sf.present
    assert "Paper 1" in sf.focus_prose
    assert "Canonical headline numbers" not in sf.focus_prose
    assert not sf.focus_prose.rstrip().endswith("---")
    assert "Total reactive configs" in sf.headline_table
    assert "Thrusts" not in sf.headline_table
    assert sf.first_sentence().startswith("Paper 1 is the canonical story.")
    assert sf.top_headline_number() == "Total reactive configs: 397"


def test_synthesis_leads_with_scientific_focus():
    from project_update.aggregate import WorkLedger
    from project_update.manifest import Project
    from project_update.synthesize import synthesize

    led = WorkLedger(project="t", repo="/x", since="2026-05-21", until=None,
                     generated="2026-05-29T00:00:00")
    led.scientific_focus = {
        "focus_prose": "Paper 1 is the canonical story.",
        "headline_table": "| Metric | Value |\n|---|---:|\n| Configs | **397** |",
        "first_sentence": "Paper 1 is the canonical story.",
        "top_headline_number": "Configs: 397",
    }
    out = synthesize(Project.from_manifest({"project": {"id": "t", "name": "T"}}, "/x"), led)
    assert out.index("## Scientific focus") < out.index("## What moved this window")


# ---------------------------------------------------------------- PI-flagged asks

def test_pi_flagged_workstream_ask_leads_ask(load_project):
    from project_update.adapters.doc_adapters import pi_flagged_asks
    from project_update.aggregate import WorkLedger
    from project_update.manifest import Project
    from project_update.synthesize import synthesize

    tracker = (
        "# TRACKER\n\n## Active workstreams\n\n"
        "| | Workstream | Status | Notes |\n|---|---|---|---|\n"
        "| W2.25 | **NPT-fixed judgment call** — accept as pre-equil vs rerun flexible "
        "| 🔴 flag to Hendrik (2026-05-22 1:1) | Recommend ACCEPT: re-thermalizes. Needs PI confirm. |\n"
        "| W2.36 | Deploy slurm_cool_prod.sh | ⏸ gated on Hendrik 2026-05-22 sign-off | Simple rsync |\n"
        "| W4 | manuscript figures | 🟡 | active |\n"
    )
    markers = ["🔴", "flag to hendrik", "needs pi confirm", "pi confirm", "sign-off"]
    asks = pi_flagged_asks(tracker, markers)
    # only the genuine 🔴 ask — the ⏸ forward-dependency on the sign-off is excluded
    assert [a.workstream for a in asks] == ["W2.25"]
    assert "NPT-fixed judgment call" in asks[0].directive
    assert "Recommend ACCEPT" in asks[0].recommendation

    led = WorkLedger(project="t", repo="/x", since="2026-05-21", until=None,
                     generated="2026-05-29T00:00:00")
    led.pi_flagged_asks = [{"workstream": "W2.25",
                            "directive": "NPT-fixed judgment call",
                            "recommendation": "Recommend ACCEPT. Needs PI confirm."}]
    led.open_decisions = ["| D.3 | 2H NEC parameterization | ⏸ |"]
    out = synthesize(Project.from_manifest({"project": {"id": "t", "name": "T"}}, "/x"), led)
    assert "PI-flagged workstream asks" in out
    assert out.index("W2.25") < out.index("D.3")


def test_pi_flagged_asks_empty_when_no_red_flags():
    from project_update.adapters.doc_adapters import pi_flagged_asks
    tracker = (
        "# TRACKER\n\n## Active workstreams\n\n"
        "| W4 | manuscript figures | 🟡 | active |\n"
        "| W3.1 | benchmark | ⏸ ready to deploy | engineering |\n"
    )
    assert pi_flagged_asks(tracker, ["🔴", "flag to hendrik", "sign-off"]) == []


# ---------------------------------------------------------------- changelog window

_CHANGELOG_SAMPLE = """# Changelog

## 2026-05-25 (afternoon): pivot to amilan long QoS (al40 stuck)

- al40 unusable for ~6+ hr: nodes drained. Pivoted to amilan long QoS.

## 2026-05-24: SLURM array output fail + recovery

- 39 array tasks instant-failed; fixed with snapshot symlinks.

## 2026-05-15: PI 1:1 — prelim followup

- Old news, before the window.
"""


def test_changelog_entries_in_window():
    from project_update.adapters.doc_adapters import changelog_entries_in_window
    entries = changelog_entries_in_window(_CHANGELOG_SAMPLE, "2026-05-21", "2026-05-29")
    assert [e.iso_date for e in entries] == ["2026-05-25", "2026-05-24"]
    assert entries[0].date == "2026-05-25 (afternoon)"
    assert entries[0].heading.startswith("pivot to amilan")
    assert "al40 unusable" in entries[0].gist


def test_this_week_section_and_prep_opening_lead_with_news(fake_repo, load_project):
    from project_update.bundle import build

    (fake_repo / "CHANGELOG.md").write_text(
        "# Changelog\n\n"
        "## 2026-05-25 (afternoon): pivot to amilan long QoS (al40 outage)\n\n"
        "- al40 stuck; pivoted to amilan long QoS.\n\n"
        "## 2026-05-10: old pre-window entry\n\n- before the window.\n",
        encoding="utf-8")
    _git(fake_repo, "add", "-A")
    _git(fake_repo, "commit", "-q", "-m", "docs: changelog")

    res = build(load_project(fake_repo), "2026-05-29", since="2026-05-21",
                kind="pi-meeting", build_deck_flag=False)
    synth = res.synthesis.read_text(encoding="utf-8")
    assert "## This week's developments (from CHANGELOG)" in synth
    assert synth.index("This week's developments") < synth.index("What moved this window")
    assert "pivot to amilan long QoS" in synth
    assert "old pre-window entry" not in synth

    prep_text = res.prep.read_text(encoding="utf-8")
    opening = prep_text.split("## 2 · The 90-second opening", 1)[1].split("## 3", 1)[0]
    assert opening.strip().startswith('> "This week: 2026-05-25 (afternoon): pivot to amilan')


# ---------------------------------------------------------------- drift window-bleed

def test_pre_window_done_claims_excluded_from_drift(tmp_path):
    from project_update.aggregate import aggregate
    from project_update.manifest import load

    repo = _seed_repo(tmp_path)
    _manifest(repo)
    (repo / "TRACKER.md").write_text("# TRACKER\n\n## Active workstreams\n\n", encoding="utf-8")
    (repo / "STATUS.md").write_text("# STATUS\n", encoding="utf-8")
    (repo / "CHANGELOG.md").write_text("# CHANGELOG\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "feat: seed")
    (repo / "TRACKER.md").write_text(
        (repo / "TRACKER.md").read_text(encoding="utf-8")
        + "| W1.4 | retire old figure-sheet.tex | ✅ done 2026-05-13 |\n"
        + "| W7.1 | new quantum analysis module | ✅ done 2026-05-24 |\n",
        encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "docs: tracker updates")

    led = aggregate(load(repo), "2026-05-21")
    drift = " ".join(r["text"] for r in led.claimed_not_evidenced)
    assert "figure-sheet" not in drift  # pre-window ✅ 2026-05-13 excluded
    assert "quantum analysis" in drift  # in-window ✅ 2026-05-24 stays
