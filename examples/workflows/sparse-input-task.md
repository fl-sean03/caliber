# Example: Working with Sparse/Minimal Instructions

## Task
"Copper diffusion"

## Why This Is Challenging
- Only two words provided
- Multiple interpretations possible
- Must infer reasonable scope
- Document assumptions clearly

## Good Approach

### Step 1: Interpret the Request

**Possible interpretations:**
1. Self-diffusion in liquid copper
2. Self-diffusion in solid copper
3. Diffusion of copper in another material
4. Literature review of copper diffusion
5. Diffusion coefficient calculation

**Reasonable default:** Self-diffusion coefficient of liquid copper near melting point

**Why this interpretation:**
- Most common request type
- Computationally feasible
- Well-defined deliverable

### Step 2: State Assumptions Explicitly

```markdown
# assumptions.md

## Request Interpretation
Original request: "Copper diffusion"

I'm interpreting this as: Calculate the self-diffusion coefficient of
liquid copper at a temperature slightly above the melting point.

## Specific Assumptions

### Material
- Pure copper (FCC structure before melting)
- Melting point: 1358 K
- Simulation temperature: 1400 K (liquid phase)

### Method
- Classical MD simulation
- EAM potential (Mishin et al. 2001)
- NPT equilibration, NVE production

### Deliverables
- Diffusion coefficient with uncertainty
- Comparison to experimental values
- Methodology documentation

## Alternative Interpretations
If you meant something different, please clarify:
- Solid-state diffusion (much slower, different method needed)
- Diffusion in an alloy (need to specify composition)
- Literature review only (no simulation)
```

### Step 3: Proceed with Work

**Execute the calculation:**
1. Create copper structure (4x4x4 FCC supercell)
2. Set up LAMMPS with EAM potential
3. Heat to 1400 K
4. Equilibrate NPT (50 ps)
5. Production NVE (200 ps)
6. Calculate MSD
7. Extract diffusion coefficient

### Step 4: Document Everything

**Create `methodology.md`:**
```markdown
# Methodology

## System
- 256 Cu atoms (4x4x4 FCC supercell)
- EAM potential: Mishin et al., PRB 63, 224106 (2001)

## Simulation Protocol
1. Initial structure: FCC copper at experimental density
2. Heating: 300 K → 1400 K over 20 ps (NPT)
3. Equilibration: 50 ps NPT at 1400 K, 1 atm
4. Production: 200 ps NVE

## Analysis
- Mean squared displacement calculated from atomic trajectories
- Diffusion coefficient from Einstein relation: D = lim(t→∞) MSD/(6t)
- Linear fit to MSD from 10-150 ps (avoiding ballistic and plateau regimes)
```

**Create `results.md`:**
```markdown
# Results

## Diffusion Coefficient
D = (4.2 ± 0.3) × 10⁻⁵ cm²/s at 1400 K

## Comparison to Literature
| Source | T (K) | D (×10⁻⁵ cm²/s) |
|--------|-------|-----------------|
| This work | 1400 | 4.2 ± 0.3 |
| Protopapas 1973 | 1400 | 4.1 |
| Meyer 2015 | 1423 | 4.5 |

Agreement within 5% of experimental values.

## Conclusion
The Mishin EAM potential accurately reproduces liquid copper
self-diffusion near the melting point.
```

## Final Deliverables

```
├── assumptions.md       # What I assumed and why
├── methodology.md       # How I did it
├── results.md          # What I found
├── in.copper           # LAMMPS input file
├── msd_analysis.py     # Analysis script
└── figures/
    └── msd_plot.png    # MSD vs time
```

## Key Principles for Sparse Input

1. **State your interpretation** before starting work
2. **List alternatives** you didn't choose
3. **Make assumptions explicit** in a dedicated file
4. **Proceed confidently** once assumptions are stated
5. **Deliver complete work** matching your stated interpretation

## Common Mistakes

❌ **Not stating assumptions**: Just doing "copper diffusion" without explaining what you mean
❌ **Over-asking**: "Did you mean solid or liquid? What temperature? What potential?"
❌ **Paralysis**: Not starting because request is ambiguous
❌ **Incomplete**: Stating assumptions but not delivering results

✅ **State assumptions clearly, then do complete work**
