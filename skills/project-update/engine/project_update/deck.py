"""Deck builder — regenerate a project's living deck (never append).

The deck SOURCE is owned by the project (e.g. hydrogenation's
manuscript/figures/_pptx/{build_pptx.py,captions.py}). The engine's job is to
TRIGGER the project's own builder, then symlink the freshly-built artifact into
the meeting bundle. History lives in the source's git log, not in slide drift —
"ongoing means regenerated, not appended".

python-pptx is NOT an engine runtime dependency: the engine never builds a deck
itself, it shells out to the project's builder (which may use python-pptx). For
projects with no builder, build_deck() reports a stub rather than failing. This
keeps the optional dep isolated behind the project's builder.
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .manifest import Project


@dataclass
class DeckResult:
    built: bool
    output: Path | None
    message: str
    command: str = ""


def build_deck(project: Project, *, dry_run: bool = False) -> DeckResult:
    deck = project.deck
    if not deck or not deck.get("builder"):
        return DeckResult(
            built=False,
            output=None,
            message=(
                f"No deck builder registered for '{project.id}'. To add one, "
                "scaffold a captions.py/build_pptx.py pair and register it under "
                "`deck:` in .sync/manifest.yaml (see MANIFEST_SCHEMA.md)."
            ),
        )

    builder = deck["builder"]
    args = str(deck.get("builder_args", "")).split()
    output = project.repo / deck["output"] if deck.get("output") else None
    builder_path = project.repo / builder

    if builder.endswith(".sh"):
        cmd = ["bash", str(builder_path), *args]
    elif builder.endswith(".py"):
        cmd = ["python3", str(builder_path), *args]
    else:
        cmd = [str(builder_path), *args]
    cmd_str = " ".join(cmd)

    if dry_run:
        return DeckResult(
            built=False, output=output,
            message=f"[dry-run] would run: {cmd_str}", command=cmd_str,
        )

    if not builder_path.exists():
        return DeckResult(
            built=False, output=output,
            message=f"Deck builder not found at {builder_path}", command=cmd_str,
        )

    proc = subprocess.run(
        cmd, cwd=str(project.repo), capture_output=True, text=True, check=False,
        env={**os.environ},
    )
    if proc.returncode != 0:
        return DeckResult(
            built=False, output=output, command=cmd_str,
            message=(
                f"Deck build FAILED (exit {proc.returncode}). "
                f"Likely missing python-pptx in the active env "
                f"(`pip install python-pptx Pillow`).\n"
                f"stderr tail:\n{proc.stderr.strip()[-600:]}"
            ),
        )
    ok = output.exists() if output else True
    return DeckResult(
        built=ok, output=output, command=cmd_str,
        message=f"Deck regenerated via project builder: {output}" if ok
        else f"Builder exited 0 but output not found at {output}",
    )


def symlink_into(meeting_dir: Path, target: Path, link_name: str | None = None) -> Path:
    """Create artifacts/<name> -> target symlink so the bundle always resolves to
    the current regenerated artifact."""
    artifacts = meeting_dir / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    link = artifacts / (link_name or target.name)
    if link.is_symlink() or link.exists():
        link.unlink()
    os.symlink(target, link)
    return link
