# torch-sim Screening Showcase - Prompt

## Overview

This showcase demonstrates the agent using torch-sim for high-throughput
materials screening, achieving performance impossible with ASE-based tools.

## The Scenario

You have a set of candidate structures and need to quickly screen
them for stability. torch-sim's batched GPU execution makes this
practical at scale.

## Prompt to Give the Agent

```
I need to screen a set of elemental metal structures for stability
using ML potentials.

Use torch-sim with MACE to:
1. Create 15-20 test structures (FCC, BCC, HCP metals)
2. Batch optimize all structures using torch-sim
3. Calculate final energies

Report:
- Total screening time
- Throughput (structures per minute)
- Final energies for each structure
- Comparison to what sequential ASE would take

Use torch-sim's batched operations to maximize GPU utilization.
```

## Alternative Prompt (From Materials Project)

```
Demonstrate torch-sim's high-throughput capability by:
1. Fetching 20-30 structures from Materials Project (any system)
2. Batch optimizing them with torch-sim + MACE
3. Reporting performance metrics and ranked results

Show the performance advantage over sequential ASE.
```

## Notes

- This showcase emphasizes PERFORMANCE - structures per minute
- torch-sim should show clear advantage for batch operations
- If torch-sim is not installed, agent should explain the capability
- GPU is required for meaningful performance comparison

## Installation

```bash
pip install torch-sim-atomistic mace-torch
```

## Expected Duration

- With torch-sim + GPU: 1-2 minutes for 15-20 structures
- With ASE (for comparison): Would take 10-20+ minutes
