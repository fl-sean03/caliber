"""orient — an ephemeral "get me up to speed" brief for one project.

Reads the project's docs + recent git + evidence globs and renders a current-
state brief: open workstreams (incl. 🔴 PI-flagged asks), what moved since
`--since`, open PI decisions, and blockers. NOT a bundle — it is transient
(printed to stdout), per BUNDLE_CONTRACT.md ("orient output is NOT a bundle").
"""
from __future__ import annotations

from .aggregate import WorkLedger, aggregate
from .manifest import Project
from .synthesize import rank_commits_for_headline


def orient(project: Project, since: str, until: str | None = None) -> str:
    ledger = aggregate(project, since, until)
    return render(project, ledger)


def render(project: Project, ledger: WorkLedger) -> str:
    L: list = []
    a = L.append
    window = f"{ledger.since} → {ledger.until or 'now'}"
    a(f"# Orient — {project.name} ({project.id})")
    a("")
    a(f"Repo: {ledger.repo}")
    a(f"HEAD: {ledger.head_sha[:10]} · window: {window} · PI: {project.pi}")
    a("")

    sf = ledger.scientific_focus or {}
    if sf.get("first_sentence"):
        a("## Scientific focus (STATUS)")
        a("")
        a(f"- {sf['first_sentence']}")
        if sf.get("top_headline_number"):
            a(f"- headline number: {sf['top_headline_number']}")
        a("")

    a("## What moved since " + ledger.since)
    a("")
    if ledger.changelog_entries:
        for e in ledger.changelog_entries[:8]:
            head = e["heading"] or "(update)"
            a(f"- **{e['date']}** — {head}")
    elif ledger.commits:
        for c in rank_commits_for_headline(ledger.commits)[:8]:
            a(f"- `{c['sha']}` **{c['prefix'] or '—'}** · {c['subject']}")
    else:
        a("- (no commits or CHANGELOG entries in the window)")
    a(f"- _{len(ledger.commits)} commits, {len(ledger.evidence_files)} evidence "
      "files touched in window._")
    a("")

    a("## Open PI asks / decisions")
    a("")
    if ledger.pi_flagged_asks:
        a("**🔴 PI-flagged workstream asks (blocking — raise first):**")
        for ask in ledger.pi_flagged_asks:
            line = f"- **{ask['workstream']}** {ask['directive']}"
            if ask.get("recommendation"):
                line += f" — _{ask['recommendation']}_"
            a(line)
        a("")
    if ledger.open_decisions:
        a("**Open D.N decision queue:**")
        for d in ledger.open_decisions[:10]:
            a(f"- {_clean_row(d)}")
        a("")
    if not ledger.pi_flagged_asks and not ledger.open_decisions:
        a("- (none detected)")
        a("")

    a("## Blockers / things to watch")
    a("")
    watch = []
    if ledger.claimed_not_evidenced:
        watch.append(
            f"{len(ledger.claimed_not_evidenced)} claimed-done items lack "
            "code/file evidence — verify before relying on them.")
    if ledger.evidenced_not_claimed:
        watch.append(
            f"{len(ledger.evidenced_not_claimed)} commits did work no TRACKER row "
            "logs — may need recording.")
    if not watch:
        watch.append("Nothing flagged — claimed and real are in sync this window.")
    for w in watch:
        a(f"- {w}")
    a("")
    a("_Ephemeral orientation brief — not committed, not a bundle. Run "
      "`project-update build` to produce the canonical dated bundle._")
    return "\n".join(L) + "\n"


def _clean_row(text: str) -> str:
    t = text.strip()
    if t.startswith("|"):
        cells = [c.strip() for c in t.strip("|").split("|") if c.strip()]
        return " · ".join(cells[:4])
    return t
