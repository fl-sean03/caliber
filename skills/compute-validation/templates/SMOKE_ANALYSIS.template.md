---
campaign: <slug>                       # must match VERIFICATION.md and dirname
iteration: 1                           # 1, 2, 3, ... incremented per smoke
job_id: <slurm-jobid-or-vast-instance> # scheduler-side identifier for traceability
smoke_duration: 30 min                 # wallclock budget actually used
backend: atesting_a100                 # alpine partition, vast SKU, or local
created: YYYY-MM-DD
verdict: needs-iteration               # pass | needs-iteration | escalate
production_ready: false                # set true only on the loop's final iteration
config_changes_from_prev: []           # list of file:line summaries, or "none" for reproducibility re-smoke
                                       # examples: ["inputs/production.namd:47 useConstantArea yes",
                                       #           "deploy_hpc.sh:12 walltime 24h -> 30h"]
---

# Smoke iteration <N>

One-line summary: what this iteration tested and the verdict. e.g. "Iteration 002 — fix verified, density stable; reproducibility re-smoke needed before advance."

---

## Run summary

What was actually submitted and what completed.

- **Config snapshot:** `<path>` (or commit hash if version-controlled)
- **Hardware:** A100 80GB on `atesting_a100` (1 node, 1 GPU)
- **Submitted at:** YYYY-MM-DD HH:MM:SSZ
- **Completed at:** YYYY-MM-DD HH:MM:SSZ — exit status: 0
- **Wallclock used:** 28 min of 30 min requested
- **Output paths:**
  - Log: `<path>`
  - Trajectory: `<path>` (if applicable)
  - Restart files: `<path>` (if applicable)
- **Notes on the run itself:** e.g. "first 5 min were slow, suspect cold cache; last 25 min throughput stable."

---

## Measurements extracted

Every signal pulled from the smoke output. Each row: signal → observed value → expected value (from VERIFICATION.md prediction or precedent) → status.

| Signal | Observed | Expected | Status |
|---|---|---|---|
| Throughput (ns/day) | 168 | 165 ± 30 | green |
| Density at smoke end (g/cm³) | 1.05 | 1.0–1.1 | green |
| Density slope (g/cm³/ns) | -0.001 ± 0.002 | ~0 | green |
| Patch grid (nx × ny × nz) | 4 × 4 × 3 | nz ≥ 3 | green |
| Pt sublattice RMSD (Å) | 0.18 | < 0.5 | green |
| Energy drift (kcal/mol/ns) | -0.02 | < 0.1 | green |
| GPU memory peak (GB) | 0.94 | < 5 | green |

Status one of: green (matches expectation) / yellow (within tolerance but borderline) / red (out of tolerance or trending wrong).

---

## Extrapolation to production

For each measured trend, project to production timescale and flag any threshold crossings.

- **Density:** smoke slope -0.001 g/cm³/ns × production duration 50 ns = -0.05 g/cm³. Final predicted ρ ≈ 1.00 g/cm³. Within liquid-NEC range. **No threshold crossing.**
- **Throughput:** 168 ns/day stable across smoke. 50 ns production → 7.1 hours. Walltime requested 24 h. **Comfortable margin; no walltime exceedance.**
- **Energy drift:** -0.02 kcal/mol/ns. Cumulative drift over 50 ns ≈ -1 kcal/mol. **Within numerical tolerance for NPT MD.**
- **Pt sublattice:** RMSD 0.18 Å in smoke, no trend. Expected stable. **No threshold crossing.**

If any extrapolated trend would cross a failure threshold within production: flag here as red even if the smoke itself is fine. The extrapolation criterion is independent of the smoke-pass criterion.

---

## Comparison to verification predictions

For each Layer A prediction in `VERIFICATION.md` risk register and per-category findings, did the smoke confirm or refute?

| Prediction | Smoke result | Match? | Notes |
|---|---|---|---|
| Patch grid nz ≥ 3 (cat 2) | nz = 3 | yes | tight but stable; no fragmentation |
| Density stable with `useConstantArea yes` (cat 4) | slope -0.001 g/cm³/ns | yes | within noise of zero |
| Pt sublattice stable at 1000 K (risk 3) | RMSD 0.18 Å | yes | well below 0.5 Å threshold |
| Throughput 165 ns/day (cat 3) | 168 ns/day | yes | +1.8% — within ±20% tolerance |

**Divergences:** none in this iteration. (If divergences exist, explain each with rationale: was the prior wrong, or is this novel? — see `workflows/iteration-discipline.md` § Bidirectional learning rule.)

---

## Comparison to baseline

(If applicable. Skip with "no baseline" for first-of-kind work.)

Baseline: `<path-to-prior-passing-smoke>` (e.g. `simulations/cubic-npt-2026-04-12/SMOKE_ANALYSIS_002.md`).

| Signal | Baseline | Current | Diff | Concerning? |
|---|---|---|---|---|
| Throughput | 145 ns/day | 168 ns/day | +16% | no — slab is smaller than baseline cubic NP |
| Density | 1.04 g/cm³ | 1.05 g/cm³ | +1% | no |
| Pt RMSD | n/a (no Pt in baseline) | 0.18 Å | new signal | no — Pt-specific to this campaign |

Diffs without a clear rationale are yellow flags.

---

## Findings

Green / yellow / red list with rationale. One bullet per finding; no bundling.

- [GREEN] All Layer A predictions confirmed by smoke; no surprises.
- [GREEN] Patch grid nz=3 holds throughout; no fragmentation in log.
- [GREEN] Density stable, slope negligible, mean within liquid-NEC range.
- [YELLOW] Throughput +1.8% above prediction — well within tolerance, but suggests prediction model was slightly conservative; consider updating the prior.
- [RED] (none)

---

## Decision

Pick exactly one of the three Action sections below. Delete the others before saving the file.

### Action: advance to production

(Use only if all 7 termination criteria in `workflows/iteration-discipline.md` are satisfied.)

- All Layer A red items: resolved (none existed).
- Yellow items: throughput-prediction prior flagged, accepted with note (will update priors).
- Smoke vs. prediction: consistent within tolerance.
- Reproducibility: this is iteration 003 (byte-identical re-run of 002); throughput within 1.8% of 002, traces overlay → reproducibility satisfied.
- Extrapolation: no threshold crossings.
- Iteration budget: 3 of 5 used.
- Production submission: cleared.

### Action: fix and re-smoke

(Use if smoke surfaced something fixable within the iteration budget.)

- **Issue identified:** <one-line summary>
- **Diagnosis:** <root cause as best understood>
- **Fix:** <file:line> <change> <expected mechanism>
- **Fix vs. workaround:** <fix | workaround> — if workaround, explain why fix isn't possible now.
- **Next smoke parameters:** <any change to duration, hardware, signals to add>
- **Iteration budget remaining:** <N - current> of 5 (or 5/2 if cumulative workaround weight ≥ 2).

### Action: escalate to human

(Use if any escalation trigger fired — see `workflows/iteration-discipline.md` § Escalation triggers.)

- **Trigger:** <which trigger fired — exact one from the list>
- **Context:** <one paragraph: what was tried, why it didn't work, what the agent doesn't know>
- **Specific question for human:** <what the human is being asked to decide>
- **State frozen at:** WORKFLOW.md `escalation_required: true` set; campaign halts until cleared.

---

## Updated priors

(If applicable. Skip with "none" if no priors changes were warranted.)

Patterns appended or revised in `<path-to-priors.yaml>` based on this iteration's findings:

- **Appended:** `<id>` — <one-line description>. Reference: this file.
- **Revised:** `<id>` — old severity `medium` → new `high` based on this iteration's evidence.

If a divergence between Layer A and Layer B was observed (case (a) in the Bidirectional learning rule), the prior reasoning being corrected should be noted here too.
