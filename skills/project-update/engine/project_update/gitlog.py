"""Git mining — stdlib subprocess wrappers over `git`.

CRITICAL: aggregation NEVER keys on author. Every lab repo commits under the
single `fl-sean03` identity (verified). The "multi-agent reality" is concurrent
agents sharing ONE git identity. We key on timestamp + touched paths +
conventional-commit prefix instead.
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

_REC_SEP = "\x1e"  # record separator unlikely to appear in commit subjects
_FIELD_SEP = "\x1f"

_PREFIX_RE = re.compile(r"^([a-z]+)(?:\(([^)]*)\))?(!)?:\s")


@dataclass
class Commit:
    sha: str
    date: str  # ISO short YYYY-MM-DD
    iso: str  # full ISO timestamp
    subject: str
    files: list = field(default_factory=list)

    @property
    def prefix(self) -> str | None:
        m = _PREFIX_RE.match(self.subject)
        return m.group(1) if m else None

    @property
    def scope(self) -> str | None:
        m = _PREFIX_RE.match(self.subject)
        return m.group(2) if m else None


def _run_git(repo: Path, args: list) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed in {repo}:\n{proc.stderr.strip()}")
    return proc.stdout


def is_git_repo(repo: Path) -> bool:
    try:
        out = _run_git(repo, ["rev-parse", "--is-inside-work-tree"])
        return out.strip() == "true"
    except (RuntimeError, FileNotFoundError):
        return False


def repo_root(start: Path) -> Path | None:
    """Resolve the work-tree root from any path inside it (`git rev-parse
    --show-toplevel`). None if `start` is not inside a git repo."""
    try:
        out = _run_git(start, ["rev-parse", "--show-toplevel"])
        return Path(out.strip()) if out.strip() else None
    except (RuntimeError, FileNotFoundError):
        return None


def is_clean(repo: Path) -> bool:
    """True if working tree has no staged/unstaged changes (untracked OK)."""
    out = _run_git(repo, ["status", "--porcelain", "--untracked-files=no"])
    return out.strip() == ""


def current_branch(repo: Path) -> str:
    return _run_git(repo, ["rev-parse", "--abbrev-ref", "HEAD"]).strip()


def log_window(repo: Path, since: str, until: str | None = None) -> list:
    """Commits in [since, until). NEVER filtered by author."""
    fmt = _REC_SEP + _FIELD_SEP.join(["%H", "%ad", "%aI", "%s"])
    args = [
        "log",
        f"--since={since}",
        "--date=short",
        f"--pretty=format:{fmt}",
        "--name-only",
    ]
    if until:
        args.insert(2, f"--until={until}")
    raw = _run_git(repo, args)
    commits: list = []
    for record in raw.split(_REC_SEP):
        record = record.strip("\n")
        if not record.strip():
            continue
        header, _, body = record.partition("\n")
        parts = header.split(_FIELD_SEP)
        if len(parts) < 4:
            continue
        sha, date, iso, subject = parts[0], parts[1], parts[2], parts[3]
        files = [ln for ln in body.split("\n") if ln.strip()]
        commits.append(Commit(sha=sha, date=date, iso=iso, subject=subject, files=files))
    return commits


def doc_diff(repo: Path, doc_relpath: str, since: str, until: str | None = None) -> str:
    """Unified diff of one narrative doc across the window. This IS the project's
    own claim of what changed."""
    args = ["log", "-p", f"--since={since}", "--date=short"]
    if until:
        args.append(f"--until={until}")
    args += ["--", doc_relpath]
    try:
        return _run_git(repo, args)
    except RuntimeError:
        return ""


def head_sha(repo: Path) -> str:
    return _run_git(repo, ["rev-parse", "HEAD"]).strip()
