# Pattern: Error Detection and Recovery

## Overview
When you make a mistake, the key is to:
1. **Notice** it happened
2. **Document** what went wrong
3. **Fix** the issue
4. **Verify** the fix worked

## Example: Wrong Units in Simulation

### The Error
Set up argon simulation with ε = 119.8 K (temperature units) but LAMMPS expected kcal/mol.

### Detection
After running, checked results:
- Expected diffusion: ~2.4 × 10⁻⁵ cm²/s
- Got: 8.7 × 10⁻³ cm²/s (360× too high!)

**Red flag:** Result is physically unreasonable

### Documentation

```markdown
# error_log.md

## Error 1: LJ Parameter Units

### What Happened
Used ε = 119.8 in LAMMPS with 'real' units, but this value is in Kelvin.
LAMMPS 'real' units expect ε in kcal/mol.

### How I Noticed
Diffusion coefficient was 360× too high:
- Expected: 2.4 × 10⁻⁵ cm²/s (Rahman 1964)
- Got: 8.7 × 10⁻³ cm²/s

### Root Cause
Copied ε = 119.8 from paper without converting:
ε/kB = 119.8 K → ε = 119.8 × 0.001987 = 0.238 kcal/mol

### Fix Applied
Changed `pair_coeff 1 1 119.8 3.405` to `pair_coeff 1 1 0.238 3.405`

### Verification
Re-ran simulation:
- Got: 2.43 × 10⁻⁵ cm²/s
- Within 1.3% of literature ✓
```

### The Fixed Input
```lammps
# CORRECT - ε in kcal/mol for 'real' units
pair_style lj/cut 10.0
pair_coeff 1 1 0.238 3.405  # ε=0.238 kcal/mol, σ=3.405 Å
```

## Example: Calculation Didn't Converge

### The Error
SCF calculation for NaCl stopped at 100 iterations without converging.

### Detection
```
     iteration #  100     ecut=    60.00 Ry
     convergence NOT achieved after 100 iterations
```

### Documentation

```markdown
# error_log.md

## Error 2: SCF Convergence Failure

### What Happened
NaCl calculation failed to converge with default settings

### Symptoms
- Energy oscillating between -XX.XX and -YY.YY
- diagonalization warnings in output
- "convergence NOT achieved" after 100 iterations

### Diagnosis
Default mixing_beta = 0.7 too aggressive for ionic system with
large charge transfer between Na and Cl.

### Fix Applied
1. Reduced mixing_beta: 0.7 → 0.3
2. Added 'mixing_mode = local-TF'
3. Increased max iterations: 100 → 200

### Verification
Re-ran with new settings:
- Converged in 47 iterations
- Final energy: -XX.XXXXX Ry
- Forces converged to < 10⁻⁴ Ry/bohr ✓
```

## Example: Result Doesn't Match Literature

### The Error
Calculated thermal expansion coefficient 50% higher than literature.

### Detection
- My result: α = 36 × 10⁻⁶ K⁻¹
- Literature: α = 24 × 10⁻⁶ K⁻¹
- Discrepancy: 50%

### Documentation

```markdown
# error_log.md

## Error 3: Thermal Expansion Too High

### What Happened
Calculated α = 36 × 10⁻⁶ K⁻¹ vs literature 24 × 10⁻⁶ K⁻¹

### Investigation
1. Checked temperature control - OK
2. Checked pressure - OK
3. Checked equilibration - PROBLEM FOUND

### Root Cause
Only 10 ps equilibration at each temperature. System wasn't fully
equilibrated before measuring volume.

### Fix Applied
Increased equilibration from 10 ps to 100 ps at each temperature

### Verification
After longer equilibration:
- Got: α = 25.2 × 10⁻⁶ K⁻¹
- Within 5% of literature ✓
```

## The Error Recovery Workflow

```
┌─────────────┐
│ Run         │
│ Calculation │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Check       │
│ Results     │
└──────┬──────┘
       │
       ▼
   ┌───────┐
   │ Seem  │─── Yes ──► Document & Done
   │ Right?│
   └───┬───┘
       │ No
       ▼
┌─────────────┐
│ DOCUMENT    │
│ the error   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ DIAGNOSE    │
│ root cause  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ FIX         │
│ the issue   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ VERIFY      │
│ fix worked  │
└──────┬──────┘
       │
       └──────► Back to "Check Results"
```

## Key Principles

1. **Always check results** against expectations/literature
2. **Document errors immediately** - don't hide them
3. **Find root cause** - don't just try random fixes
4. **Verify the fix** - don't assume it worked
5. **Learn from errors** - apply lessons to future work
