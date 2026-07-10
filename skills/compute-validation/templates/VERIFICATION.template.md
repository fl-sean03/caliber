---
campaign: <slug>                       # short identifier, must match campaign dir
project: <project-name>                # e.g. hydrogenation, mxene-2026, solvfe
verified_by: claude-opus-4-7-1m        # model + identifier
created: YYYY-MM-DD
verification_status: yellow            # green | yellow | red | needs-human
production_ready: false                # set true only when all termination criteria met
references:
  configs:
    - <path-to-primary-config>         # e.g. simulations/<campaign>/inputs/production.namd
  playbooks:
    - <path>                           # e.g. simulations/<project>/HPC_PLAYBOOK.md
  priors:
    - <path>                           # e.g. simulations/<project>/.priors.yaml
---

# Campaign: <name>

One-line purpose. Why this campaign exists, what it produces.

## TL;DR

- **Status:** <green / yellow / red> — one-line gist (e.g. "yellow: patch-grid sizing flagged, smoke will catch")
- **Top concerns:** up to 3 bullets, highest-severity first
- **Recommended next action:** advance to smoke / fix and re-verify / escalate to human

---

## Category 1 — Config integrity

**Status:** <green / yellow / red>

Each finding as: `[STATUS] <file:line>` `<observation>` `<rationale>`. One bullet per finding; no bundling.

- [GREEN] `inputs/production.namd:47` — `useConstantArea yes` set; consistent with slab geometry.
- [YELLOW] `deploy_hpc.sh:12` — walltime requested 24h but throughput estimate gives 18h; comfortable margin but no buffer for restart-on-walltime.
- [RED] (none)

---

## Category 2 — Domain sanity

**Status:** <green / yellow / red>

Domain-specific: physics for MD, statistics for ML, chemistry for QM. See `tools/<software>.md` for the heuristics that apply here.

- [GREEN] Density at start: 1.04 g/cm³, within liquid-NEC expected range (1.0–1.1).
- [GREEN] Thermostat target 333 K matches experimental NEC liquid regime.
- [YELLOW] Box z-extent 48.3 Å with patch margin 14 Å → patches in z = 3; tight but should hold. Smoke must verify.

---

## Category 3 — Computational sanity

**Status:** <green / yellow / red>

Resource estimates from first principles vs. what the submit script asks for.

| Metric | Estimate (independent) | Requested | Margin | Status |
|---|---|---|---|---|
| Walltime | 18 h | 24 h | +33% | green |
| GPU memory | 0.8 GB | 40 GB (A100) | abundant | green |
| Throughput | 165 ns/day expected | — | — | (will measure in smoke) |
| Disk per stage | 12 GB | — | — | green |

If your independent estimate disagrees with the request by >2× in either direction, flag and reconcile here.

---

## Category 4 — Pattern matching against priors

**Status:** <green / yellow / red>

Priors loaded from: `<path-to-priors.yaml>` (or note "no priors.yaml; used <alternate-source>").

Patterns evaluated:

| Pattern ID | Triggered? | Mitigation applied | Reference |
|---|---|---|---|
| `slab-npt-needs-useConstantArea` | yes | set `useConstantArea yes` (`inputs/production.namd:47`) | `simulations/.priors.yaml` |
| `namd-velocity-limit-on-flexible-water` | no (no flexible water in this system) | n/a | — |
| `<other patterns evaluated>` | — | — | — |

If a high-severity pattern matched and mitigation was *not* applied, that's a red — explain why and either apply or escalate.

---

## Category 5 — Precedent comparison

**Status:** <green / yellow / red>

Last successful campaign in same family: `<path>` (e.g. `simulations/cubic-npt-2026-04-12/`).

Diff and rationales:

| What changed | Old → New | Rationale | Safe? |
|---|---|---|---|
| Geometry | cubic NP → Pt(111) slab | PI requested slab study | requires patch-grid review (cat. 2) |
| Box z | 110 Å → 48 Å | slab is thinner | yellow — see cat. 2 |
| `useConstantArea` | n/a → yes | required by slab NPT | yes |

Every diff must have a rationale. Unrationalized diffs are red flags, not yellow.

If no precedent exists (first-of-kind work), state so explicitly: this raises the prior on YELLOW and increases reliance on categories 2, 3, 4, and 7.

---

## Category 6 — Risk register

**Status:** <green / yellow / red>

Top-3 failure modes for this campaign, in priority order.

| # | Mode | Likelihood | Impact | Catch tier | Mitigation |
|---|---|---|---|---|---|
| 1 | Patch grid too small in z | medium | crash at ~10 ps | smoke (Layer B) | grep `PATCH GRID` in smoke log; verify nz ≥ 3 |
| 2 | Density drift on slab without constant area | low (mitigated) | invalidates result | smoke (Layer B) | `useConstantArea yes` set; verify density stable in smoke |
| 3 | Pt sublattice melts at 1000 K | low | structural damage | verification (Layer A) | all Pt B=1.0 fixed in PDB; verified `inputs/system.pdb` |

"Catch tier" = where this would be detected: verification (already caught here), smoke (Layer B will surface), production (only visible at full scale — these are the ones that motivate Layer B).

---

## Category 7 — External research

**Status:** <green / yellow / red>

Was external research needed for this campaign? If no, write "not needed — campaign is a routine variant of <precedent>" and skip the rest.

If yes:

- **Question:** What was unfamiliar that needed external sourcing?
- **What was found:** Concrete findings that affected the verification.
- **Sources:** URLs / paper citations / forum threads / tool docs consulted.

Example:

- **Question:** Behavior of NAMD-3 GPU patch grid on slab geometries with z-extent < 50 Å — first time we're running this regime.
- **What was found:** NAMD GPU requires patch grid nz ≥ ~4 for good decomposition; nz=3 works but is borderline. Forum post (Dec 2024) recommends explicit `pairlistDist` reduction if nz=2 or 3.
- **Sources:** `https://www.ks.uiuc.edu/Research/namd/3.0/ug/`; `https://www.ks.uiuc.edu/Research/namd/mailing_list/...`

Keep findings concrete enough that a future verification can short-circuit by reading them.

---

## Mitigations applied to config before smoke

Concrete edits made to the campaign config as a result of this verification. Each as `<file:line> <change> <rationale>`. One per bullet.

- `inputs/production.namd:47` — added `useConstantArea yes` (was unset). Rationale: slab geometry requires it; matched prior `slab-npt-needs-useConstantArea`.
- `deploy_hpc.sh:8` — requested partition `aa100` (was `gpu`). Rationale: A100 throughput estimate fits walltime; default `gpu` is mixed.

If no mitigations were applied, write "none — config passes verification as-is" and explain why no edits were needed. This is acceptable for byte-identical re-runs of a passing precedent.

---

## Recommended smoke parameters

Concrete instructions for what the Layer B smoke should run. The agent driving Layer B will read this section.

- **Run length:** 30 minutes wallclock (~50 ps simulation time at expected throughput).
- **Backend:** `atesting_a100` (free Alpine testing partition; per `compute-strategy/backends/alpine.md`).
- **Signals to monitor:**
  - `PATCH GRID` line in NAMD log → confirm nz ≥ 3.
  - Density vs. time → fit linear; project to production end; flag if predicted > 1.10 g/cm³.
  - Pt sublattice RMSD → flag if > 0.5 Å.
  - Throughput (ns/day from log) → compare to estimate of 165 ns/day; flag if < 100 or > 250.
- **Reproducibility:** after first smoke is clean, re-submit byte-identical and confirm throughput within ±5% and density traces overlay.

---

## Open questions for human review

If any. Often empty for routine variants; non-empty for first-of-kind work, novel parameter regimes, or when the agent reached its 30-minute external-research cap without resolution.

- (none) — or list specific questions, e.g. "Patch grid sizing was researched but I'm not 100% certain nz=3 is stable for our specific timestep; recommend human eyes if smoke shows any irregularity."

---

## Verdict checklist

- [ ] All red items resolved (or none existed)
- [ ] Yellow items resolved or accepted with rationale
- [ ] Mitigations applied and documented
- [ ] Smoke parameters specified
- [ ] Cleared to proceed to Layer B (smoke)

---

## Validation summary

(Filled in after Layer B loop terminates. See `workflows/iteration-discipline.md` for the format.)
