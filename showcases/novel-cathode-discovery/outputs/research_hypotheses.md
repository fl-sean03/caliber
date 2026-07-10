# Research Hypotheses: Novel Li-Ion Cathode Materials

**Date:** 2026-02-23
**Benchmark:** BENCH-T10-001

## Executive Summary

Based on comprehensive literature review (2022-2025) and Materials Project database analysis, we identify **5 high-priority compositional spaces** that are:
1. Under-explored or absent from the Materials Project database
2. Scientifically justified based on recent research trends
3. Predicted to achieve high voltage (>4.0 V) and reasonable capacity

## Database Gap Analysis Summary

### Well-Represented in Materials Project:
- LiMO2 layered oxides (M = Co, Ni, Mn, Fe, V, Ti, Cr) - 100+ entries
- LiMPO4 olivines (M = Fe, Mn, Co, Ni, Cr, Cu, Zn) - 300+ entries
- Li2MSiO4 silicates (M = Fe, Mn, Co, Ni) - 73 entries
- LiMPO4F fluorophosphates (M = V, Fe, Mn, Co, Ni) - 34 entries

### Major Gaps Identified:
1. **High-entropy compositions (5+ TMs)** - ZERO entries
2. **Mixed polyanion systems** (e.g., Li2M(PO4)(SO4)) - ZERO entries
3. **Quaternary+ fluorophosphates** - ZERO entries
4. **Disordered rock-salt with high-entropy TMs** - Limited
5. **Honeycomb-ordered structures with Mo/W/Nb** - Limited

---

## Hypothesis 1: High-Entropy Fluorophosphates

### Rationale
- LiMPO4F (M = V, Fe, Mn) achieve 3.6-4.2 V, good stability
- High-entropy mixing stabilizes structures through configurational entropy
- NO high-entropy fluorophosphates in Materials Project database
- Recent literature shows HE stabilizes unusual TM combinations

### Proposed Compositions
```
Li(Fe0.2Mn0.2Co0.2Ni0.2V0.2)PO4F     - 5-component equimolar
Li(Fe0.2Mn0.2Co0.3V0.2Mo0.1)PO4F    - Mo-doped for higher voltage
Li(Mn0.25Co0.25Ni0.25V0.25)PO4F     - 4-component (no Fe)
```

### Expected Properties
- Voltage: 4.0-4.5 V (weighted average of constituent redox couples)
- Capacity: 140-160 mAh/g (1 Li per formula unit)
- Stability: Enhanced by configurational entropy (ΔSconf > 1.5R)
- Safety: Phosphate framework inherently stable

### Novelty Check
- MP Database: NO entries for 4+ TM fluorophosphates
- Literature: Limited to binary TM fluorophosphates

---

## Hypothesis 2: Honeycomb-Ordered Li2Ni2MO6 (M = Mo, W, Nb)

### Rationale
- Li2Ni2TeO6 achieves 4.5 V, 240 mAh/g but Te is expensive
- Mo6+/W6+/Nb5+ are isoelectronic alternatives to Te6+
- Honeycomb structure enables 2-electron Ni2+/Ni4+ redox
- Limited exploration of Mo/W in honeycomb ordering

### Proposed Compositions
```
Li2Ni2MoO6     - Mo replaces Te (cheap, stable)
Li2Ni2WO6      - W replaces Te (high voltage)
Li2Ni1.5Co0.5MoO6  - Mixed TM for stability
Li2Ni1.5Mn0.5MoO6  - Mn for cost reduction
```

### Expected Properties
- Voltage: 4.2-4.5 V (Ni2+/Ni4+ redox)
- Capacity: 200-240 mAh/g (2 Li per formula unit)
- Structure: C2/m or P21/c space group (honeycomb ordering)

### Novelty Check
- MP Database: Li2Ni2MoO6 not present, Li2Ni2WO6 not present
- Literature: Only Te-based honeycomb cathodes reported

---

## Hypothesis 3: Mixed Polyanion Systems

### Rationale
- Single polyanions (PO4, SO4, SiO4) have fixed voltage ranges
- Mixing polyanions could:
  - Create multi-plateau voltage profiles
  - Tune electronic structure
  - Enable novel structural frameworks
- ZERO mixed polyanion cathodes in MP database

### Proposed Compositions
```
Li2Fe(PO4)(SO4)     - Phosphate-sulfate hybrid
Li2V(PO4)(SO4)      - V for higher voltage
Li2Mn(PO4)(SO4)     - Mn for Jahn-Teller effects
Li3Fe(PO4)(SiO4)    - Phosphate-silicate hybrid
Li3V(PO4)(SiO4)     - V silicate-phosphate
```

### Expected Properties
- Voltage: 3.5-4.3 V depending on TM and anion ratio
- Capacity: 115-150 mAh/g
- Novel: Multi-plateau voltage profiles expected

### Novelty Check
- MP Database: NO Li2M(PO4)(SO4) or Li3M(PO4)(SiO4) entries
- Literature: Only isolated borophosphate examples

---

## Hypothesis 4: Fluorinated High-Entropy DRX (All Redox-Active)

### Rationale
- Disordered rock-salt (DRX) achieves 250-300 mAh/g
- Most DRX use inactive Ti/Al/Nb to dilute TMs (lowers voltage)
- Fluorination suppresses O2 loss, improves cycle life
- NO high-entropy fluorinated DRX with all redox-active TMs in database

### Proposed Compositions
```
Li1.3(Ni0.2Mn0.2Co0.2Fe0.2V0.2)0.7O1.7F0.3    - 5-TM, all redox-active
Li1.2(Ni0.25Mn0.25Co0.25V0.25)0.8O1.8F0.2     - 4-TM variant
Li1.3(Ni0.2Mn0.2Co0.2V0.2Mo0.2)0.7O1.7F0.3   - Mo for high voltage
```

### Expected Properties
- Voltage: 3.8-4.2 V (all TMs contribute to redox)
- Capacity: 220-280 mAh/g (Li-excess + anionic redox)
- Stability: F suppresses O2 release, HE prevents phase separation

### Novelty Check
- MP Database: NO fluorinated HE-DRX with 5+ TMs
- Literature: Fluorinated DRX exists, HE-DRX exists, but not combined

---

## Hypothesis 5: Nb/Mo-Containing Layered Oxides

### Rationale
- LiNbO2 and LiMoO2 are in MP but under-explored
- Nb5+ and Mo4+/Mo6+ enable multi-electron redox
- Mixing with Ni/Co could achieve high voltage + capacity
- Limited entries for mixed Nb/Mo layered oxides

### Proposed Compositions
```
LiNi0.5Nb0.5O2      - Nb stabilizes high-voltage Ni
LiNi0.5Mo0.5O2      - Mo enables 2e- redox
LiNi0.4Co0.3Nb0.3O2 - Ternary with Nb stabilization
Li1.1Ni0.4Mo0.5O2   - Li-excess Mo layered
```

### Expected Properties
- Voltage: 4.0-4.5 V (Ni2+/Ni4+ + Mo4+/Mo6+)
- Capacity: 180-220 mAh/g
- Stability: Nb5+ acts as structural pillar

### Novelty Check
- MP Database: Binary LiNbO2, LiMoO2 exist but ternary/quaternary limited
- Literature: Emerging interest but limited systematic exploration

---

## Screening Priority

### Phase 2 Structure Generation Order:

| Priority | Hypothesis | # Structures | Reasoning |
|----------|------------|--------------|-----------|
| 1 | HE Fluorophosphates | 50 | Highest novelty, clear gap |
| 2 | Honeycomb Mo/W | 30 | High capacity potential |
| 3 | Mixed Polyanions | 40 | Unexplored territory |
| 4 | HE Fluorinated DRX | 40 | High capacity, complex |
| 5 | Nb/Mo Layered | 40 | Lower risk, builds on known |

**Total: ~200 structures for screening**

---

## Success Criteria

For a candidate to be considered successful:

1. **Stability**: Formation energy < -1.0 eV/atom
2. **Metastability**: Energy above hull < 50 meV/atom
3. **Voltage**: > 4.0 V vs Li/Li+
4. **Capacity**: > 150 mAh/g theoretical
5. **Novelty**: NOT in Materials Project database
6. **Reasonable elements**: No radioactive, ultra-rare, or toxic elements

---

## Next Steps

1. Generate CIF/POSCAR files for all candidate structures
2. Run MLIP relaxation (MACE-MP-0) for rapid screening
3. Calculate formation energies and filter by stability
4. Estimate voltages for stable candidates
5. Select top 5-10 for DFT validation
6. Verify novelty against MP and literature
