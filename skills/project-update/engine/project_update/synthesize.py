"""Synthesizer — work ledger -> PI-aware markdown synthesis.

Mirrors the format proven in 31-Hydrogenation's 2026-05-15 synthesis.md
(Hendrik-tested): scientific focus (STATUS), this-week's-developments
(CHANGELOG), milestones (doc-only, kept OUT of drift), activity ledger,
claimed-vs-real drift, and the open PI-decision queue with 🔴 PI-flagged
workstream asks pulled to the lead.

PI preferences shape what's surfaced:
  - data not advocacy   -> reconciliation is shown plainly, flagged not spun
  - scientific/policy vs engineering split (don't escalate engineering)
  - detail + clear status per workstream
"""
from __future__ import annotations

from pathlib import Path

from .aggregate import WorkLedger
from .manifest import Project

_PREFIX_LABEL = {
    "feat": "feature / new capability",
    "fix": "bug fix",
    "compute": "compute / production",
    "docs": "documentation",
    "refactor": "refactor",
    "polish": "polish",
    "chore": "chore",
}

# Engineering scopes that should NOT be escalated as PI-facing science.
_ENGINEERING_SCOPES = {"compute", "chore", "refactor"}

# Conventional-commit prefix priority for headline / 90-second-opening ranking.
# Science/production first, tooling/housekeeping last. A PI 1:1 should lead with
# a `feat` (new capability) or `compute` (production run), never a refactor.
# Lower number = higher priority.
_PREFIX_PRIORITY = {
    "feat": 0,
    "compute": 0,
    "fix": 1,
    "polish": 2,
    "refactor": 3,
    "docs": 4,
    "chore": 5,
}
_PREFIX_PRIORITY_DEFAULT = 6  # unknown / no-prefix commits rank below known ones


def rank_commits_for_headline(commits: list) -> list:
    """Order non-doc commits so the most PI-significant change leads.

    Primary key: conventional-commit prefix priority (science/production first,
    tooling/housekeeping last — see _PREFIX_PRIORITY). Tie-break within a prefix
    preserves the existing behaviour (file-count desc, then recency, which is the
    incoming order from git: newest first).
    """
    substance = [c for c in commits if (c.get("prefix") or "") != "docs"]
    indexed = sorted(
        enumerate(substance),
        key=lambda ic: (
            _PREFIX_PRIORITY.get(ic[1].get("prefix") or "", _PREFIX_PRIORITY_DEFAULT),
            -(ic[1].get("n_files") or 0),
            ic[0],
        ),
    )
    return [c for _, c in indexed]


def synthesize(project: Project, ledger: WorkLedger, *, version: str = "dev") -> str:
    window = f"{ledger.since} → {ledger.until or 'now'}"
    lines: list = []
    a = lines.append

    a(f"# Synthesis — {project.name} · {window}")
    a("")
    a(f"**Generated:** {ledger.generated} · project-update@{version} · "
      f"HEAD `{ledger.head_sha[:10]}`")
    a(f"**PI:** {project.pi} · **cadence:** {project.cadence}")
    a("")
    a("> What actually happened this window, reconciled against what the project's")
    a("> own docs claim. Organized for a PI 1:1: science first, engineering as FYI,")
    a("> data-not-advocacy framing throughout.")
    a("")

    _section_scientific_focus(a, ledger)
    _section_this_week(a, ledger)
    _section_headline(a, ledger)
    _section_milestones(a, ledger)
    _section_reconciliation(a, ledger)
    _section_engineering_split(a, project, ledger)
    _section_decisions(a, ledger)
    _section_watch(a, ledger)
    _section_tldr(a, ledger)

    a("")
    a("---")
    a("_project-update synthesis (Tier-1, single-repo). Source material stays "
      "canonical in this project's own docs + `updates/`. This doc is a "
      "reconciliation, not a replacement._")
    return "\n".join(lines) + "\n"


def _section_scientific_focus(a, ledger: WorkLedger) -> None:
    """The meeting's scientific LEAD — the project's own framing from STATUS.md
    (Current focus prose + Canonical headline numbers), rendered above the commit
    activity ledger. Skipped cleanly when STATUS has no such headings."""
    sf = ledger.scientific_focus
    if not sf:
        return
    a("## Scientific focus (from STATUS.md)")
    a("")
    a("> The project's OWN scientific framing — the meeting's lead. This is what "
      "the science is about; the commit activity below is the supporting ledger.")
    a("")
    if sf.get("focus_prose"):
        a(sf["focus_prose"])
        a("")
    if sf.get("headline_table"):
        a("**Canonical headline numbers:**")
        a("")
        a(sf["headline_table"])
        a("")


def _section_this_week(a, ledger: WorkLedger) -> None:
    """The actual news this window — the dated CHANGELOG entries in [since, until].
    Placed after the scientific framing but ABOVE the commit activity ledger,
    because the CHANGELOG narrative is the week's story. Skipped cleanly when the
    CHANGELOG is absent or has no in-window entries."""
    entries = ledger.changelog_entries
    if not entries:
        return
    a("## This week's developments (from CHANGELOG)")
    a("")
    a("> What actually changed THIS window, per the project's own CHANGELOG — the "
      "narrative of the week, above the raw commit ledger.")
    a("")
    for e in entries[:12]:
        head = e["heading"] or "(update)"
        line = f"- **{e['date']}** — {head}"
        if e.get("gist") and e["gist"] != head:
            line += f": {e['gist']}"
        a(line)
    a("")


def _section_headline(a, ledger: WorkLedger) -> None:
    a("## What moved this window (activity ledger)")
    a("")
    n = len(ledger.commits)
    if n == 0:
        a("No commits in the window. (Check mtime evidence below — work may be "
          "uncommitted.)")
        a("")
    else:
        prefixes = ", ".join(
            f"{c} {_PREFIX_LABEL.get(k, k)}" for k, c in
            sorted(ledger.commit_prefix_counts.items(), key=lambda kv: -kv[1])
        )
        a(f"**{n} commits** — {prefixes}.")
        a("")
        top = list(ledger.touched_paths.items())[:6]
        if top:
            a("Touched areas (by commit-file count): "
              + ", ".join(f"`{d}` ({c})" for d, c in top) + ".")
            a("")
        substance = rank_commits_for_headline(ledger.commits)
        if substance:
            a("**The substance:**")
            a("")
            for c in substance[:10]:
                a(f"- `{c['sha']}` **{c['prefix'] or '—'}** · {c['subject']}")
            a("")
    if ledger.doc_only_milestones:
        top = _top_milestone(ledger.doc_only_milestones)
        a(f"**Milestone win:** {_milestone_text(top)}")
        a("")


def _top_milestone(milestones: list) -> dict:
    """Pick the single most-headline-worthy milestone. Prefer ones mentioning an
    allocation/award magnitude (node-hr) so the biggest external win leads."""
    def score(m: dict) -> int:
        t = m["text"].lower()
        s = 0
        if "node-hr" in t or "node-hour" in t:
            s += 2
        if "approved" in t or "awarded" in t or "accepted" in t:
            s += 1
        return -s
    return sorted(milestones, key=score)[0]


def _strip_leading_ws(cleaned: str, ws: str) -> str:
    """Drop a leading workstream-id cell from a cleaned row so it is not emitted
    twice when the caller re-prefixes `**{ws}**`."""
    if not ws:
        return cleaned
    candidate = cleaned.lstrip("*").strip()
    if candidate.startswith(ws):
        rest = candidate[len(ws):].lstrip("*")
        return rest.lstrip(" ·")
    return cleaned


def _milestone_text(m: dict) -> str:
    ws = m.get("workstream", "")
    cleaned = _strip_leading_ws(_clean(m["text"]), ws)
    prefix = f"**{ws}** " if ws else ""
    return f"{prefix}{cleaned}"


def _section_milestones(a, ledger: WorkLedger) -> None:
    if not ledger.doc_only_milestones:
        return
    a("## Milestones (doc-only, externally evidenced)")
    a("")
    a("External / administrative wins this window — approvals, allocations, "
      "account grants, emailed decisions. These legitimately have no code/file "
      "evidence (the evidence lives in email/portal, not git), so they are NOT "
      "drift — surface them as wins, not as claims to second-guess.")
    a("")
    for m in ledger.doc_only_milestones[:10]:
        a(f"- {_milestone_text(m)}")
    a("")


def _section_reconciliation(a, ledger: WorkLedger) -> None:
    a("## Claimed vs. real (drift check)")
    a("")
    a(f"- ✅ **Confirmed** (claimed AND evidenced): {len(ledger.confirmed)}")
    a(f"- ⚠️ **Claimed-not-evidenced** (doc says it, no commit/file backs it — "
      f"verify before telling the PI): {len(ledger.claimed_not_evidenced)}")
    a(f"- 🔍 **Evidenced-not-claimed** (real work the docs missed): "
      f"{len(ledger.evidenced_not_claimed)}")
    if ledger.doc_only_milestones:
        a(f"- 🏆 **Doc-only milestones** (external/administrative — not drift, "
          f"see above): {len(ledger.doc_only_milestones)}")
    a("")
    if ledger.claimed_not_evidenced:
        a("### ⚠️ Verify these claims")
        a("")
        for r in ledger.claimed_not_evidenced[:12]:
            ws = r["workstream"]
            cleaned = _strip_leading_ws(_clean(r["text"]), ws)
            prefix = f"**{ws}** " if ws else ""
            a(f"- {prefix}{cleaned}")
        a("")
        a("_External/administrative milestones (approvals, allocations, account "
          "grants) have been split out into the Milestones section above — those "
          "are not drift. The items here are remaining ✅-done code/analysis claims "
          "with no commit backing them. Read each before flagging to the PI._")
        a("")
    if ledger.evidenced_not_claimed:
        a("### 🔍 Real work the docs didn't log")
        a("")
        for e in ledger.evidenced_not_claimed[:10]:
            a(f"- `{e['sha']}` **{e['prefix']}** · {e['subject']} — _no TRACKER row references this; "
              "candidate to add._")
        a("")


def _section_engineering_split(a, project: Project, ledger: WorkLedger) -> None:
    eng = [c for c in ledger.commits if (c["scope"] or c["prefix"]) in _ENGINEERING_SCOPES
           or (c["prefix"] in _ENGINEERING_SCOPES)]
    if not eng:
        return
    a("## Engineering / infra (FYI — closed autonomously, do NOT escalate)")
    a("")
    a("_Per feedback_dont_escalate_engineering: compute routing, sizing, queue "
      "choices are autonomous. Mention to the PI only as status, never as a question._")
    a("")
    for c in eng[:8]:
        a(f"- `{c['sha']}` {c['subject']}")
    a("")


def _render_pi_flagged_asks(a, ledger: WorkLedger) -> None:
    """Render the PI-flagged WORKSTREAM asks (🔴 flag-to-PI / PI-confirm rows) as
    the LEAD of the 'Ask PI' list — these outrank the D.N queue because they are
    active, blocking, PI-escalated workstream decisions."""
    for ask in ledger.pi_flagged_asks:
        ws = ask["workstream"]
        directive = ask["directive"]
        line = f"- **{ws}** {directive}"
        if ask.get("recommendation"):
            line += f" — _{ask['recommendation']}_"
        a(line)


def _section_decisions(a, ledger: WorkLedger) -> None:
    if not ledger.open_decisions and not ledger.pi_flagged_asks:
        return
    a("## Open PI-decision queue (pull-forward)")
    a("")
    if ledger.pi_flagged_asks:
        a("**🔴 PI-flagged workstream asks (lead — these are blocking, raise "
          "first):**")
        a("")
        _render_pi_flagged_asks(a, ledger)
        a("")
    if ledger.open_decisions:
        a("Unresolved items from the project's TRACKER decision table — resurface "
          "so they don't get lost between meetings:")
        a("")
        for d in ledger.open_decisions[:12]:
            a(f"- {_clean(d)}")
        a("")


def _section_watch(a, ledger: WorkLedger) -> None:
    a("## Things to watch")
    a("")
    watch = []
    if ledger.claimed_not_evidenced:
        watch.append(
            f"{len(ledger.claimed_not_evidenced)} claims lack code/file evidence — "
            "confirm they're real-but-doc-only vs. drift.")
    if ledger.evidenced_not_claimed:
        watch.append(
            f"{len(ledger.evidenced_not_claimed)} commits did work the TRACKER never "
            "logged — the project agent may have forgotten to record them.")
    uncommitted = [f for f in ledger.evidence_files
                   if f["mtime"][:10] not in {c["date"] for c in ledger.commits}]
    if uncommitted:
        watch.append(
            f"{len(uncommitted)} evidence files changed on dates with no commit "
            "(possible uncommitted output).")
    if not watch:
        watch.append("Nothing flagged — claimed and real are in sync this window.")
    for w in watch:
        a(f"- {w}")
    a("")


def _section_tldr(a, ledger: WorkLedger) -> None:
    a("## TL;DR")
    a("")
    a("| Signal | Count |")
    a("|---|---:|")
    a(f"| Commits | {len(ledger.commits)} |")
    a(f"| Confirmed claims | {len(ledger.confirmed)} |")
    a(f"| Claims to verify | {len(ledger.claimed_not_evidenced)} |")
    a(f"| Unlogged real work | {len(ledger.evidenced_not_claimed)} |")
    a(f"| Evidence files touched | {len(ledger.evidence_files)} |")
    a(f"| Open PI decisions | {len(ledger.open_decisions)} |")
    a("")


def _clean(text: str) -> str:
    """Trim a raw TRACKER row down to readable prose."""
    t = text.strip()
    if t.startswith("|"):
        cells = [c.strip() for c in t.strip("|").split("|")]
        cells = [c for c in cells if c]
        return " · ".join(cells[:4])
    return t


def write_synthesis(text: str, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    return out_path
