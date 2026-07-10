"""Doc adapters — the heterogeneity seam.

The engine never hardcodes how a project's docs are shaped. Doc adapters read a
project's narrative docs + diff them across a window; the engine auto-selects the
adapter from the manifest's declared+present docs. To add a new shape, write a
subclass and register it in DOC_ADAPTERS.
"""
from __future__ import annotations

from .doc_adapters import DOC_ADAPTERS, DocAdapter, get_doc_adapter

__all__ = ["DOC_ADAPTERS", "DocAdapter", "get_doc_adapter"]
