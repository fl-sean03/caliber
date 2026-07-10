"""Manifest loader — the per-project `<repo>/.sync/manifest.yaml` (the Tier-1
replacement for LabSync's central registry).

Per ADR-001 + MANIFEST_SCHEMA.md, every project carries its own manifest that
declares its doc shapes, evidence globs, deck builder, PI-flag markers, and
bundle root. The engine mines + synthesizes a SINGLE repo from this file alone —
it never imports LabSync. A `Project` object exposes the same surface the ported
mining/synthesis modules expect.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import gitlog, yaml_lite

MANIFEST_RELPATH = ".sync/manifest.yaml"

# Default markers that escalate a WORKSTREAM row to a PI ask. The manifest's
# tracker_format.pi_flag_markers overrides this; both are honored.
_DEFAULT_PI_FLAG_MARKERS = [
    "🔴", "flag to hendrik", "flag to pi", "needs pi confirm", "pi confirm",
    "sign-off",
]


@dataclass
class Project:
    """A single project, resolved from its `.sync/manifest.yaml`."""

    id: str
    name: str
    repo: Path
    pi: str = "Hendrik Heinz"
    cadence: str = "unknown"
    docs: dict = field(default_factory=dict)
    tracker_format: dict = field(default_factory=dict)
    deck: dict = field(default_factory=dict)
    evidence_globs: list = field(default_factory=list)
    bundle: dict = field(default_factory=dict)
    conventional_prefixes: list = field(default_factory=list)

    @classmethod
    def from_manifest(cls, data: dict, repo: Path) -> Project:
        ident = data.get("project") or {}
        return cls(
            id=ident.get("id") or repo.name,
            name=ident.get("name") or ident.get("id") or repo.name,
            repo=Path(repo),
            pi=ident.get("pi", "Hendrik Heinz"),
            cadence=ident.get("cadence", "unknown"),
            docs=data.get("docs") or {},
            tracker_format=data.get("tracker_format") or {},
            deck=data.get("deck") or {},
            evidence_globs=data.get("evidence_globs") or [],
            bundle=data.get("bundle") or {},
            conventional_prefixes=data.get("conventional_prefixes")
            or ["feat", "fix", "docs", "compute", "refactor", "polish", "chore"],
        )

    # ---- doc access -------------------------------------------------------
    def doc_path(self, key: str) -> Path | None:
        rel = self.docs.get(key)
        return self.repo / rel if rel else None

    def doc_exists(self, key: str) -> bool:
        p = self.doc_path(key)
        return bool(p and p.exists())

    @property
    def doc_adapter(self) -> str:
        """Auto-select the doc-reading shape from which docs the manifest
        declares + which exist. Keeps the heterogeneity logic in ONE place so
        a project only declares its docs, not an adapter name."""
        if self.doc_exists("tracker"):
            return "quad"
        if self.doc_exists("status"):
            return "agents_status"
        if self.doc_exists("roadmap"):
            return "agents_roadmap"
        if self.doc_exists("readme"):
            return "readme_only"
        return "base"

    # ---- PI-flag markers --------------------------------------------------
    def pi_flag_markers(self) -> list:
        markers = self.tracker_format.get("pi_flag_markers")
        if markers:
            return [str(m) for m in markers]
        return list(_DEFAULT_PI_FLAG_MARKERS)

    # ---- bundle -----------------------------------------------------------
    def bundle_root(self) -> Path:
        root = self.bundle.get("root") or "updates/pi-meetings"
        return self.repo / root

    def bundle_dir(self, date: str) -> Path:
        return self.bundle_root() / date

    def contract_version(self) -> int:
        try:
            return int(self.bundle.get("contract_version", 1))
        except (TypeError, ValueError):
            return 1


def manifest_path(repo: Path) -> Path:
    return repo / MANIFEST_RELPATH


def load(repo: Path) -> Project:
    """Load `<repo>/.sync/manifest.yaml` into a Project. Raises FileNotFoundError
    with a clear hint if the manifest is missing."""
    repo = Path(repo)
    path = manifest_path(repo)
    if not path.exists():
        raise FileNotFoundError(
            f"no manifest at {path}. Create one per MANIFEST_SCHEMA.md "
            f"(declare docs, tracker_format.pi_flag_markers, evidence_globs, "
            f"deck, bundle.root)."
        )
    data: Any = yaml_lite.load_file(path)
    if not isinstance(data, dict):
        raise RuntimeError(f"manifest at {path} did not parse to a mapping")
    return Project.from_manifest(data, repo)


def resolve_repo(repo_arg: str | None) -> Path:
    """Resolve the repo root: an explicit --repo (its git toplevel) or the cwd's
    git toplevel."""
    start = Path(repo_arg).resolve() if repo_arg else Path.cwd()
    root = gitlog.repo_root(start)
    if root is None:
        raise RuntimeError(
            f"{start} is not inside a git repository (the engine resolves the "
            f"repo root via `git rev-parse --show-toplevel`)."
        )
    return root
