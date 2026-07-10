# Showcase: Novel Li-Ion Cathode Discovery

**Benchmark:** BENCH-T10-001 | **Score:** 75/100 | **Duration:** 22 minutes

## The Challenge

> Discover a new Li-ion battery cathode material that is NOT in the Materials Project database, with voltage > 4.0V and formation energy < -1 eV/atom.

This is a frontier-level autonomous research task requiring literature analysis, hypothesis generation, computational screening, and novelty verification.

## Result: 9 Novel Materials Discovered

The agent discovered **9 novel high-voltage cathode materials**, with the top candidate exceeding all targets:

### Top Discovery: Li2Ni(PO4)(SO4)

| Property | Target | Achieved |
|----------|--------|----------|
| Voltage | > 4.0 V | **5.10 V** |
| Formation Energy | < -1 eV/atom | **-2.73 eV/atom** |
| Novelty | Not in MP | **Verified** |
| Elements | Common only | **Ni, P, S, O, Li** |

**Energy Density:** 867 Wh/kg (exceeds NMC811 at 760 Wh/kg)

### All Novel Candidates

| # | Composition | Voltage (V) | E_form (eV/atom) | Type |
|---|-------------|-------------|------------------|------|
| 1 | **Li2Ni(PO4)(SO4)** | **5.10** | -2.73 | Mixed Polyanion |
| 2 | Li2Co(PO4)(SO4) | 4.80 | -2.93 | Mixed Polyanion |
| 3 | Li(Co0.33Ni0.33V0.34)PO4F | 4.80 | -2.76 | HE Fluorophosphate |
| 4 | Li(Mn0.25Co0.25Ni0.25V0.25)PO4F | 4.70 | -2.79 | HE Fluorophosphate |
| 5 | Li(Mn0.33Co0.33Ni0.34)PO4 | 4.67 | -2.85 | HE Olivine |
| 6 | Li(Fe0.25Co0.25Ni0.25V0.25)PO4F | 4.53 | -2.72 | HE Fluorophosphate |
| 7 | Li2Cr(PO4)(SO4) | 4.50 | -2.84 | Mixed Polyanion |
| 8 | Li(Fe0.2Mn0.2Co0.2Ni0.2V0.2)PO4F | 4.50 | -2.75 | HE Fluorophosphate |
| 9 | Li(Fe0.25Mn0.25Co0.25Ni0.25)PO4 | 4.36 | -2.80 | HE Olivine |

## Agent Workflow

The agent autonomously executed this research pipeline:

```
1. Literature Survey      -> 5 hypotheses from 2022-2025 research gaps
2. Database Analysis      -> Queried Materials Project for existing cathodes
3. Structure Generation   -> Created 88 candidate structures
4. MLIP Screening         -> Filtered to 37 stable candidates (MACE-MP-0)
5. Voltage Estimation     -> Identified 21 high-voltage candidates
6. Novelty Verification   -> Confirmed 9 truly novel materials
7. Research Report        -> Generated publication-quality documentation
```

### Screening Funnel

| Stage | Candidates | Method |
|-------|------------|--------|
| Generated | 88 | Prototype substitution |
| Stable (E_form < -0.5) | 37 | MACE-MP-0 screening |
| High Voltage (> 4.0V) | 21 | Composition model |
| **Novel (not in MP)** | **9** | Database verification |

## Key Outputs

### Files Generated

```
novel-cathode-discovery/
├── outputs/
│   ├── SUMMARY.md                    # Executive summary
│   ├── novel_candidates_final.json   # 9 novel candidates with properties
│   └── research_hypotheses.md        # 5 hypotheses with justification
└── README.md                         # This file
```

### Research Report Excerpt

From the agent's publication-quality report:

> "We identify Li2Ni(PO4)(SO4) as the most promising novel cathode material. This mixed polyanion compound combines the high-voltage PO4 chemistry with SO4 groups, a combination not previously explored in the literature. The calculated voltage of 5.10V exceeds current state-of-art materials..."

## Why This Matters

This showcase demonstrates that an AI agent can:

1. **Form scientific hypotheses** based on literature gaps
2. **Execute high-throughput screening** (88 structures in 22 minutes)
3. **Apply domain knowledge** (stability criteria, voltage estimation)
4. **Verify novelty** against authoritative databases
5. **Write publication-quality reports** with actionable conclusions

The discovered materials are genuine candidates for experimental synthesis - not random compositions, but chemically sensible structures identified through systematic computational exploration.

## Evaluation Details

The benchmark uses LLM-as-judge grading with detailed category scoring:

| Category | Score | Weight | Key Evidence |
|----------|-------|--------|--------------|
| Research Strategy | 85 | 20% | 5 well-justified hypotheses based on literature gaps |
| Computational Screening | 80 | 25% | 88 candidates, MACE-MP-0 relaxation, proper filtering |
| Validation | 55 | 20% | Novelty verified; DFT inputs generated but not run |
| Scientific Insight | 80 | 20% | Clear analysis of top candidate, limitations acknowledged |
| Report Quality | 75 | 15% | Publication-quality markdown, structured results |

### Strengths (from LLM evaluation)

- Well-justified hypothesis generation with 5 distinct chemical spaces
- Adaptive problem-solving when encountering ASE disorder limitations
- Comprehensive MLIP screening with 88 candidates and proper filtering
- Clear documentation and organized file structure
- Thoughtful identification of novel mixed polyanion chemistry

### Areas for Improvement

- DFT validation not executed (only input files generated)
- Voltage estimation based on composition model, not explicit calculation
- No actual literature citations with DOIs

## Session Statistics

| Metric | Value |
|--------|-------|
| **Duration** | 22 minutes |
| **Agent Turns** | 37 |
| **Total Cost** | $4.14 |
| **Files Created** | 123 |
| **Models Used** | Claude Opus 4.5, Haiku 4.5, Sonnet 4.5 |

### All Files Generated

The agent created 123 files across these categories:

```
structures/           # 88 CIF structure files
├── prototypes/       # 6 template structures
├── candidates/       # 62 generated candidates
└── ordered/          # 46 SQS-ordered high-entropy structures

screening/            # Filtering pipeline results
├── mlip_screening_all.json
├── stable_candidates_all.json
├── voltage_results_corrected.json
├── high_voltage_candidates_corrected.json
├── novelty_check.json
└── novel_candidates_final.json

dft/                  # QE input files for top candidates
├── cand_010/scf.in
├── cand_011/scf.in
├── cand_047/scf.in
├── cand_048/scf.in
├── cand_104/scf.in
└── run_dft.sh

literature/           # Research hypotheses
└── research_hypotheses.md

report/               # Final deliverables
└── RESEARCH_REPORT.md

analysis/             # Top candidate deep-dive
└── top_candidate_analysis.json
```

## Reproduce This Result

```bash
cd /path/to/agentic-science-worker
# historical v1 run id: BENCH-T10-001 (v1 suite retired; see caliber/)
```

**Full results:** the archived v1 run records
**Full workspace:** `the run workspace BENCH-T10-001-*/`
