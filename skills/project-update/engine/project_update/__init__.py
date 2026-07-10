"""project-update — Tier-1 single-repo update engine.

A stdlib-only, manifest-driven engine that mines + synthesizes ONE project repo
into its canonical dated update bundle. It has NO dependency on LabSync (the
Tier-1 isolation invariant): a project + this engine is sufficient to build that
project's own weekly / PI-meeting update.

See:
  - ADR-001-two-tier-update-architecture.md  (why)
  - MANIFEST_SCHEMA.md                        (the .sync/manifest.yaml it reads)
  - BUNDLE_CONTRACT.md                        (the bundle it writes)
"""
from __future__ import annotations

__version__ = "0.1.0"
