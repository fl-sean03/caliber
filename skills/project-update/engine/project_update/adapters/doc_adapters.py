"""Doc adapters — read + diff a project's narrative docs.

Heterogeneity is real: hydrogenation has the full STATUS/TRACKER/CHANGELOG/AGENTS
quad; some projects have AGENTS+STATUS, AGENTS+ROADMAP, or README-only. Each
adapter knows how to pull the "CLAIMED work" signal out of whichever docs a
project actually has. The engine auto-selects the adapter from the manifest's
declared+present docs (see manifest.Project.doc_adapter).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .. import gitlog

if TYPE_CHECKING:
    from ..manifest import Project

# A "claim" = something the project's own docs assert happened/changed.
_ICON_DONE = "✅"
_ICON_INPROGRESS = "🟡"
_WS_ROW_RE = re.compile(r"\|\s*\*?\*?(W\d+(?:\.\w+)?)\*?\*?\s*\|")
_D_ROW_RE = re.compile(r"\|\s*\*?\*?(D\.\d+)\*?\*?\s*\|")

# The red blocked/decision-needed icon — when present in pi_flag_markers it
# ALWAYS escalates a row (even ⏸/🟡), because 🔴 is itself the escalation.
_PI_FLAG_ICON = "🔴"


@dataclass
class DocClaim:
    """One asserted item pulled from a narrative doc diff."""
    doc: str           # which doc (tracker/status/changelog)
    kind: str          # 'status-flip' | 'new-row' | 'decision' | 'changelog-entry'
    text: str          # the line/snippet
    workstream: str = ""  # W4.10b etc. if detectable


@dataclass
class StatusFocus:
    """The project's own SCIENTIFIC framing, pulled from STATUS.md. This is the
    meeting's scientific lead — prose the project author wrote, not git subjects.

      focus_prose      : the paragraphs under `## Current focus` (up to next `##`)
      headline_table   : the `## Canonical headline numbers` markdown table rows.
    Both may be empty for projects whose STATUS lacks these exact headings.
    """
    focus_prose: str = ""
    headline_table: str = ""

    @property
    def present(self) -> bool:
        return bool(self.focus_prose or self.headline_table)

    def first_sentence(self) -> str:
        """First sentence of the focus prose, markdown stripped — for a terse
        opening line. Empty if no prose."""
        if not self.focus_prose:
            return ""
        para = next((p for p in self.focus_prose.split("\n\n") if p.strip()), "")
        flat = re.sub(r"\s+", " ", para).strip()
        flat = flat.replace("**", "").replace("`", "")
        m = re.search(r"(.+?[.!?])(\s|$)", flat)
        return (m.group(1) if m else flat).strip()

    def top_headline_number(self) -> str:
        """The single most salient headline number, as a 'Metric: Value' string.
        Prefers a row whose value carries a bolded figure; else the first data
        row. Empty if no table."""
        for line in self.headline_table.splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 2:
                continue
            metric, value = cells[0], cells[-1]
            if not metric or set(metric) <= set("-: "):
                continue
            if metric.lower() in {"metric", ""}:
                continue
            if "**" in value:
                return f"{metric}: {_strip_md(value)}"
        for line in self.headline_table.splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 2:
                continue
            metric, value = cells[0], cells[-1]
            if not metric or set(metric) <= set("-: ") or metric.lower() == "metric":
                continue
            return f"{metric}: {_strip_md(value)}"
        return ""


def _strip_md(s: str) -> str:
    return s.replace("**", "").replace("`", "").strip()


def extract_status_focus(status_text: str) -> StatusFocus:
    """Pull the `## Current focus` prose and the `## Canonical headline numbers`
    table out of a STATUS.md body. Robust to absence: returns an empty StatusFocus
    if the headings are missing. Heading match is case-insensitive and tolerant of
    trailing parenthetical text (e.g. `## Current focus (scientific framing)`)."""
    focus = _section_body(status_text, r"current focus")
    focus = re.sub(r"\n+-{3,}\s*$", "", focus.strip())
    table = _first_table(_section_body(status_text, r"canonical headline numbers"))
    return StatusFocus(focus_prose=focus.strip(), headline_table=table.strip())


_H2_RE = re.compile(r"^##\s+(.*?)\s*$")


def _section_body(text: str, heading_pattern: str) -> str:
    """Return the body lines under the first `## <heading_pattern>` up to the next
    `##` heading. Empty string if the heading is absent."""
    want = re.compile(heading_pattern, re.IGNORECASE)
    lines = text.splitlines()
    out: list = []
    capturing = False
    for line in lines:
        m = _H2_RE.match(line)
        if m:
            if capturing:
                break
            if want.match(m.group(1)) or want.search(m.group(1)):
                capturing = True
            continue
        if capturing:
            out.append(line)
    return "\n".join(out)


def _first_table(text: str) -> str:
    """Return the first contiguous markdown table (`| ... |` lines) in `text`."""
    rows: list = []
    started = False
    for line in text.splitlines():
        if line.lstrip().startswith("|"):
            rows.append(line.rstrip())
            started = True
        elif started:
            break
    return "\n".join(rows)


@dataclass
class ChangelogEntry:
    """One dated CHANGELOG entry — the heading date + a short gist. The dated
    headings (`## 2026-05-25 (afternoon): pivot to amilan ...`) ARE the week's
    story; in-window entries lead the synthesis 'what happened'."""
    date: str          # display date, may carry a time-of-day parenthetical
    heading: str       # the heading text after the date (e.g. "pivot to ...")
    gist: str = ""     # 1-2 line gist from the entry body
    iso_date: str = "" # bare YYYY-MM-DD for window comparison/sorting


_CHANGELOG_HEADING_RE = re.compile(
    r"^##\s+(\d{4}-\d{2}-\d{2})\s*(.*?)\s*$")


def parse_changelog_entries(text: str) -> list:
    """Parse a CHANGELOG body into dated entries (newest-first as written).
    Each entry = the `## <date> ...` heading + a short gist from its first
    bullet/sentence. Robust to absence (returns [])."""
    lines = text.splitlines()
    entries: list = []
    cur: ChangelogEntry | None = None
    body: list = []

    def _flush() -> None:
        if cur is not None:
            cur.gist = _changelog_gist(body)
            entries.append(cur)

    for line in lines:
        m = _CHANGELOG_HEADING_RE.match(line)
        if m:
            _flush()
            iso_date = m.group(1)
            date = iso_date
            heading = m.group(2).lstrip(":").strip()
            heading = re.sub(r"\s+", " ", heading)
            pm = re.match(r"^\((?P<paren>[^)]*)\)\s*:?\s*(?P<rest>.*)$", heading)
            if pm:
                date = f"{date} ({pm.group('paren')})"
                heading = pm.group("rest").strip()
            cur = ChangelogEntry(date=date, heading=heading, iso_date=iso_date)
            body = []
        elif cur is not None:
            body.append(line)
    _flush()
    return entries


def _changelog_gist(body: list) -> str:
    """Pull a 1-2 line gist from a changelog entry body: the first 1-2 non-empty
    bullet/prose lines, markdown stripped and trimmed."""
    picked: list = []
    for raw in body:
        s = raw.strip()
        if not s or set(s) <= set("-*# "):
            continue
        s = s.lstrip("-*").strip()
        s = _strip_md(s)
        if s:
            picked.append(s)
        if len(picked) >= 2:
            break
    gist = " ".join(picked)
    if len(gist) > 240:
        gist = gist[:237].rstrip() + "..."
    return gist


def changelog_entries_in_window(text: str, since: str, until: str | None) -> list:
    """The dated CHANGELOG entries whose heading date falls within [since, until]
    (until inclusive; open-ended if until is None)."""
    out = []
    for e in parse_changelog_entries(text):
        if e.iso_date < since:
            continue
        if until and e.iso_date > until:
            continue
        out.append(e)
    return out


@dataclass
class PiFlaggedAsk:
    """A WORKSTREAM row flagged for the PI (🔴 / 'flag to Hendrik' / 'PI confirm'
    / 'sign-off'). This is the most important kind of open ask — it lives in the
    workstream table, NOT the D.N decision queue, and must lead the 'Ask PI' list
    above the D.N items."""
    workstream: str    # e.g. "W2.25"
    directive: str     # the ask / decision text (the row's 2nd cell)
    recommendation: str = ""  # the recommendation / notes (the row's last cell)


@dataclass
class DocReading:
    adapter: str
    docs_present: list = field(default_factory=list)
    docs_missing: list = field(default_factory=list)
    claims: list = field(default_factory=list)        # list[DocClaim]
    diffs: dict = field(default_factory=dict)          # doc_key -> raw unified diff
    open_decisions: list = field(default_factory=list) # rows from PI-decision queue
    pi_flagged_asks: list = field(default_factory=list)  # list[PiFlaggedAsk]
    changelog_entries: list = field(default_factory=list)  # in-window ChangelogEntry list
    status_focus: StatusFocus = field(default_factory=StatusFocus)  # scientific lead


class DocAdapter:
    """Base doc adapter. Reads the project's docs over a window."""

    name = "base"
    doc_keys: tuple = ()

    def read(self, project: Project, since: str, until: str | None) -> DocReading:
        reading = DocReading(adapter=self.name)
        for key in self.doc_keys:
            path = project.doc_path(key)
            if path and path.exists():
                reading.docs_present.append(key)
                diff = gitlog.doc_diff(project.repo, project.docs[key], since, until)
                if diff:
                    reading.diffs[key] = diff
                    reading.claims.extend(self._claims_from_diff(key, diff))
            elif key in project.docs:
                reading.docs_missing.append(key)
        status_path = project.doc_path("status")
        if status_path and status_path.exists():
            reading.status_focus = extract_status_focus(
                status_path.read_text(encoding="utf-8"))
        changelog_path = project.doc_path("changelog")
        if changelog_path and changelog_path.exists():
            reading.changelog_entries = changelog_entries_in_window(
                changelog_path.read_text(encoding="utf-8"), since, until)
        return reading

    def _claims_from_diff(self, doc_key: str, diff: str) -> list:
        """Extract added lines that look like progress assertions."""
        claims: list = []
        for line in diff.splitlines():
            if not line.startswith("+") or line.startswith("+++"):
                continue
            content = line[1:].strip()
            if not content:
                continue
            ws = ""
            m = _WS_ROW_RE.search(content)
            if m:
                ws = m.group(1)
            if _ICON_DONE in content:
                claims.append(DocClaim(doc=doc_key, kind="status-flip", text=content, workstream=ws))
            elif _ICON_INPROGRESS in content and ws:
                claims.append(DocClaim(doc=doc_key, kind="new-row", text=content, workstream=ws))
            elif doc_key == "changelog" and content.startswith(("- ", "* ", "#")):
                claims.append(DocClaim(doc=doc_key, kind="changelog-entry", text=content))
        return claims


class QuadAdapter(DocAdapter):
    """STATUS + TRACKER + CHANGELOG + AGENTS (the gold standard)."""

    name = "quad"
    doc_keys = ("tracker", "status", "changelog")

    def read(self, project: Project, since: str, until: str | None) -> DocReading:
        reading = super().read(project, since, until)
        tracker = project.doc_path("tracker")
        if tracker and tracker.exists():
            text = tracker.read_text(encoding="utf-8")
            if project.tracker_format.get("pi_decision_queue"):
                reading.open_decisions = self._open_decisions(text)
            reading.pi_flagged_asks = pi_flagged_asks(text, project.pi_flag_markers())
        return reading

    @staticmethod
    def _open_decisions(text: str) -> list:
        rows: list = []
        for line in text.splitlines():
            m = _D_ROW_RE.search(line)
            if m and "✅" not in line and "CLOSED" not in line.upper():
                rows.append(line.strip())
        return rows


def _build_escalation_re(markers: list) -> re.Pattern | None:
    """Build a case-insensitive phrase regex from the non-icon markers in
    pi_flag_markers. The 🔴 icon is handled separately (it always escalates)."""
    phrases = [m for m in markers if m and m != _PI_FLAG_ICON and not _is_icon(m)]
    if not phrases:
        return None
    # tolerate "sign-off"/"signoff" and "needs pi confirm"/"need pi confirm"
    parts = []
    for p in phrases:
        esc = re.escape(p.strip())
        esc = esc.replace(r"sign\-off", r"sign-?off")
        esc = esc.replace(r"needs\ ", r"needs?\\s+")
        esc = esc.replace(r"\ ", r"\\s+")
        parts.append(esc)
    return re.compile("|".join(parts), re.IGNORECASE)


def _is_icon(s: str) -> bool:
    """A marker is an 'icon' (matched verbatim, anywhere) if it has no ascii
    letters — e.g. an emoji. Phrase markers carry letters."""
    return not any(ch.isalpha() and ch.isascii() for ch in s)


def pi_flagged_asks(text: str, markers: list | None = None) -> list:
    """Scan a TRACKER for WORKSTREAM rows flagged for the PI per `markers`
    (pi_flag_markers from the manifest). 🔴 (or any non-letter icon marker)
    ALWAYS escalates. A letter-phrase marker ('flag to Hendrik', 'Needs PI
    confirm', 'sign-off') escalates UNLESS the row is merely ⏸/🟡 (a forward
    dependency on someone else's sign-off, not its own PI ask). Returns
    PiFlaggedAsk with the workstream id, directive (2nd cell), and recommendation
    (last cell). D.N decision rows are NOT collected here."""
    markers = markers or ["🔴", "flag to hendrik", "needs pi confirm",
                          "pi confirm", "sign-off", "flag to pi"]
    icon_markers = [m for m in markers if m and _is_icon(m)]
    esc_re = _build_escalation_re(markers)
    asks: list = []
    seen: set = set()
    for line in text.splitlines():
        m = _WS_ROW_RE.search(line)
        if not m:
            continue
        ws = m.group(1)
        if any(icon in line for icon in icon_markers):
            triggered = True
        elif esc_re and esc_re.search(line) and not (
            _ICON_INPROGRESS in line or "⏸" in line):
            triggered = True
        else:
            triggered = False
        if not triggered:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        cells = [c for c in cells if c]
        directive = ""
        recommendation = ""
        id_idx = next(
            (i for i, c in enumerate(cells)
             if _WS_ROW_RE.search(f"|{c}|")), None)
        if id_idx is not None and id_idx + 1 < len(cells):
            directive = _strip_md(cells[id_idx + 1])
            if len(cells) - 1 > id_idx + 1:
                recommendation = _strip_md(cells[-1])
        if not directive:
            continue
        key = (ws, directive[:60])
        if key in seen:
            continue
        seen.add(key)
        asks.append(PiFlaggedAsk(
            workstream=ws, directive=directive, recommendation=recommendation))
    return asks


class AgentsRoadmapAdapter(DocAdapter):
    """AGENTS + ROADMAP only (e.g. SolvationFE). No status/tracker/changelog."""

    name = "agents_roadmap"
    doc_keys = ("roadmap",)


class AgentsStatusAdapter(DocAdapter):
    """AGENTS + STATUS only (e.g. ALCF hub)."""

    name = "agents_status"
    doc_keys = ("status",)


class ReadmeOnlyAdapter(DocAdapter):
    """README.md only — the minimal git-only source.

    For repos with no AGENTS/STATUS/TRACKER: there is no structured claim doc to
    reconcile against, so this adapter mines git + mtimes only (in the aggregator)
    and exposes README as the narrative doc. It surfaces NO claims — nothing to
    flag as drift; the digest reports what git shows."""

    name = "readme_only"
    doc_keys = ("readme",)

    def _claims_from_diff(self, doc_key: str, diff: str) -> list:
        return []


DOC_ADAPTERS = {
    QuadAdapter.name: QuadAdapter,
    AgentsRoadmapAdapter.name: AgentsRoadmapAdapter,
    AgentsStatusAdapter.name: AgentsStatusAdapter,
    ReadmeOnlyAdapter.name: ReadmeOnlyAdapter,
    DocAdapter.name: DocAdapter,
}


def get_doc_adapter(name: str) -> DocAdapter:
    cls = DOC_ADAPTERS.get(name, DocAdapter)
    return cls()
