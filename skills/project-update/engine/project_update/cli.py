"""project-update CLI — the engine's operator surface.

  python3 -m project_update orient --repo <path> [--since DATE] [--until DATE]
  python3 -m project_update build  --repo <path> --date <YYYY-MM-DD>
                                   [--since DATE] [--until DATE]
                                   [--kind pi-meeting|weekly|adhoc] [--no-deck]

The repo root is resolved via `git rev-parse --show-toplevel` (the cwd's repo, or
the --repo path's repo). The rest is read from `<repo>/.sync/manifest.yaml`.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import sys

from . import __version__, manifest


def _default_since(date: str | None) -> str:
    """A sensible default window start: 7 days before `date` (or today)."""
    base = _dt.date.fromisoformat(date) if date else _dt.date.today()
    return (base - _dt.timedelta(days=7)).isoformat()


def cmd_orient(args) -> int:
    from .orient import orient
    repo = manifest.resolve_repo(args.repo)
    project = manifest.load(repo)
    since = args.since or _default_since(None)
    print(orient(project, since, args.until))
    return 0


def cmd_build(args) -> int:
    from .bundle import build
    repo = manifest.resolve_repo(args.repo)
    project = manifest.load(repo)
    date = args.date
    since = args.since or _default_since(date)
    result = build(
        project, date,
        since=since,
        until=args.until,
        kind=args.kind,
        build_deck_flag=not args.no_deck,
        version=__version__,
    )
    print(f"bundle dir  : {result.bundle_dir}")
    print(f"meeting.yaml: {result.meeting_yaml}")
    print(f"PREP.md     : {result.prep}")
    print(f"synthesis   : {result.synthesis}")
    print(f"deck        : {result.deck.message}")
    print(f"artifacts   : {len(result.artifacts)} symlinked")
    for art in result.artifacts:
        print(f"  - {art}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="project-update",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--version", action="version", version=f"project-update {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    o = sub.add_parser("orient", help="ephemeral current-state brief (stdout)")
    o.add_argument("--repo", help="repo path (default: cwd); resolved to git toplevel")
    o.add_argument("--since", help="window start YYYY-MM-DD (default: 7d ago)")
    o.add_argument("--until", help="window end YYYY-MM-DD (default: open)")
    o.set_defaults(func=cmd_orient)

    b = sub.add_parser("build", help="write the canonical dated bundle")
    b.add_argument("--repo", help="repo path (default: cwd); resolved to git toplevel")
    b.add_argument("--date", required=True, help="meeting/checkpoint date YYYY-MM-DD")
    b.add_argument("--since", help="window start YYYY-MM-DD (default: date - 7d)")
    b.add_argument("--until", help="window end YYYY-MM-DD (default: date)")
    b.add_argument("--kind", default="pi-meeting",
                   choices=["pi-meeting", "weekly", "adhoc"])
    b.add_argument("--no-deck", action="store_true", help="skip the deck rebuild")
    b.set_defaults(func=cmd_build)

    args = p.parse_args(argv)
    try:
        return args.func(args)
    except (FileNotFoundError, RuntimeError, PermissionError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
