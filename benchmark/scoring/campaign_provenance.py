#!/usr/bin/env python3
"""
campaign_provenance.py — G2: fuse a campaign's grading with its provenance graph.

Builds (or extends) a campaign's `graph.jsonl` so that every graded reported_value
becomes an `asw:Claim` that `wasDerivedFrom` the campaign's Runs and their output
artifacts — satisfying the acceptance test: *from any graded anchor, walk mechanically
to the exact QE/MD inputs that produced it* (RESEARCH_GRAPH_VERDICT G2).

Two uses:
  1. **grade-time** — the calibration/pilot driver calls `fuse_campaign(...)` right after
     grading, so each score.json is born with a provenance graph.
  2. **backfill** — run over a retained workspace to reconstruct provenance post-hoc
     (the rep1/rep2 workspaces keep their runs/*.in/*.out, so this loses only the live
     worker-decision chain, not the artifact lineage).

The richer, live worker-emitted run nodes come from the `long-compute` skill calling the
`asw-graph` CLI as work happens; this module is the floor that guarantees a graph exists.

STDLIB only.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

_p = Path(__file__).resolve().parent / "asw_graph.py"
_spec = importlib.util.spec_from_file_location("asw_graph_mod", _p)
_agm = importlib.util.module_from_spec(_spec)
sys.modules["asw_graph_mod"] = _agm
_spec.loader.exec_module(_agm)
ProvenanceGraph = _agm.ProvenanceGraph

# file-name heuristics for grouping computations
_INPUT_SUFFIXES = (".in", ".pwi", ".scf", ".nscf")
_OUTPUT_SUFFIXES = (".out", ".pwo", ".log")
_INPUT_PREFIXES = ("in.",)          # LAMMPS: in.*
_OUTPUT_PREFIXES = ("log.",)        # LAMMPS: log.*


def _is_input(name: str) -> bool:
    return name.endswith(_INPUT_SUFFIXES) or name.startswith(_INPUT_PREFIXES)


def _is_output(name: str) -> bool:
    return name.endswith(_OUTPUT_SUFFIXES) or name.startswith(_OUTPUT_PREFIXES)


def _infer_tool(files: list[Path]) -> str:
    names = " ".join(f.name.lower() for f in files)
    blob = ""
    for f in files:
        if _is_output(f.name):
            try:
                blob = f.read_text(errors="ignore")[:2000].lower(); break
            except Exception:
                pass
    if "quantum espresso" in blob or ".pwi" in names or ".pwo" in names or "pw.x" in blob:
        return "quantum-espresso"
    if "lammps" in blob or "in." in names or "log.lammps" in names:
        return "lammps"
    if "mace" in names or "chgnet" in names or "m3gnet" in names:
        return "mlip"
    return "compute"


def fuse_campaign(workspace, graph_path=None, *, model: str, task_id: str,
                  reported_values: dict, units: dict | None = None,
                  anchors_passed: dict | None = None,
                  harness: str = "asw_loop", config_hash: str | None = None,
                  max_files: int = 400) -> dict:
    """Build/extend the campaign provenance graph; return a summary."""
    ws = Path(workspace)
    graph_path = Path(graph_path) if graph_path else ws / "graph.jsonl"
    g = ProvenanceGraph(graph_path)
    agent = g.agent(model, harness=harness, config_hash=config_hash)

    # 1) group compute files by parent dir → Run nodes with used/generated edges
    run_ids: list[str] = []
    output_art_ids: list[str] = []
    seen = 0
    dirs: dict[Path, list[Path]] = {}
    for f in ws.rglob("*"):
        if not f.is_file():
            continue
        if _is_input(f.name) or _is_output(f.name):
            dirs.setdefault(f.parent, []).append(f)
    for rundir, files in sorted(dirs.items()):
        ins = [f for f in files if _is_input(f.name)]
        outs = [f for f in files if _is_output(f.name)]
        if not (ins or outs):
            continue
        in_ids, out_ids = [], []
        for f in ins:
            if seen >= max_files:
                break
            in_ids.append(g.artifact(f, role="input")); seen += 1
        for f in outs:
            if seen >= max_files:
                break
            oid = g.artifact(f, role="output"); out_ids.append(oid); seen += 1
        rid = g.run(_infer_tool(files), label=str(rundir.relative_to(ws)),
                    used=in_ids, agent=agent)
        for oid in out_ids:
            g.edge(oid, "prov:wasGeneratedBy", rid)
        run_ids.append(rid)
        output_art_ids.extend(out_ids)

    # 2) top-level deliverables as artifacts
    deliverables = []
    for name, role in (("report.md", "report"), ("reported_values.json", "reported-values"),
                       ("WORKFLOW.md", "workflow")):
        fp = ws / name
        if fp.is_file():
            deliverables.append(g.artifact(fp, role=role))

    # 3) one Claim per reported value, derived from the runs + their outputs + report
    units = units or {}
    anchors_passed = anchors_passed or {}
    evidence = output_art_ids + run_ids + [d for d in deliverables]
    claim_ids = {}
    for key, val in reported_values.items():
        cid = g.claim(key, val, units=units.get(key), method="see report.md",
                      derived_from=evidence)
        # record verification outcome as a typed edge to the report artifact
        if key in anchors_passed and deliverables:
            rel = "asw:supports" if anchors_passed[key] else "asw:refutes"
            g.edge(cid, rel, deliverables[0])
        claim_ids[key] = cid

    summ = g.summary()
    summ.update({"task_id": task_id, "runs": len(run_ids),
                 "claims": len(claim_ids), "graph": str(graph_path)})
    return summ


def backfill_from_score(runroot, model: str = "claude-opus-4-8") -> dict:
    """Backfill a retained calibration run dir (has ws/ + score.json)."""
    runroot = Path(runroot)
    ws = runroot / "ws"
    score = json.loads((runroot / "score.json").read_text())
    rv = score.get("reported_values", {})
    # anchors_passed unknown per-key here; leave empty (claims still recorded)
    return fuse_campaign(ws, model=score.get("model", model),
                         task_id=score.get("task_id", runroot.parent.name),
                         reported_values=rv)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Fuse campaign grading with provenance graph.")
    ap.add_argument("runroot", help="a run dir containing ws/ and score.json")
    ap.add_argument("--model", default="claude-opus-4-8")
    a = ap.parse_args(argv)
    print(json.dumps(backfill_from_score(a.runroot, model=a.model), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
