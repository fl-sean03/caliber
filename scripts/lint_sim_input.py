#!/usr/bin/env python3
"""
lint_sim_input.py — deterministic pre-run lint for QE / LAMMPS input files
(Slice A5 prototype, rebase-2026-07-02, U-11; provenance claude-fable-5).

Motivation: on 2026-01-17 `pw.x` was invoked at least twice with an EMPTY input
file, producing the repo-root `CRASH` debris ("could not find namelist
&control"). That failure class costs a spawned run + cleanup every time and is
100% catchable before execution. This lint is deliberately tiny and
deterministic — judgment stays in the agent, this only refuses the objectively
malformed.

STATUS: standalone prototype. NOT wired into .claude/hooks/validate_simulation.py
— the hook is the live session's operating surface; activation is owner decision
B-2 (see 08_upgrades/upgrade-2026-07-02/proposals/).

Usage:
    python scripts/lint_sim_input.py qe     path/to/pw.in
    python scripts/lint_sim_input.py lammps path/to/in.script
Exit 0 = pass, 1 = BLOCK (reasons on stdout), 2 = usage error.
"""

import re
import sys
from pathlib import Path

# LAMMPS: pair styles that only make sense with specific `units` settings.
# Conservative list — only unambiguous physics mismatches are flagged.
LAMMPS_UNITS_FOR_PAIR = {
    "lj/cut": {"lj", "real", "metal", "si"},   # broadly valid; listed for structure
    "eam": {"metal"},
    "eam/alloy": {"metal"},
    "eam/fs": {"metal"},
    "tersoff": {"metal"},
    "sw": {"metal"},
    "airebo": {"metal"},
    "reaxff": {"real"},
    "reax/c": {"real"},
}


def lint_qe(text: str):
    """QE pw.x input: non-empty, &control namelist must come first."""
    problems = []
    stripped = text.strip()
    if not stripped:
        problems.append("EMPTY input file — pw.x will abort with "
                        "'could not find namelist &control' (the 2026-01-17 CRASH class)")
        return problems
    # First non-blank, non-comment (!) line should open the &control namelist.
    first = next((ln.strip() for ln in stripped.splitlines()
                  if ln.strip() and not ln.strip().startswith("!")), "")
    if not first.lower().startswith("&control"):
        problems.append(f"first namelist is '{first[:40]}' — pw.x requires &control first")
    if "&system" not in stripped.lower():
        problems.append("missing &system namelist")
    if "&electrons" not in stripped.lower():
        problems.append("missing &electrons namelist")
    return problems


def lint_lammps(text: str):
    """LAMMPS input: non-empty, units declared before pair_style, consistency."""
    problems = []
    stripped = text.strip()
    if not stripped:
        problems.append("EMPTY input file — lmp will abort immediately")
        return problems
    units = None
    units_line = None
    pair_lines = []
    for i, raw in enumerate(stripped.splitlines(), 1):
        ln = raw.split("#", 1)[0].strip()
        if not ln:
            continue
        m = re.match(r"units\s+(\S+)", ln)
        if m:
            units, units_line = m.group(1), i
        m = re.match(r"pair_style\s+(\S+)", ln)
        if m:
            pair_lines.append((i, m.group(1)))
    if pair_lines and units is None:
        problems.append("pair_style used but no `units` command — LAMMPS defaults to "
                        "'lj', which is almost never intended with tabulated potentials")
    for i, style in pair_lines:
        if units_line is not None and i < units_line:
            problems.append(f"line {i}: pair_style before `units` (line {units_line}) — "
                            "units must be set first")
        allowed = LAMMPS_UNITS_FOR_PAIR.get(style)
        if allowed and units is not None and units not in allowed:
            problems.append(f"line {i}: pair_style '{style}' with units '{units}' — "
                            f"expected one of {sorted(allowed)}")
    return problems


def lint_file(kind: str, path: Path):
    if not path.exists():
        return [f"input file does not exist: {path}"]
    text = path.read_text(errors="replace")
    if kind == "qe":
        return lint_qe(text)
    if kind == "lammps":
        return lint_lammps(text)
    raise ValueError(f"unknown kind: {kind}")


def main(argv):
    if len(argv) != 3 or argv[1] not in ("qe", "lammps"):
        print(__doc__)
        return 2
    problems = lint_file(argv[1], Path(argv[2]))
    if problems:
        print(f"BLOCK {argv[2]}:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"OK {argv[2]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
