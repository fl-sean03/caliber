---
name: project-update
description: Get fully up to date on a project, or build its weekly / PI-meeting update bundle, from INSIDE the project directory. Use when an agent lands cold in a project and needs the current state (open workstreams, what moved, open PI decisions, blockers), or when asked to "build the weekly update", "prep the PI meeting", or "aggregate the relevant files into the update dir". Mines only THIS repo, driven by its own .sync/manifest.yaml. No dependency on LabSync.
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
---

# project-update — in-project update engine (Tier 1)

You are inside one project repo and need either to (a) **catch up** on its
current state, or (b) **build** its canonical dated update bundle for a weekly
checkpoint or a PI 1:1. This skill wraps a deterministic, stdlib-only engine that
mines **only this one repo** — git history, narrative docs, evidence files — and
synthesizes the result, driven by the project's own `.sync/manifest.yaml`.

> **Isolation invariant.** This engine has NO dependency on LabSync. A project +
> this skill is sufficient to build that project's own update. LabSync (Tier 2)
> later *reads* the bundle this produces and runs the post-meeting writeback — it
> does not mine the project itself. See
> `36-LabSync/docs/ADR-001-two-tier-update-architecture.md`.

The engine lives next to this file at `engine/project_update/` (a peer of the
`compute-strategy` / `compute-validation` / `campaign-orchestration` skills).

---

## When to use this

- An agent starts work in a project and asks "what's the current state?" → **orient**.
- Sean (or LabSync's dispatch) says "build the weekly update" / "prep the Friday
  1:1" / "aggregate the relevant files into the update dir" → **build**.
- You need the deterministic, no-LLM floor for producing a meeting bundle.

Do **not** use this to author figures, edit the manuscript, run simulations, or
write into another project. It mines + synthesizes; it only *triggers* the
project's own deck builder, never authors slides.

---

## Prerequisite: the manifest

The engine reads `<repo>/.sync/manifest.yaml`. If it is absent, the engine errors
with a hint. Create one per `36-LabSync/docs/MANIFEST_SCHEMA.md` — declare the
docs the project actually has (`status`/`tracker`/`changelog`/`agents`, omit what
is missing), `tracker_format.pi_flag_markers` (the markers that escalate a
WORKSTREAM row to a PI ask, e.g. `["🔴", "flag to hendrik", "needs pi confirm",
"sign-off"]`), `evidence_globs`, the `deck` builder, and `bundle.root`
(`updates/pi-meetings`). Absent docs degrade gracefully — no changelog → no
window-news; no tracker → no Ask-PI/drift; no deck → skip deck.

---

## The two modes

### 1 · orient — get me up to speed (ephemeral, not committed)

```bash
python3 /path/to/skills/project-update/engine -m project_update \
  orient --repo "$(pwd)" --since 2026-05-22
# or, if the engine package dir is on PYTHONPATH:
PYTHONPATH=.../skills/project-update/engine python3 -m project_update orient --since 2026-05-22
```

Prints a current-state brief to stdout: scientific focus (from STATUS), what
moved since `--since` (CHANGELOG news or ranked commits), open PI asks (🔴
workstream asks + the D.N decision queue), and blockers. It is transient — **not
written to a committed file**. Use it to catch up before doing work.

### 2 · build — write the canonical dated bundle

```bash
PYTHONPATH=.../skills/project-update/engine python3 -m project_update \
  build --repo "$(pwd)" --date 2026-05-29 --since 2026-05-22 --kind pi-meeting
# add --no-deck to skip the deck rebuild; --kind weekly for a no-meeting checkpoint
```

Writes `<repo>/<bundle.root>/<date>/` per
`36-LabSync/docs/BUNDLE_CONTRACT.md`:

- `meeting.yaml` — machine-readable parse anchor (provenance incl. repo HEAD,
  `generated_by: project-update@<version>`, the window, the artifact list).
- `synthesis.md` — full reconciliation: scientific focus, this-week's-developments
  (CHANGELOG), milestones (doc-only, kept OUT of drift), activity ledger,
  claimed-vs-real drift, open PI-decision queue (🔴 asks lead).
- `PREP.md` — in-the-room script: what to open, 90-sec opening, headline, walk-
  through, **Ask PI** (🔴 workstream asks first, then D.N), engineering FYI, drift.
- `artifacts/` — **symlinks** (never copies) to the regenerated deck + manuscript
  / SI PDFs, always resolving to the current build.

The deck step triggers the manifest's `deck.builder`. If python-pptx is missing
or the builder fails, it degrades with a clear message and still symlinks the
existing built deck.

---

## Boundaries (read before you run build)

- **This repo only.** The engine never reaches into another project; cross-project
  knowledge lives in LabSync's registry, never in a manifest.
- **Additive.** A build writes a *new* dated dir. Re-running for the same date
  regenerates only the engine-owned files (`meeting.yaml`, `PREP.md`,
  `synthesis.md`, `artifacts/`) and **never touches** human/LabSync files in that
  dir (`TRANSCRIPT.md`, `feedback-extracted.md`, `action-items.md`,
  `writeback-log.md`).
- **Never authors figures.** It triggers the project's deck rebuild; the figure
  source stays owned by the project.
- **Git hygiene.** The bundle is purely additive — commit the new dated dir as its
  own commit. Do not stage unrelated pending work from other agents.
- **Post-meeting is LabSync's job.** Sean pastes `TRANSCRIPT.md`; LabSync extracts
  directives and writes them back into the TRACKER. The engine stops at `prepped`.

---

## Quick checklist

- [ ] Does `<repo>/.sync/manifest.yaml` exist + declare the docs this repo has?
- [ ] Did I pick the window (`--since` = last checkpoint, `--date` = meeting date)?
- [ ] For a build: is `--kind` right (`pi-meeting` vs `weekly`)?
- [ ] After build: does the synthesis lead with the 🔴 PI-flagged ask + CHANGELOG
      news, and do `artifacts/` symlinks resolve to real files?
- [ ] Am I committing ONLY the new dated dir (+ a new manifest if I created one)?
