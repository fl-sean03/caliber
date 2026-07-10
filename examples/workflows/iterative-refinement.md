# Example: Iterative Plan Refinement

## Task
"Calculate the band gap of GaN and compare to experimental values."

## Why This Requires Iteration
- PBE systematically underestimates band gaps
- Initial result will be "wrong" - this is expected
- Must recognize the problem and revise approach
- Document the reasoning process

## Good Approach

### Initial Plan
```markdown
# initial_plan.md

## Objective
Calculate band gap of GaN wurtzite structure

## Approach
1. Get structure from Materials Project
2. Run PBE SCF calculation
3. Run band structure calculation
4. Extract band gap
5. Compare to experimental value (3.4 eV)

## Expected Result
Band gap close to 3.4 eV
```

### Execute Initial Plan

**Run PBE calculation:**
- Structure: GaN wurtzite (mp-804)
- Functional: PBE
- Pseudopotentials: ONCV from PseudoDojo
- K-points: 8x8x6

**Result:** Band gap = 1.7 eV

### Recognize the Problem

```markdown
# problem_diagnosis.md

## Observation
PBE band gap (1.7 eV) is 50% lower than experimental (3.4 eV)

## Diagnosis
This is NOT an error in my calculation. PBE systematically underestimates
band gaps due to:
1. Self-interaction error in DFT
2. Missing derivative discontinuity
3. Approximate exchange-correlation functional

## Evidence
- Literature confirms PBE gives ~1.7 eV for GaN (Ref: Rinke et al., PRB 2008)
- My result matches other PBE calculations
- The physics is correct; the method has known limitations

## Options for Improvement
1. HSE06 hybrid functional (expensive but accurate)
2. GW calculations (very expensive, most accurate)
3. Scissors operator correction (empirical but fast)
4. Report PBE value with documented limitation
```

### Revise the Plan

```markdown
# revised_plan.md

## Problem
PBE underestimates band gap (1.7 vs 3.4 eV expected)

## Revised Approach
Option chosen: **HSE06 hybrid functional**

Rationale:
- HSE06 typically gives band gaps within 0.3 eV of experiment
- Computationally feasible for GaN unit cell
- Well-established method for semiconductors

## New Steps
1. Restart from converged PBE density
2. Run HSE06 SCF (may need more iterations)
3. Calculate band structure with HSE06
4. Extract corrected band gap

## Expected Result
Band gap 3.0-3.5 eV (closer to experimental 3.4 eV)
```

### Execute Revised Plan

**HSE06 calculation:**
- Starting density: From PBE
- Functional: HSE06 (mixing=0.25)
- Result: Band gap = 3.2 eV

### Document Learning

```markdown
# lesson_learned.md

## What Happened
1. Initial PBE calculation gave 1.7 eV (expected but wrong)
2. Recognized this as method limitation, not calculation error
3. Applied HSE06 correction
4. Final result: 3.2 eV (within 6% of experimental 3.4 eV)

## Key Insight
For band gap calculations, PBE is a starting point, not the answer.
Always plan for a correction step when band gaps are important.

## Future Recommendations
- For quick screening: PBE is fine (relative trends preserved)
- For accurate gaps: Budget for HSE06 or GW
- Always document which level of theory was used
```

## Final Deliverables

```
├── initial_plan.md
├── pbe_results/
│   ├── scf.out
│   └── bands.dat
├── problem_diagnosis.md
├── revised_plan.md
├── hse_results/
│   ├── scf.out
│   └── bands.dat
└── lesson_learned.md
```

## The Key Pattern

```
┌─────────────┐
│ Initial     │
│ Plan        │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Execute     │──────┐
│             │      │
└──────┬──────┘      │
       │             │
       ▼             │
┌─────────────┐      │
│ Evaluate    │      │
│ Results     │      │
└──────┬──────┘      │
       │             │
       ▼             │
   ┌───────┐         │
   │ Good? │─── Yes ─┼──► Done
   └───┬───┘         │
       │ No          │
       ▼             │
┌─────────────┐      │
│ Diagnose    │      │
│ Problem     │      │
└──────┬──────┘      │
       │             │
       ▼             │
┌─────────────┐      │
│ Revise      │      │
│ Plan        │──────┘
└─────────────┘
```

## Common Mistakes

❌ **Accepting wrong results**: "PBE gives 1.7 eV" without noting this is wrong
❌ **No diagnosis**: Jumping to a fix without understanding the problem
❌ **No documentation**: Fixing the problem but not writing down what happened
❌ **Stopping at diagnosis**: "PBE underestimates gaps" but not actually fixing it

✅ **Iterate until result is correct or limitation is clearly documented**
