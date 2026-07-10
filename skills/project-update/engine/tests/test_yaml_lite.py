"""yaml_lite: the manifest subset round-trips correctly."""
from __future__ import annotations

from project_update import yaml_lite

_SRC = """project:
  id: hydrogenation
  name: Pt-NEC LOHC Hydrogenation
  cadence: weekly
docs:
  status: STATUS.md
  tracker: TRACKER.md
tracker_format:
  workstreams: true
  pi_decision_queue: true
  pi_flag_markers: ["\U0001F534", "flag to hendrik", "sign-off"]
evidence_globs:
  - simulations/*/WORKFLOW.md
  - manuscript/build/*.pdf
bundle:
  root: updates/pi-meetings
  contract_version: 1
conventional_prefixes: [feat, fix, docs]
"""


def test_parses_nested_maps_and_lists():
    d = yaml_lite.loads(_SRC)
    assert d["project"]["id"] == "hydrogenation"
    assert d["project"]["cadence"] == "weekly"
    assert d["tracker_format"]["workstreams"] is True
    assert d["tracker_format"]["pi_decision_queue"] is True


def test_parses_flow_and_block_lists():
    d = yaml_lite.loads(_SRC)
    assert d["tracker_format"]["pi_flag_markers"] == ["🔴", "flag to hendrik", "sign-off"]
    assert d["evidence_globs"] == ["simulations/*/WORKFLOW.md", "manuscript/build/*.pdf"]
    assert d["conventional_prefixes"] == ["feat", "fix", "docs"]


def test_scalar_typing():
    d = yaml_lite.loads(_SRC)
    assert d["bundle"]["contract_version"] == 1
    assert isinstance(d["bundle"]["contract_version"], int)
    assert d["bundle"]["root"] == "updates/pi-meetings"
