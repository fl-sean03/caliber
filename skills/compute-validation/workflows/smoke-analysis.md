# Workflow: Smoke Analysis (Layer B)

The deep-dive doc for Layer B of `compute-validation/SKILL.md`. Read this when you've just completed a smoke run and need to extract predictive signal, compare to Layer A predictions, and decide whether to advance, iterate, or escalate.

> **Core principle:** smoke is a *measurement instrument*, not a pass/fail check. A 5-minute smoke contains enough data to predict 5-day production behavior — *if you extract the right signal*.

---

## Mindset

Most agents (and humans) treat smoke as a binary: did it crash, yes or no? That's leaving 90% of the value on the floor. A smoke produces:

- Time-series data on every instantaneous physical/computational observable
- Convergence/drift trajectories
- Resource utilization fingerprints
- Reproducibility evidence (compared to prior smokes)

All of this is *predictive* of long-running behavior, if you fit the trends and extrapolate.

Treat each smoke like a small experiment whose purpose is to *predict the result of the larger experiment*. Be data-greedy. Don't accept "exit 0 + restart written" as a green smoke — that's necessary but nowhere near sufficient.

Falsification mindset applies here too: actively look for trends that *would* fail the production run. Don't search for "evidence it works"; search for "evidence it won't."

---

## The signal extraction taxonomy

A smoke produces signal in four categories. Each tells you something different about production behavior.

### A. Physical / scientific observables

What the simulation is computing. Catches drift, instability, mis-equilibration, FF errors that don't crash but produce bad data.

| Domain | Examples |
|---|---|
| MD | Total/kinetic/potential energy, temperature, pressure (xx/yy/zz), box dimensions, density, RMSD vs initial, force magnitudes |
| ML training | Loss, accuracy, gradient norms, weight norms, learning rate effective, validation metrics |
| DFT | SCF residual, force consistency, total energy convergence, magnetization |
| Data pipeline | Throughput rows/sec, error rate, distribution of intermediate values |

For each: extract the trajectory (not just the final value). The shape matters more than the endpoint.

### B. Computational observables

How the run is consuming resources. Catches throughput collapse, memory leaks, hardware degradation.

| Signal | What it tells you |
|---|---|
| Throughput (steps/sec, ns/day, samples/sec) | Realistic production walltime; bad nodes |
| GPU memory trajectory | OOM risk; memory leaks |
| GPU utilization | Underutilized → suspect |
| Step-time variance | Thermal throttling; storage I/O contention |
| Wall vs CPU time | Sync overhead; parallelism efficiency |
| Output write success | Resilience for restart |

### C. Risk indicators

Specific predictors of failure modes. These usually come from comparing observed behavior to known thresholds.

| Indicator | Predicts |
|---|---|
| Box dimension trajectory | Patch-grid invalidation; barostat instability |
| Pressure anisotropy | Slow equilibration; force-field issue |
| Energy drift slope | Numerical instability over long runs |
| Temperature variance | Thermostat saturation |
| Memory growth rate | OOM at production timescale |
| Output file size growth | Storage exhaustion |

### D. Reproducibility indicators

Signal that the *system itself* is deterministic enough to commit to production. Two consecutive smokes with identical configs should produce nearly identical curves.

| Check | Tolerance |
|---|---|
| Throughput | within ±5% across runs |
| Energy curves | overlay within thermal noise |
| Box trajectories | overlay within barostat noise |
| Final state | atom-level agreement after fixed N steps |

If two consecutive smokes diverge meaningfully, the system has hidden non-determinism. Don't ship to production.

---

## Methods for extracting predictive signal

The agent's toolbox for turning short-time measurement into long-time prediction.

### Method 1: Linear extrapolation

For trends that look linear over the smoke timescale, fit a line and project to production timescale.

**Example (slab patch-grid prediction):**
- Smoke shows z(0) = 120 Å, z(5 ps) = 119.5 Å → slope ≈ −0.1 Å/ps
- Equilibrium z target (from density) ≈ 62 Å → reaches at t ≈ 580 ps
- Patch-grid invalidation threshold ≈ 35 Å → reaches at t ≈ 850 ps
- Production runs 5 ns. **Crash predicted at t ≈ 850 ps, well within production**.

**When linear:** early-time decay, monotonic drift, throughput (when not throttling).

**When NOT linear:** energy near equilibrium, exponential-decay equilibration, resource accumulation.

### Method 2: Exponential / asymptotic fit

For equilibration trends approaching an asymptote.

**Example (energy equilibration):**
- E(t) = E_∞ + ΔE · exp(−t/τ)
- Fit gives τ (equilibration timescale) and E_∞ (equilibrium energy)
- If τ > production duration / 5, equilibration is incomplete at production end

**When applicable:** equilibration toward a stable mean (energy, temperature, density, loss in late training).

### Method 3: Convergence analysis

For monotonic-decreasing residuals (SCF, optimization).

- Compute residual reduction per step: r(n+1) / r(n)
- If ratio > 0.95, convergence is too slow → predict failure to converge in production
- If ratio < 0.5, healthy convergence

### Method 4: Statistical comparison to baseline

When a known-good prior smoke exists for a similar system:

- Overlay the two trajectories (energy, throughput, box dims, etc.)
- Compute deviations per timepoint
- If deviations exceed historical noise (±3σ from prior runs), flag as anomaly
- This is the strongest signal when available — it's a *measured* baseline, not a *predicted* one

### Method 5: Threshold-crossing prediction

For trajectories that hit a specific failure boundary:

- Identify all relevant thresholds (margin → patch-grid; max box dim → minimum-image violation; max pressure → barostat instability)
- For each threshold, compute time-to-cross from current trend
- Compare to production timescale
- If crossing predicted within production: red flag

### Method 6: Variance trend analysis

For instabilities that show up as growing oscillations before crashing:

- Compute rolling stdev of an observable over smoke timescale
- If stdev grows monotonically: instability brewing
- Common in barostat/thermostat saturation, integration timestep-too-large bugs

---

## Comparing measurement to Layer A predictions

For every prediction made in `VERIFICATION.md`, the smoke either confirms or contradicts.

| Layer A predicted | Smoke measured | What this means |
|---|---|---|
| Throughput X ns/day | Y ns/day, Y ≈ X | Verification model is calibrated; trust other predictions |
| Throughput X ns/day | Y ns/day, Y << X | Slow node? Thermal throttle? Unexpected overhead? Investigate before production |
| Density target ρ | Box trajectory predicts ρ | Confirms equilibration plan |
| Density target ρ | Box trajectory predicts ≠ ρ | Equilibration won't complete OR target was wrong; either way, fix needed |
| Equilibration τ < 1 ns | Smoke fits give τ ≈ 1 ns | Confirmed |
| No drift expected | Energy slope > tolerance | Numerical issue; investigate timestep, FF |
| OOM risk yellow | GPU memory at 60% in smoke | Confirmed safe (smoke and production memory should be similar) |

**Bidirectional learning rule:** every divergence is information.
- If Layer A overestimated: prior was conservative, can be tuned (note in priors.yaml update)
- If Layer A underestimated risk: smoke caught what reasoning missed (note in priors.yaml; update verification checklist for next time)

Don't paper over divergences. Each one is a prior update opportunity.

---

## The decision tree

After analysis, one of three outcomes:

```
        ┌───────────────────────────────────────────────┐
        │ All measurements consistent with Layer A      │
        │ AND extrapolation crosses no failure          │
        │   thresholds within production timescale      │
        │ AND reproducibility check satisfied           │
        │   (2 smokes, identical config, identical      │
        │    behavior within noise)                     │
        └────────────────────────┬──────────────────────┘
                                 │
                                YES
                                 ↓
                       advance to production

        ┌───────────────────────────────────────────────┐
        │ One or more red findings, but                 │
        │ root cause is diagnosable                     │
        │ AND fix is concrete and high-confidence       │
        │ AND iteration budget remains                  │
        └────────────────────────┬──────────────────────┘
                                 │
                                YES
                                 ↓
                  apply fix → update config → re-smoke

        ┌───────────────────────────────────────────────┐
        │ Iteration budget exceeded                     │
        │ OR same red flag persists after fix           │
        │ OR novel signal not in priors w/ low conf     │
        │ OR predicted production walltime exceeds      │
        │   request + buffer                            │
        │ OR cost cap would be exceeded                 │
        └────────────────────────┬──────────────────────┘
                                 │
                                YES
                                 ↓
                      escalate to human
```

See `iteration-discipline.md` for the full satisfaction-criteria spec.

---

## Common smoke-analysis pitfalls (anti-patterns)

The agent should explicitly NOT:

- **Treat exit code 0 as a smoke pass.** It's necessary but minor signal. Clean exit ≠ trajectory healthy.
- **Skip extrapolation.** A smoke without "what does this predict for production" is wasted compute.
- **Ignore reproducibility.** Single-smoke pass is not enough. Two consecutive identical-config smokes must overlay.
- **Accept divergence from baseline as noise.** If a known-good baseline exists, deviations are signal — investigate.
- **Confuse short-time stability with long-time stability.** Smokes don't run long enough for slow drift to reach failure threshold; the agent must extrapolate.
- **Trust visual inspection over fits.** Eyeballing a curve is bias-prone. Compute slopes, fit residuals, quantify.
- **Forget computational observables.** A smoke that's scientifically clean but ran 3× slower than expected predicts a walltime overrun in production.
- **Skip comparing to verification.** Without comparison, smoke results don't update priors and the system doesn't learn.

---

## What goes in `SMOKE_ANALYSIS_NNN.md`

See `templates/SMOKE_ANALYSIS.template.md` for the full schema. Required content:

1. **Run summary** — what was submitted, what completed
2. **Measurements extracted** — table of (signal, observed, expected, status). Include every observable from the four categories above that's relevant to this domain.
3. **Extrapolation to production** — for each measured trend, project to production timescale. Identify any threshold crossings. Cite the method used (linear, exponential, baseline comparison).
4. **Comparison to verification predictions** — for each Layer A prediction, did it match? If not, why?
5. **Comparison to baseline (if available)** — diff from a prior successful smoke
6. **Findings** — green/yellow/red list with rationale per item
7. **Decision** — one of: advance / fix-and-re-smoke (with concrete fix) / escalate (with concrete reason)
8. **Updated priors** — anything to append to project priors.yaml

Be specific. "Throughput looks fine" is not analysis. "Throughput 28 ns/day, expected 25-30 from atom count + A100 benchmark, GREEN" is analysis.

---

## When to invoke external research

For routine smokes against known-good protocols, internal analysis suffices.

When to spend time on external research:
- Throughput is anomalously low/high and you can't explain it
- A new diagnostic appears in the log that you don't recognize
- Box behavior is qualitatively different from baseline (e.g., suddenly anisotropic when it shouldn't be)
- Energy/loss curves show a feature (kink, oscillation, cliff) that's not in baseline

Tools: WebSearch for tool-specific user forums, WebFetch for documentation, read mailing-list archives. Cap external research at 30 min unless explicitly extended.

---

## Tool-specific signal extraction

The framework above is tool-agnostic. Concrete recipes for each tool live in `tools/`:

- `tools/namd.md` — NAMD MD smoke analysis (xst, xsc, log, dcd interfaces)
- `tools/lammps.md` — LAMMPS thermo + dump analysis
- `tools/qe.md` — Quantum ESPRESSO SCF + force convergence
- `tools/ml-training.md` — Generic PyTorch/JAX training analysis
- `tools/TEMPLATE.md` — How to add a new tool

Read the relevant tool page when analyzing a smoke. It tells you which files to read, which numbers to extract, and which thresholds matter for that tool.

---

## Quick checklist for an agent doing smoke analysis

You just got a smoke result back. Walk this:

1. ☐ Read `VERIFICATION.md` for this campaign — what was Layer A's predicted behavior?
2. ☐ Read `tools/<tool>.md` for the diagnostic interface details
3. ☐ Read the smoke output files (log, xst, dcd index, restart files, etc.)
4. ☐ Extract trajectories for every applicable observable (categories A-D above)
5. ☐ Fit / extrapolate each trajectory using the appropriate method
6. ☐ Compare extrapolations to production timescale; flag any threshold crossings
7. ☐ Compare measurements to Layer A predictions; note divergences
8. ☐ Compare to baseline smoke if available
9. ☐ Run reproducibility check if this is iteration ≥ 2 with identical config
10. ☐ Synthesize findings (green/yellow/red)
11. ☐ Decide: advance / iterate / escalate
12. ☐ Write `SMOKE_ANALYSIS_NNN.md` with all of the above
13. ☐ Update `priors.yaml` if new patterns emerged

Don't shortcut these. The whole point of this layer is depth.

---

## Cross-references

- `compute-validation/SKILL.md` — parent skill, the 3-layer model
- `compute-validation/workflows/verification.md` — Layer A reasoning
- `compute-validation/workflows/iteration-discipline.md` — when to terminate the loop
- `compute-validation/templates/SMOKE_ANALYSIS.template.md` — output artifact format
- `compute-validation/tools/<tool>.md` — tool-specific signal extraction recipes
