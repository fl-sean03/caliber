# Example: Multi-Compound DFT Study

## Task
"Calculate formation energies for NaCl, KCl, and RbCl. Document issues encountered and lessons learned."

## Why This Is Non-Trivial
- Three separate calculations required
- Must track progress across all three
- Learning from first should improve later ones
- Documentation structure specified

## Good Approach

### Phase 1: Setup
```
Create directory structure FIRST:
├── nacl/
├── kcl/
├── rbcl/
├── references/          # For elemental calculations
└── results/
```

### Phase 2: First Compound (NaCl)

**Steps:**
1. Get NaCl structure from Materials Project
2. Get/download pseudopotentials (Na, Cl)
3. Set up SCF calculation
4. Run calculation
5. Check convergence - if issues, document and fix
6. Calculate formation energy: E_f = E(NaCl) - E(Na_metal) - 0.5*E(Cl2)
7. Document in `nacl/calculation.md`
8. Document any issues in `nacl/issues.md`

**Example issue documentation (nacl/issues.md):**
```markdown
## Issues Encountered

### 1. SCF Convergence
- Initial run failed to converge with default mixing_beta=0.7
- Solution: Reduced to mixing_beta=0.3
- Result: Converged in 12 iterations

### 2. K-point Convergence
- Tested 4x4x4, 6x6x6, 8x8x8 grids
- Energy converged to 1 meV/atom at 6x6x6
- Using 6x6x6 for production
```

### Phase 3: Second Compound (KCl)

**Apply lessons from NaCl:**
1. Start with mixing_beta=0.3 (learned from NaCl)
2. Use 6x6x6 k-points (known to be converged)
3. Reuse Cl pseudopotential and Cl2 reference calculation

**Document improvements in `kcl/improvements.md`:**
```markdown
## Improvements Applied from NaCl

1. **Mixing parameter**: Started with mixing_beta=0.3 instead of default
   - Result: Converged on first try (vs 2 attempts for NaCl)

2. **K-points**: Used 6x6x6 directly
   - Saved time on convergence testing

3. **Reference reuse**: Used same Cl2 calculation
   - Ensures consistency across compounds
```

### Phase 4: Third Compound (RbCl)

**Document efficiency gains in `rbcl/efficiency.md`:**
```markdown
## Efficiency Notes

### Time Comparison
| Compound | Setup Time | Compute Time | Issues |
|----------|------------|--------------|--------|
| NaCl     | 45 min     | 15 min       | 2      |
| KCl      | 15 min     | 12 min       | 0      |
| RbCl     | 10 min     | 14 min       | 0      |

### What Made RbCl Faster
1. Reused computational settings from KCl
2. No convergence testing needed
3. Reference calculations already done (Cl2)
```

### Phase 5: Compile Results

**Create `results/formation_energies.csv`:**
```csv
compound,formation_energy_eV,literature_eV,difference_percent,notes
NaCl,-4.26,-4.23,0.7,PBE with PAW pseudopotentials
KCl,-4.32,-4.28,0.9,Same methodology as NaCl
RbCl,-4.18,-4.15,0.7,Same methodology as NaCl
```

**Create `learning_summary.md`:**
```markdown
# Learning Summary

## Key Lessons
1. **Mixing parameter**: Default 0.7 too aggressive for ionic compounds. Use 0.3.
2. **K-points**: 6x6x6 sufficient for rock-salt structures
3. **Reference reuse**: Calculate Cl2 once, reuse for all chlorides

## Efficiency Gains
- First compound: 60 min total
- Second compound: 27 min (55% reduction)
- Third compound: 24 min (60% reduction)

## Recommendations for Future Work
- For other alkali halides, start with these settings
- May need to adjust for different crystal structures
```

## Final Deliverables Checklist

- [ ] `nacl/calculation.md` - NaCl methodology and results
- [ ] `nacl/issues.md` - Problems encountered with NaCl
- [ ] `kcl/calculation.md` - KCl methodology and results
- [ ] `kcl/improvements.md` - What was done better vs NaCl
- [ ] `rbcl/calculation.md` - RbCl methodology and results
- [ ] `rbcl/efficiency.md` - Efficiency gains documented
- [ ] `results/formation_energies.csv` - All results in one file
- [ ] `learning_summary.md` - Overall lessons learned

## Common Mistakes

❌ **Stopping after first compound**: "The pattern is established..."
❌ **Missing documentation files**: Doing calculations but not creating issues.md, improvements.md
❌ **Not applying lessons**: Repeating same mistakes in KCl that were fixed in NaCl
❌ **No final compilation**: Individual results but no summary CSV

✅ **Do all three compounds with full documentation**
