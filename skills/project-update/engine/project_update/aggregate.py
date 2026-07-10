"""Aggregator — reconstruct "what actually happened" into a work ledger.

Given a project + time window, mine git (timestamp/path/prefix, NEVER author),
file mtimes, and narrative-doc diffs, then reconcile CLAIMED (what docs say) vs
REAL (what commits/files show) into three classes:

  confirmed             : claimed AND evidenced
  claimed_not_evidenced : doc says done, no commit/file backs it (flag)
  evidenced_not_claimed : real work the docs missed (candidate to surface)

Output is a structured dict (the "work ledger"), JSON-serializable.
"""
from __future__ import annotations

import datetime as _dt
import fnmatch
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import gitlog
from .adapters.doc_adapters import get_doc_adapter
from .manifest import Project

# Noise we never count as "real work" in the mtime scan.
_IGNORE_SUBSTR = (
    "/.git/",
    "/__pycache__/",
    "/.pytest_cache/",
    "/.ruff_cache/",
    "/node_modules/",
    "/.mypy_cache/",
)
_IGNORE_SUFFIX = (".pyc", ".log", ".aux", ".swp")


@dataclass
class WorkLedger:
    project: str
    repo: str
    since: str
    until: str | None
    generated: str
    head_sha: str = ""
    # REAL signals
    commits: list = field(default_factory=list)      # list[dict]
    commit_prefix_counts: dict = field(default_factory=dict)
    touched_paths: dict = field(default_factory=dict)  # top-level dir -> count
    evidence_files: list = field(default_factory=list)  # mtime-detected work
    # CLAIMED signals
    doc_claims: list = field(default_factory=list)     # list[dict]
    open_decisions: list = field(default_factory=list)
    # PI-flagged WORKSTREAM asks (🔴 flag-to-Hendrik / PI-confirm rows). These are
    # the most important open asks and lead the "Ask PI" list above the D.N
    # decision queue. Each: {"workstream", "directive", "recommendation"}.
    pi_flagged_asks: list = field(default_factory=list)
    # in-window CHANGELOG developments (the actual news this window). Each:
    # {"date", "heading", "gist"}. Newest-first as written in the CHANGELOG.
    changelog_entries: list = field(default_factory=list)
    docs_present: list = field(default_factory=list)
    docs_missing: list = field(default_factory=list)
    diffs: dict = field(default_factory=dict)
    # reconciliation
    confirmed: list = field(default_factory=list)
    claimed_not_evidenced: list = field(default_factory=list)
    evidenced_not_claimed: list = field(default_factory=list)
    # doc-only milestones: claimed items that are external/administrative events
    # (approvals, allocations, account grants) which legitimately have no code
    # evidence — NOT suspect drift. Surfaced in a positively-framed bucket.
    doc_only_milestones: list = field(default_factory=list)
    # the project's own SCIENTIFIC framing (STATUS "Current focus" prose + the
    # canonical headline-numbers table). This is the meeting's scientific lead.
    scientific_focus: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def _to_epoch(date_str: str) -> float:
    return _dt.datetime.strptime(date_str, "%Y-%m-%d").timestamp()


def _scan_mtimes(repo: Path, globs: list, since: str, until: str | None) -> list:
    """Find files matching evidence_globs modified in window (catches uncommitted work)."""
    if not globs:
        return []
    start = _to_epoch(since)
    end = _to_epoch(until) + 86400 if until else None
    found: list = []
    for pattern in globs:
        for root, dirs, files in os.walk(repo):
            dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
            for fn in files:
                full = Path(root) / fn
                rel = str(full.relative_to(repo))
                if not _glob_match(rel, pattern):
                    continue
                if any(s in f"/{rel}" for s in _IGNORE_SUBSTR):
                    continue
                if rel.endswith(_IGNORE_SUFFIX):
                    continue
                try:
                    mt = full.stat().st_mtime
                except OSError:
                    continue
                if mt < start:
                    continue
                if end and mt >= end:
                    continue
                found.append(
                    {
                        "path": rel,
                        "mtime": _dt.datetime.fromtimestamp(mt).isoformat(timespec="seconds"),
                    }
                )
    seen = set()
    uniq = []
    for f in found:
        if f["path"] not in seen:
            seen.add(f["path"])
            uniq.append(f)
    return sorted(uniq, key=lambda f: f["mtime"])


def _glob_match(rel: str, pattern: str) -> bool:
    if "**" in pattern:
        pre, _, post = pattern.partition("**/")
        if pre and not rel.startswith(pre):
            return False
        return fnmatch.fnmatch(rel, f"{pre}*{post}") or fnmatch.fnmatch(
            rel.rsplit("/", 1)[-1] if "/" in rel else rel, post
        ) or fnmatch.fnmatch(rel, pattern.replace("**/", "*/")) or _deep_match(rel, pre, post)
    return fnmatch.fnmatch(rel, pattern)


def _deep_match(rel: str, pre: str, post: str) -> bool:
    if pre and not rel.startswith(pre):
        return False
    tail = rel[len(pre):] if pre else rel
    return fnmatch.fnmatch(tail.rsplit("/", 1)[-1], post)


def _top_dir(path: str) -> str:
    return path.split("/", 1)[0] if "/" in path else path


def aggregate(project: Project, since: str, until: str | None = None) -> WorkLedger:
    repo = project.repo
    ledger = WorkLedger(
        project=project.id,
        repo=str(repo),
        since=since,
        until=until,
        generated=_dt.datetime.now().isoformat(timespec="seconds"),
    )
    if not gitlog.is_git_repo(repo):
        raise RuntimeError(f"{repo} is not a git repo")
    ledger.head_sha = gitlog.head_sha(repo)

    # --- REAL: git ---
    commits = gitlog.log_window(repo, since, until)
    prefix_counts: dict = {}
    touched: dict = {}
    for c in commits:
        ledger.commits.append(
            {"sha": c.sha[:10], "date": c.date, "subject": c.subject,
             "prefix": c.prefix, "scope": c.scope, "n_files": len(c.files)}
        )
        if c.prefix:
            prefix_counts[c.prefix] = prefix_counts.get(c.prefix, 0) + 1
        for f in c.files:
            td = _top_dir(f)
            touched[td] = touched.get(td, 0) + 1
    ledger.commit_prefix_counts = prefix_counts
    ledger.touched_paths = dict(sorted(touched.items(), key=lambda kv: -kv[1]))

    # --- REAL: mtime evidence ---
    ledger.evidence_files = _scan_mtimes(repo, project.evidence_globs, since, until)

    # --- CLAIMED: doc diffs ---
    adapter = get_doc_adapter(project.doc_adapter)
    reading = adapter.read(project, since, until)
    ledger.docs_present = reading.docs_present
    ledger.docs_missing = reading.docs_missing
    ledger.open_decisions = reading.open_decisions
    ledger.pi_flagged_asks = [
        {"workstream": a.workstream, "directive": a.directive,
         "recommendation": a.recommendation}
        for a in reading.pi_flagged_asks
    ]
    ledger.changelog_entries = [
        {"date": e.date, "heading": e.heading, "gist": e.gist}
        for e in reading.changelog_entries
    ]
    sf = reading.status_focus
    if sf.present:
        ledger.scientific_focus = {
            "focus_prose": sf.focus_prose,
            "headline_table": sf.headline_table,
            "first_sentence": sf.first_sentence(),
            "top_headline_number": sf.top_headline_number(),
        }
    ledger.diffs = {k: _truncate(v) for k, v in reading.diffs.items()}
    ledger.doc_claims = [
        {"doc": c.doc, "kind": c.kind, "text": c.text, "workstream": c.workstream}
        for c in reading.claims
    ]

    _reconcile(ledger)
    return ledger


def _truncate(diff: str, max_lines: int = 400) -> str:
    lines = diff.splitlines()
    if len(lines) <= max_lines:
        return diff
    return "\n".join(lines[:max_lines]) + f"\n... [{len(lines) - max_lines} more diff lines]"


def _reconcile(ledger: WorkLedger) -> None:
    """Build the three reconciliation classes.

    Corpus of REAL work = commit subjects + touched top-dirs + evidence-file paths.
    A CLAIM (a newly-added ✅/🟡 doc row) is *confirmed* if its distinctive
    keywords appear in that corpus; otherwise *claimed-not-evidenced* (flag).
    A commit is *evidenced-not-claimed* if it does real (non-doc) work whose
    distinctive keywords appear in NO doc claim added this window.
    """
    evidence_corpus = " ".join(c["subject"].lower() for c in ledger.commits)
    evidence_corpus += " " + " ".join(ledger.touched_paths.keys()).lower()
    evidence_corpus += " " + " ".join(f["path"].lower() for f in ledger.evidence_files)

    seen_claims = set()
    for claim in ledger.doc_claims:
        ws = claim["workstream"]
        text = claim["text"]
        key = (ws, text[:60])
        if key in seen_claims:
            continue
        seen_claims.add(key)
        if not ws:
            continue
        kws = _keywords(text)
        hit = any(k in evidence_corpus for k in kws) if kws else False
        record = {"workstream": ws, "kind": claim["kind"], "text": text[:200]}
        if hit:
            ledger.confirmed.append(record)
        elif _is_doc_only_milestone(text):
            ledger.doc_only_milestones.append(record)
        else:
            # Drift-list window-bleed guard: a ✅-done claim carrying a parseable
            # completion date STRICTLY before the window start wasn't claimed this
            # window — exclude it. Claims with no parseable date stay.
            done = _completion_date(text)
            if done and done < ledger.since:
                continue
            ledger.claimed_not_evidenced.append(record)

    claimed_blob = " ".join(c["text"].lower() for c in ledger.doc_claims)
    for c in ledger.commits:
        subj = c["subject"]
        prefix = c["prefix"] or ""
        if prefix == "docs":
            continue
        scope_kw = _keywords(subj)
        if scope_kw and not any(k in claimed_blob for k in scope_kw):
            ledger.evidenced_not_claimed.append(
                {"sha": c["sha"], "subject": subj, "prefix": prefix}
            )
    ledger.evidenced_not_claimed = _rank_evidenced(ledger.evidenced_not_claimed)
    ledger.confirmed = _dedupe_records(ledger.confirmed)
    ledger.claimed_not_evidenced = _dedupe_records(ledger.claimed_not_evidenced)
    ledger.doc_only_milestones = _dedupe_records(ledger.doc_only_milestones)


# Completion-date markers in a claimed ✅ row used to drop pre-window-completed
# claims from the drift "verify these claims" list (they weren't claimed THIS
# window).
_COMPLETION_DATE_RE = re.compile(
    r"(?:done|resolved|closed|delivered|completed|approved|sent|fixed|✅)\D{0,12}"
    r"(\d{4}-\d{2}-\d{2})",
    re.IGNORECASE,
)


def _completion_date(text: str) -> str | None:
    """Return the first parseable completion date (YYYY-MM-DD) attached to a
    done/resolved/✅ marker in the claim text, or None if none is parseable."""
    m = _COMPLETION_DATE_RE.search(text)
    return m.group(1) if m else None


_MILESTONE_RE = re.compile(
    r"\b(?:approved|approval|allocation|node-?hr(?:s)?|node-?hours?|grant(?:ed)?|"
    r"accept(?:ed)?|account(?:s)?|award(?:ed)?|incite|alcc)\b",
    re.IGNORECASE,
)
# DD (Director's Discretionary) / ALCC / INCITE programs — matched
# case-sensitively for DD so it doesn't fire on "add"/"odd" etc.
_PROGRAM_RE = re.compile(r"\b(?:DD|ALCC|INCITE)\b")


def _is_doc_only_milestone(text: str) -> bool:
    """True if a claim describes an external/administrative milestone (approval,
    allocation, account grant, emailed decision) — no code evidence expected."""
    return bool(_MILESTONE_RE.search(text) or _PROGRAM_RE.search(text))


def _dedupe_records(records: list) -> list:
    seen = set()
    out = []
    for r in records:
        k = (r.get("workstream", ""), r["text"][:60])
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out


_STOPWORDS = {
    "the", "and", "for", "with", "into", "from", "this", "that", "new", "add",
    "fix", "feat", "docs", "compute", "refactor", "polish", "chore", "update",
    "updated", "build", "via", "per", "all", "to", "of", "in", "on", "a", "an",
    "is", "are", "now", "plus", "after",
}


def _keywords(text: str) -> list:
    words = []
    for raw in text.replace("|", " ").replace("(", " ").replace(")", " ").split():
        w = raw.strip(".,:;`*#×—–-").lower()
        if len(w) >= 4 and w not in _STOPWORDS and not w.startswith("source"):
            words.append(w)
    return words[:8]


def _rank_evidenced(items: list) -> list:
    order = {"feat": 0, "compute": 1, "fix": 2, "refactor": 3, "polish": 4}
    return sorted(items, key=lambda it: order.get(it["prefix"], 9))[:25]
