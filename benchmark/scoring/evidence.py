#!/usr/bin/env python3
"""
evidence.py — the append-only evidence store (harness/EVIDENCE_STORE.md is the
contract; this is the implementation).

Every rule here traces to a paid-for v1 failure:
  * run-ids embed task-id + UTC timestamp + a random suffix, and a dir is
    allocated by an ATOMIC exclusive mkdir — a collision yields a NEW id, never
    an overwrite. No code path in this module deletes or truncates under runs/.
    (v1: rmtree-on-rerun; 16/98 lost workspaces; D11.)
  * result.json is written atomically (temp file + os.replace) so a crash never
    leaves a half-written verdict.
  * MANIFEST.sha256 hashes every artifact and is written LAST; its PRESENCE is
    what marks a run dir COMPLETE. A missing manifest = a crash mid-write =>
    verify_run reports INCOMPLETE (quarantine, never silently repair).
    (v1: doc-claims about artifacts diverged from the artifacts, RD-06.)

Stdlib-only. This module owns durability + integrity; the executor
(harness/executor.py) owns what goes INTO a run dir.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

MANIFEST_NAME = "MANIFEST.sha256"
RESULT_NAME = "result.json"
_ALLOC_TRIES = 1000


class EvidenceError(RuntimeError):
    """A run dir could not be allocated, or an invariant would be violated."""


# ---------------------------------------------------------------------------
# Run-id + allocation
# ---------------------------------------------------------------------------

def new_run_id(task_id: str, now: datetime | None = None) -> str:
    """`<task-id>-<UTC yyyymmdd-hhmmss>-<rand4>` (EVIDENCE_STORE.md layout)."""
    now = now or datetime.now(timezone.utc)
    ts = now.astimezone(timezone.utc).strftime("%Y%m%d-%H%M%S")
    rand4 = secrets.token_hex(2)  # 4 hex chars
    return f"{task_id}-{ts}-{rand4}"


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write `data` to `path` atomically: temp file in the same dir, fsync,
    os.replace (atomic on the same filesystem), then fsync the directory."""
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}.{secrets.token_hex(4)}")
    with open(tmp, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    dfd = os.open(str(path.parent), os.O_DIRECTORY)
    try:
        os.fsync(dfd)
    finally:
        os.close(dfd)


def sha256_file(path: Path, _bufsize: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(_bufsize), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class RunDir:
    """Handle to one allocated run directory. Nothing here overwrites another
    run's data — the dir is unique by construction."""
    path: Path
    task_id: str
    run_id: str

    def subpath(self, *parts: str) -> Path:
        p = self.path.joinpath(*parts)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    # -- writers -----------------------------------------------------------

    def write_result(self, result: dict) -> Path:
        """Atomically write result.json. Model/cli_version/usage/cost live here
        in-band (EVIDENCE_STORE rule 4)."""
        path = self.path / RESULT_NAME
        data = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8")
        _atomic_write_bytes(path, data)
        return path

    def open_transcript(self, name: str = "transcript.jsonl"):
        """Open the transcript for line-buffered append. The executor writes to
        this UNCONDITIONALLY from the first event (rule 2) so a kill mid-run
        still leaves a partial, quarantinable transcript."""
        return open(self.path / name, "a", buffering=1, encoding="utf-8")

    def _iter_files(self, exclude: set[str]) -> list[Path]:
        return sorted(
            p for p in self.path.rglob("*")
            if p.is_file() and p.name not in exclude
            and not p.name.startswith(".")  # skip in-flight .tmp atomic files
        )

    def write_manifest(self) -> Path:
        """Hash every artifact under the run dir and write MANIFEST.sha256 LAST.
        Its presence marks the run COMPLETE. Format is sha256sum-compatible:
        `<hex>  <relpath>`."""
        lines = []
        for f in self._iter_files(exclude={MANIFEST_NAME}):
            rel = f.relative_to(self.path).as_posix()
            lines.append(f"{sha256_file(f)}  {rel}")
        body = ("\n".join(lines) + "\n").encode("utf-8") if lines else b""
        _atomic_write_bytes(self.path / MANIFEST_NAME, body)
        return self.path / MANIFEST_NAME


class EvidenceStore:
    """Allocator over `runs/`. `allocate` is the only way to get a RunDir, and
    it never returns an existing one."""

    def __init__(self, root: str | os.PathLike):
        self.root = Path(root)

    def allocate(self, task_id: str, now: datetime | None = None) -> RunDir:
        """Create `runs/<task_id>/<run_id>/` via atomic exclusive mkdir. On the
        astronomically-unlikely collision, mint a NEW id — never overwrite."""
        if not task_id or "/" in task_id or task_id.startswith("."):
            raise EvidenceError(f"unsafe task_id: {task_id!r}")
        parent = self.root / task_id
        for _ in range(_ALLOC_TRIES):
            run_id = new_run_id(task_id, now)
            d = parent / run_id
            try:
                d.mkdir(parents=True, exist_ok=False)  # leaf must not pre-exist
            except FileExistsError:
                continue  # collision -> new id, never reuse
            return RunDir(path=d, task_id=task_id, run_id=run_id)
        raise EvidenceError(
            f"could not allocate a unique run dir for {task_id!r} after {_ALLOC_TRIES} tries"
        )


# ---------------------------------------------------------------------------
# Integrity verification
# ---------------------------------------------------------------------------

COMPLETE, INCOMPLETE, CORRUPT = "COMPLETE", "INCOMPLETE", "CORRUPT"


@dataclass
class VerifyReport:
    run_dir: str
    status: str                                    # COMPLETE | INCOMPLETE | CORRUPT
    reason: str = ""
    missing: list[str] = field(default_factory=list)     # in manifest, absent on disk
    extra: list[str] = field(default_factory=list)       # on disk, absent from manifest
    mismatched: list[str] = field(default_factory=list)  # present but wrong hash

    @property
    def ok(self) -> bool:
        return self.status == COMPLETE


def _parse_manifest(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        line = line.rstrip("\n")
        if not line.strip():
            continue
        digest, _, rel = line.partition("  ")
        out[rel] = digest
    return out


def verify_run(run_dir: str | os.PathLike) -> VerifyReport:
    """Check a run dir against its manifest.

    No manifest        -> INCOMPLETE (crash mid-write; quarantine, don't repair).
    Any missing/extra/mismatched file -> CORRUPT.
    Otherwise          -> COMPLETE.
    """
    d = Path(run_dir)
    rep = VerifyReport(run_dir=str(d), status=COMPLETE)
    manifest_path = d / MANIFEST_NAME
    if not d.is_dir():
        rep.status = INCOMPLETE
        rep.reason = "run dir does not exist"
        return rep
    if not manifest_path.exists():
        rep.status = INCOMPLETE
        rep.reason = f"no {MANIFEST_NAME}: run never completed (crash mid-write) — quarantine"
        return rep

    expected = _parse_manifest(manifest_path.read_text(encoding="utf-8"))
    on_disk = {
        p.relative_to(d).as_posix()
        for p in d.rglob("*")
        if p.is_file() and p.name != MANIFEST_NAME and not p.name.startswith(".")
    }

    rep.missing = sorted(set(expected) - on_disk)
    rep.extra = sorted(on_disk - set(expected))
    for rel in sorted(set(expected) & on_disk):
        if sha256_file(d / rel) != expected[rel]:
            rep.mismatched.append(rel)

    if rep.missing or rep.extra or rep.mismatched:
        rep.status = CORRUPT
        rep.reason = (f"manifest mismatch: missing={len(rep.missing)} "
                      f"extra={len(rep.extra)} mismatched={len(rep.mismatched)}")
    return rep
