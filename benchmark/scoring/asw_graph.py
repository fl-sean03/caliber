#!/usr/bin/env python3
"""
asw_graph.py — provenance write-path for ASW campaigns (the verification substrate).

RATIFIED 2026-07-07 (RESEARCH_GRAPH_VERDICT_fable.md). This is G1 of the graph build:
a per-campaign, append-only, PROV-typed provenance graph in PLAIN JSON — a research
audit trail, NOT a production graph DB. It exists so that from any graded anchor you can
walk mechanically to the exact runs/inputs that produced it — the difference between an
ASW grade being an *assertion* and being an *audit*.

DESIGN (amendments A1/A2):
- **A1 — standards-aligned, not standards-encumbered.** PROV vocabulary is the *type
  system*, expressed as plain JSON strings (`"@type": "prov:Activity"`, PROV edge names,
  content-addressed IDs). One append-only `graph.jsonl` per campaign, JSON-LD-*compatible*
  by construction. RO-Crate / nanopublication are EXPORT targets (later), never runtime
  formats. No RDF library, no triple store, no graph DB in the hot path.
- **A2 — write-path first.** This module is the WRITE path + a minimal grep-grade `query`.
  No vector store, no retrieval pipeline, no embeddings.

Node @types:  prov:Entity (Artifact), prov:Activity (Run), prov:Agent,
              asw:Hypothesis, asw:Claim.
Edge rels:    prov:used, prov:wasGeneratedBy, prov:wasDerivedFrom,
              prov:wasAssociatedWith, asw:supports, asw:refutes.
IDs:          artifacts are content-addressed (sha256[:16]); other nodes hash their
              defining fields → dedup + verifiable lineage.

STDLIB only. Library + CLI.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

CONTEXT = {
    "prov": "http://www.w3.org/ns/prov#",
    "asw": "https://asw.science/prov#",
}
NODE_TYPES = {"prov:Entity", "prov:Activity", "prov:Agent",
              "asw:Hypothesis", "asw:Claim"}
EDGE_RELS = {"prov:used", "prov:wasGeneratedBy", "prov:wasDerivedFrom",
             "prov:wasAssociatedWith", "asw:supports", "asw:refutes"}


def _hash(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def _canonical(d: dict) -> str:
    return json.dumps(d, sort_keys=True, separators=(",", ":"))


class ProvenanceGraph:
    """Append-only PROV-typed provenance graph for one campaign (graph.jsonl)."""

    def __init__(self, path: str | os.PathLike):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ids: set[str] = set()
        if self.path.exists():
            for line in self.path.read_text().splitlines():
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if rec.get("@id"):
                    self._ids.add(rec["@id"])

    # -- low-level append (idempotent on @id / edge identity) --------------
    def _append(self, rec: dict) -> None:
        with open(self.path, "a") as f:
            f.write(_canonical(rec) + "\n")

    def _node(self, node_id: str, typ: str, props: dict) -> str:
        if typ not in NODE_TYPES:
            raise ValueError(f"unknown node @type {typ!r}")
        if node_id in self._ids:
            return node_id            # dedup: identical content-addressed node
        rec = {"@id": node_id, "@type": typ}
        rec.update({k: v for k, v in props.items() if v is not None})
        self._append(rec)
        self._ids.add(node_id)
        return node_id

    # -- nodes -------------------------------------------------------------
    def artifact(self, filepath: str | os.PathLike, role: str | None = None,
                 media_type: str | None = None) -> str:
        """Content-addressed Entity for a file on disk (sha256 of content)."""
        p = Path(filepath)
        data = p.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        node_id = "art:" + digest[:16]
        return self._node(node_id, "prov:Entity", {
            "prov:type": "Artifact", "path": str(p), "sha256": digest,
            "bytes": len(data), "role": role, "mediaType": media_type})

    def run(self, tool: str, command: str | None = None,
            used: list[str] | None = None, agent: str | None = None,
            cost_usd: float | None = None, wall_s: float | None = None,
            exit_code: int | None = None, session: str | None = None,
            label: str | None = None) -> str:
        """Activity: one computation (a QE/LAMMPS/MLIP run, a fit, etc.)."""
        key = _canonical({"tool": tool, "command": command, "used": sorted(used or []),
                          "session": session, "label": label})
        node_id = "run:" + _hash(key)
        rid = self._node(node_id, "prov:Activity", {
            "prov:type": "Run", "tool": tool, "command": command, "label": label,
            "cost_usd": cost_usd, "wall_s": wall_s, "exit_code": exit_code,
            "session": session})
        for u in (used or []):
            self.edge(rid, "prov:used", u)
        if agent:
            self.edge(rid, "prov:wasAssociatedWith", agent)
        return rid

    def agent(self, model: str, harness: str = "claude-code-p",
              harness_version: str | None = None,
              config_hash: str | None = None) -> str:
        key = _canonical({"model": model, "harness": harness,
                          "hv": harness_version, "ch": config_hash})
        node_id = "agent:" + _hash(key)
        return self._node(node_id, "prov:Agent", {
            "model": model, "harness": harness,
            "harness_version": harness_version, "config_hash": config_hash})

    def hypothesis(self, text: str) -> str:
        node_id = "hyp:" + _hash(text)
        return self._node(node_id, "asw:Hypothesis", {"text": text})

    def claim(self, key: str, value, units: str | None = None,
              conditions: str | None = None, uncertainty=None,
              method: str | None = None, derived_from: list[str] | None = None,
              generated_by: str | None = None) -> str:
        """A reported value / assertion, with a wasDerivedFrom chain to its evidence."""
        ck = _canonical({"key": key, "value": value, "units": units,
                         "conditions": conditions})
        node_id = "claim:" + _hash(ck)
        cid = self._node(node_id, "asw:Claim", {
            "key": key, "value": value, "units": units, "conditions": conditions,
            "uncertainty": uncertainty, "method": method})
        for d in (derived_from or []):
            self.edge(cid, "prov:wasDerivedFrom", d)
        if generated_by:
            self.edge(cid, "prov:wasGeneratedBy", generated_by)
        return cid

    # -- edges -------------------------------------------------------------
    def edge(self, subject: str, rel: str, obj: str) -> None:
        if rel not in EDGE_RELS:
            raise ValueError(f"unknown edge rel {rel!r}")
        eid = "edge:" + _hash(f"{subject}|{rel}|{obj}")
        if eid in self._ids:
            return
        self._append({"@id": eid, "@type": "prov:Relation",
                      "rel": rel, "subject": subject, "object": obj})
        self._ids.add(eid)

    # -- read (minimal; grep-grade per A2) ---------------------------------
    def _load(self) -> tuple[dict, list[dict]]:
        nodes, edges = {}, []
        if not self.path.exists():
            return nodes, edges
        for line in self.path.read_text().splitlines():
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if rec.get("@type") == "prov:Relation":
                edges.append(rec)
            elif rec.get("@id"):
                nodes[rec["@id"]] = rec
        return nodes, edges

    def query(self, node_id: str) -> dict:
        """Return a node plus its full transitive provenance ancestry (used /
        wasDerivedFrom / wasGeneratedBy / wasAssociatedWith)."""
        nodes, edges = self._load()
        if node_id not in nodes:
            raise KeyError(node_id)
        follow = {"prov:used", "prov:wasDerivedFrom", "prov:wasGeneratedBy",
                  "prov:wasAssociatedWith"}
        seen, ancestry, frontier = set(), [], [node_id]
        while frontier:
            cur = frontier.pop()
            for e in edges:
                if e["subject"] == cur and e["rel"] in follow:
                    obj = e["object"]
                    if obj not in seen:
                        seen.add(obj)
                        ancestry.append({"rel": e["rel"], "node": nodes.get(obj, {"@id": obj})})
                        frontier.append(obj)
        return {"node": nodes[node_id], "ancestry": ancestry}

    def summary(self) -> dict:
        nodes, edges = self._load()
        by_type: dict[str, int] = {}
        for n in nodes.values():
            by_type[n.get("@type", "?")] = by_type.get(n.get("@type", "?"), 0) + 1
        return {"path": str(self.path), "nodes": len(nodes),
                "edges": len(edges), "by_type": by_type}


# --------------------------------------------------------------------------
# CLI — so the long-compute worker can record provenance as it runs, e.g.
#   asw-graph artifact runs/scf.out --role dft-output --graph graph.jsonl
#   asw-graph run --tool qe --label scf --used art:... --graph graph.jsonl
#   asw-graph claim --key pt_GPa --value 9.7 --units GPa --derived-from run:... --graph ...
# --------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="asw-graph", description="ASW provenance write-path.")
    ap.add_argument("--graph", required=True, help="path to campaign graph.jsonl")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("artifact"); a.add_argument("file"); a.add_argument("--role"); a.add_argument("--media-type")
    r = sub.add_parser("run"); r.add_argument("--tool", required=True); r.add_argument("--command")
    r.add_argument("--label"); r.add_argument("--used", nargs="*", default=[]); r.add_argument("--agent")
    r.add_argument("--cost-usd", type=float); r.add_argument("--wall-s", type=float)
    r.add_argument("--exit-code", type=int); r.add_argument("--session")
    ag = sub.add_parser("agent"); ag.add_argument("--model", required=True); ag.add_argument("--harness", default="claude-code-p")
    ag.add_argument("--harness-version"); ag.add_argument("--config-hash")
    h = sub.add_parser("hypothesis"); h.add_argument("text")
    c = sub.add_parser("claim"); c.add_argument("--key", required=True); c.add_argument("--value", required=True)
    c.add_argument("--units"); c.add_argument("--conditions"); c.add_argument("--uncertainty")
    c.add_argument("--method"); c.add_argument("--derived-from", nargs="*", default=[]); c.add_argument("--generated-by")
    e = sub.add_parser("edge"); e.add_argument("subject"); e.add_argument("rel"); e.add_argument("object")
    q = sub.add_parser("query"); q.add_argument("id")
    sub.add_parser("summary")

    args = ap.parse_args(argv)
    g = ProvenanceGraph(args.graph)
    out = None
    if args.cmd == "artifact":
        out = g.artifact(args.file, role=args.role, media_type=args.media_type)
    elif args.cmd == "run":
        out = g.run(args.tool, command=args.command, used=args.used, agent=args.agent,
                    cost_usd=args.cost_usd, wall_s=args.wall_s, exit_code=args.exit_code,
                    session=args.session, label=args.label)
    elif args.cmd == "agent":
        out = g.agent(args.model, harness=args.harness,
                      harness_version=args.harness_version, config_hash=args.config_hash)
    elif args.cmd == "hypothesis":
        out = g.hypothesis(args.text)
    elif args.cmd == "claim":
        try:
            val = float(args.value)
        except ValueError:
            val = args.value
        out = g.claim(args.key, val, units=args.units, conditions=args.conditions,
                      uncertainty=args.uncertainty, method=args.method,
                      derived_from=args.derived_from, generated_by=args.generated_by)
    elif args.cmd == "edge":
        g.edge(args.subject, args.rel, args.object); out = "ok"
    elif args.cmd == "query":
        out = json.dumps(g.query(args.id), indent=2)
    elif args.cmd == "summary":
        out = json.dumps(g.summary(), indent=2)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
