# Tool: NAMD

NAMD-specific smoke analysis recipes for the `compute-validation` skill. Read this when analyzing a smoke run produced by NAMD 2.x or 3.x. Pairs with `workflows/smoke-analysis.md` (the framework) — this page tells you which NAMD files to read, which numbers to extract, and which thresholds matter.

---

## NAMD diagnostic interfaces

A NAMD smoke (or any NAMD run) produces these files in the run directory. Each carries different signal.

| File | What's in it | Read with | Best for |
|---|---|---|---|
| `<output>.log` (or stdout) | Per-step ENERGY, PRESSURE, MISC, TIMING; minimization/heating/run progression; FATAL errors | `grep`, `awk`, manual read | Most diagnostics |
| `<output>.xst` | Cell basis vectors over time (timestep, ax/ay/az, bx/by/bz, cx/cy/cz, origin xyz) | `awk` numeric extraction | Box dynamics (NPT) |
| `<output>.xsc` | Final cell state at last checkpoint (one line) | `awk '!/^#/{print}'` | Restart sanity |
| `<output>.restart.coor`, `.restart.vel`, `.restart.xsc` | Binary checkpoint state | NAMD itself; size sanity | Resilience check |
| `<output>.dcd` | Trajectory frames | MDAnalysis, VMD, catdcd | Structural drift, RMSD |
| Per-step `TIMING:` lines | Wall + CPU time per N steps | `grep "^TIMING"` | Throughput, step-time variance |

For a smoke run named `smoke_npt`, expect: `smoke_npt.log` (often stdout-tee'd), `smoke_npt.xst`, `smoke_npt.xsc`, `smoke_npt.dcd`, `smoke_npt.restart.{coor,vel,xsc}`.

---

## Key NAMD log patterns

Most extraction is from `<output>.log`. Critical line types:

```
ENERGY:    STEP    BOND    ANGLE    DIHED    IMPRP    ELECT    VDW    BOUNDARY    MISC    KINETIC    TOTAL    TEMP    POTENTIAL    TOTAL3    TEMPAVG    PRESSURE    GPRESSURE    VOLUME    PRESSAVG    GPRESSAVG
```

All ENERGY columns are kcal/mol; TEMP is K; PRESSURE is bar. Ordering varies by NAMD version but column-by-position is stable.

```
PRESSURE:    STEP    Pxx    Pxy    Pxz    Pyx    Pyy    Pyz    Pzx    Pzy    Pzz
GPRESSURE:   STEP    Gxx    Gxy    ...   (group pressure tensor — for useGroupPressure)
PRESSAVG:    STEP    avg components   (rolling average)
GPRESSAVG:   STEP    group avg components
TIMING:      STEP    Benchmark time = X s/step    Day = Y days/ns
```

```
WRITING COORDINATES TO OUTPUT FILE AT STEP <N>
WRITING EXTENDED SYSTEM TO OUTPUT FILE AT STEP <N>
CLOSING COORDINATE DCD FILE
```

```
FATAL ERROR: <message>
```

```
TCL: <message>      (from print statements in config)
```

---

## Signal extraction recipes

### A1. Energy stability and drift

```bash
grep "^ENERGY:" smoke.log | awk 'NR>1 {print $2, $12, $14}' \
    > energy_trace.dat   # step, total, potential
```

Then compute drift slope (energy per ns):
```python
import numpy as np
data = np.loadtxt("energy_trace.dat")
step, total, _ = data.T
ns = step * 1e-6              # 1 fs timestep → ns
slope = np.polyfit(ns, total, 1)[0]   # kcal/mol per ns
```

**Thresholds:**
- |slope| < 1 kcal/mol/ns: GREEN (stable)
- |slope| 1-10 kcal/mol/ns: YELLOW (mild drift; check FF, timestep, rigidBonds)
- |slope| > 10 kcal/mol/ns: RED (serious instability)

For NPT, total energy isn't conserved — use *potential energy* and check that it's *bounded*, not zero-drift.

### A2. Temperature equilibration

```bash
grep "^ENERGY:" smoke.log | awk 'NR>1 {print $2, $13}' > temp_trace.dat
# columns: step, TEMP
```

Fit T(t) = T_target + (T_initial - T_target) · exp(-t/τ).

**Thresholds:**
- τ < 100 ps: GREEN, fast equilibration
- τ 100-500 ps: YELLOW, normal but verify equilibration period was long enough
- τ > 500 ps: RED, thermostat too weak (langevinDamping too small) or numerical issue

Check post-equilibration variance: σ_T should be ~ T_target · √(2/N_dof). For 12 k atoms, σ_T ≈ 5-10 K is healthy.

### A3. Pressure (NPT only)

```bash
grep "^PRESSAVG:" smoke.log | awk 'NR>1 {print $2, $3, $7, $11}' > p_trace.dat
# columns: step, Pxx, Pyy, Pzz
```

**Thresholds for converged NPT:**
- |P_avg − 1.013 bar| < 50 bar (after equilibration period): GREEN
- |P_avg| 50-500 bar: YELLOW (still equilibrating; extrapolate to determine eta)
- |P_avg| > 500 bar persistent: RED (barostat saturation, FF mismatch)

**Pressure anisotropy:**
- max(|Pxx|, |Pyy|, |Pzz|) - min(...) < 100 bar: GREEN
- > 100 bar after equilibration: YELLOW (suggests box hasn't equilibrated isotropically)

### B1. Box dynamics (NPT, the patch-grid catcher)

```bash
awk '!/^#/ {print $1, $2, $6, $10}' smoke.xst > box_trace.dat
# columns: step, ax, by, cz   (assuming orthogonal box)
```

For each dimension, fit:
- Linear: a(t) = a₀ + (da/dt) · t
- Exponential: a(t) = a_∞ + (a₀ - a_∞) · exp(-t/τ)

Then **extrapolate to production timescale**.

**Patch-grid risk check (for `useFlexibleCell yes`):**

```python
margin    = 5.0         # from config: margin
cutoff    = 12.0        # from config
pairlist  = 14.0        # from config: pairlistdist
patch_min = cutoff + pairlist + margin   # NAMD's minimum patch dimension

# Initial box from xst
initial_dim_z = 120.0
# Extrapolated equilibrium
eq_dim_z = 62.0   # from fit

# Patches per dimension when run started
n_patches_z = int(initial_dim_z / patch_min)

# Crash threshold: patch dim < cutoff
crash_dim_z = n_patches_z * cutoff   # below this, NAMD bails

if eq_dim_z < crash_dim_z:
    print("RED: patch-grid invalidation predicted")
    print(f"  eq_dim_z = {eq_dim_z}, crash threshold = {crash_dim_z}")
    print(f"  recommend margin >= {(initial_dim_z - eq_dim_z) / n_patches_z - cutoff - pairlist:.0f}")
```

This is the catch for the 2026-05-06 slab failure. The smoke shows z trending downward; extrapolation predicts the crash.

**Density check:**

```python
# Volume from box trace
volume_A3 = ax * by * cz
# Atom mass total (read from PSF — sum of mass column)
total_mass_amu = ...
# Density in g/cm³
rho = total_mass_amu * 1.66054 / volume_A3
# Compare to target
target_rho = 0.92    # NEC at 453 K
```

If extrapolated equilibrium ρ deviates from target by > 10%, FLAG. Either Packmol packing was wrong or target density was misestimated.

### C1. Throughput

```bash
grep "^TIMING:" smoke.log | awk '{print $2, $5, $9}' > timing.dat
# step, s/step, days/ns
```

**Reference benchmarks (A100 PCIE 40GB, 1 fs dt, NAMD 3.0.x multicore-CUDA):**

| Atoms | ns/day (rough) |
|---|---|
| 10 k | 60-100 |
| 25 k | 30-50 |
| 50 k | 18-30 |
| 100 k | 10-18 |
| 200 k | 5-10 |
| 500 k | 2-5 |

Adjust ±30% for: rigidBonds water (faster), PME grid spacing, switching distance, replica/ensemble overhead.

**Risk indicators:**
- Throughput < 50% of benchmark: bad node, thermal throttle, configuration overhead → investigate
- Step-time variance > 30%: I/O bottleneck or shared GPU contention
- Throughput slowly degrading: memory leak (rare in NAMD but possible with long runs)

**Predict production walltime:**
```
production_walltime_hr = (production_numsteps / 1e6) / (smoke_ns_per_day / 24)
```
If this exceeds requested walltime + 50% buffer: RED. Either request more wall or reduce numsteps.

### C2. GPU memory

NAMD doesn't log GPU memory directly. Use `srun --pty nvidia-smi` mid-run if accessible, or rely on the SLURM job's `--mem-per-gpu` reservation.

For NAMD 3.0.x A100, rough memory per atom: 200-400 bytes. For 50 k atoms: ~10-20 MB GPU memory — tiny. Memory issues only emerge for > 1 M atom systems on smaller GPUs.

### D1. Reproducibility check (iteration ≥ 2 with identical config)

If your previous smoke produced `smoke_npt_001.log` and current is `smoke_npt_002.log`:

```bash
# Energy curves
diff <(grep "^ENERGY:" smoke_npt_001.log | awk '{print $2, $12}') \
     <(grep "^ENERGY:" smoke_npt_002.log | awk '{print $2, $12}') | head

# Throughput
echo "001:"; grep "^TIMING:" smoke_npt_001.log | tail -3
echo "002:"; grep "^TIMING:" smoke_npt_002.log | tail -3
```

NAMD with `langevin on` is stochastic; expect minor differences from random number streams (different velocities reassigned, slightly different trajectories) but:
- Energy curves should overlay within thermal noise (~few kcal/mol)
- Box trajectories should be statistically indistinguishable
- Throughput within ±5%

If diverging: deterministic non-reproducibility = bug. Investigate.

---

## NAMD-specific failure modes & how smoke surfaces them

| Failure mode | Manifestation in smoke | What to extract |
|---|---|---|
| **Patch-grid invalidation** (slab NPT) | Box z trend extrapolates below crash threshold | Linear fit on z(t); compare extrapolated equilibrium to patch-min |
| **NEC density way off** | Extrapolated box volume doesn't match target density | Compute ρ from extrapolated box; compare to target |
| **Initial-geometry overlap** | NaN energies in first 100 steps; "atom moving too fast" FATAL | Check first 10 ENERGY lines; if none printed, 100% sure of overlap |
| **Insufficient minimization** | Atoms moving too fast at start of heating (after min) | Check for "FATAL: Atom velocity > 12000" near step 1000-2000 |
| **PME grid wrong** | "PME grid does not match" warning at start | grep early log for PME warnings |
| **Pt melting** (1000 K, no fixedAtoms) | RMSD of "fixed" Pt atoms drifting | Compute Pt RMSD from DCD; should be near 0 with fixedAtoms |
| **Barostat saturation** (NPT) | Pressure components never settle near target | Plot PRESSAVG; check it's converged |
| **Force-field parsing error** | "Couldn't find parameter" early in log | grep for "MISSING PARAMETER" or similar |
| **Walltime overrun** | Throughput much slower than benchmark | Throughput vs benchmark; project production walltime |
| **Restart write failure** | No restart files at end of smoke | `ls *.restart.*` |
| **Numerical instability** (timestep too large) | Energy drift; growing variance over time | Drift slope on potential energy |
| **rigidBonds violation** | Particular SHAKE warnings; "exceeded SHAKE iterations" | grep for SHAKE in log |
| **GPU memory pressure** (rare for typical sizes) | OOM error or early "device error" | Mid-run `nvidia-smi` |

---

## Standard NAMD smoke recipes

### Recipe 1: NPT smoke for MD ensemble

Reduce a production NPT config to a smoke variant:

```bash
sed -e 's|^minimize *.*|minimize 10000|' \
    -e 's|set stepsPerHeat *.*|set stepsPerHeat 5000|' \
    -e 's|^run 5000000.*|run 5000|' \
    -e 's|outputName *\([^ ]*\) *|outputName \1_smoke|' \
    npt_equilibration.namd > npt_smoke.namd
```

This keeps full minimization (10 k steps; required for dense systems), shorter heating ramp (50 ps total), and 5 ps of NPT. Total: ~30-90 sec on A100 for 12 k atoms; ~3-10 min for 50 k atoms.

**Critical:** keep `minimize` length identical to production. Most "minimize too short" bugs surface as "atoms moving too fast" at heating start, which is exactly what the smoke should be testing.

### Recipe 2: 1000 K decorrelation smoke

```bash
sed -e 's|^run 100000000.*|run 100000|' \
    -e 's|outputName *\([^ ]*\) *|outputName \1_smoke|' \
    randomization_1000K.namd > randomization_smoke.namd
```

100 k steps = 100 ps. Catches: NEC stability at 1000 K, Pt fixedAtoms behavior, throughput sanity. ~1-3 min on A100.

### Recipe 3: Cooling + production smoke

```bash
sed -e 's|^run 12650000.*|run 50000|' \
    -e 's|set stepsPerTemp *.*|set stepsPerTemp 5000|' \
    cooling_production_453K.namd > cool_prod_smoke.namd
```

Reduces cooling steps from 150 ps each to 5 ps each (so 14 × 5 = 70 ps cooling), then 50 ps production. Catches: NPT-to-NVT handoff issues, snapshot loading errors.

---

## What goes in a NAMD smoke analysis

Concrete fields for `SMOKE_ANALYSIS_NNN.md` when the campaign uses NAMD:

```markdown
## Measurements extracted

| Signal              | Method            | Observed                | Expected (Layer A)      | Status |
|---------------------|-------------------|-------------------------|-------------------------|--------|
| Throughput          | TIMING / ns/day   | 28 ns/day               | 25-30 ns/day (50k @ A100) | GREEN |
| Energy drift        | linear fit on PE  | 2 kcal/mol/ns           | < 1 kcal/mol/ns         | YELLOW |
| Temperature avg     | post-equil mean   | 452.7 K                 | 453 K target            | GREEN |
| Temperature σ       | post-equil stdev  | 5.2 K                   | < 8 K for 50k           | GREEN |
| Pressure avg (xx)   | PRESSAVG late     | -45 bar                 | ~1 bar after eq         | YELLOW |
| Box trajectory (z)  | linear fit on xst | -0.105 Å/ps             | shrinkage to ~62 Å      | RED    |
| Density extrapolated| ρ from final fit  | 0.94 g/cm³              | 0.92 g/cm³ target       | GREEN |
| Restart files       | filesystem check  | all 3 written           | all 3 expected          | GREEN |
| FATAL count         | grep              | 0                       | 0                       | GREEN |

## Extrapolation to production

- Box z: linear fit predicts z=35 Å (patch-grid crash threshold) at t=850 ps. Production runs 5 ns. **CRASH PREDICTED at ~850 ps.**
- Throughput: 28 ns/day → 5 ns production needs 4.3 hr. Walltime requested 12 hr. GREEN budget.
- Energy drift at 2 kcal/mol/ns over 5 ns = 10 kcal/mol total. Acceptable for NPT.

## Findings

🔴 RED: patch-grid crash predicted from box-z extrapolation. Action: increase margin from 5.0 to 30.0 (gives n_patches_z=2, accommodates equilibrium z down to ~52 Å with safety).

🟡 YELLOW: pressure anisotropy persistent at -45 bar avg. Likely fine after extended equilibration but worth monitoring. Acceptable for production.

✅ GREEN: throughput, density, energy drift, restart files all within expected.

## Decision

**Action: fix and re-smoke.**
- Apply: `sed -i 's|^margin.*5.0|margin 30.0|' configs/npt_equilibration.namd`
- Re-deploy and re-run smoke
- On next iteration, verify box trajectory no longer extrapolates to crash threshold within 5 ns
```

---

## Cross-references

- `compute-validation/SKILL.md` — parent skill
- `compute-validation/workflows/smoke-analysis.md` — the framework this applies
- `compute-validation/workflows/verification.md` — Layer A reasoning that informs what to look for
- `compute-strategy/backends/alpine.md` — Alpine HPC where NAMD runs in this environment
- For project-specific NAMD failure-mode catalogs: see the project's `.priors.yaml` and `HPC_PLAYBOOK.md`
