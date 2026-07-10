# ggen Integration Showcase - Prompt

## Overview

This showcase demonstrates the agent using ggen for structure generation
as part of a materials discovery workflow.

## The Scenario

You need to find stable crystal structures in a chemical system. ggen
handles structure generation and initial stability screening. The agent
then takes the candidates and performs additional analysis.

## Prompt to Give the Agent

```
I need to find thermodynamically stable crystal structures in the Li-S
binary system for potential battery cathode applications.

Use ggen to:
1. Explore the Li-S chemical space
2. Generate candidate structures with different stoichiometries
3. Assess thermodynamic stability (convex hull analysis)

Then take the top candidates (on or near the hull) and:
1. Report their structures, space groups, and formation energies
2. Discuss which compositions look most promising
3. Suggest next steps for validation

Keep it quick - use max_atoms=12 and num_trials=10 per stoichiometry.
```

## Alternative Prompt (Simpler, Faster)

```
Demonstrate ggen's structure generation capability by generating
NaCl structures. Show the API usage and report the results.
```

## Notes

- This is a minimal showcase designed to demonstrate ggen integration
- The agent should recognize ggen as the right tool for structure generation
- **Li-S binary system is used instead of Li-P-S** (faster - fewer stoichiometries)
- If ggen is not installed, the agent should note this and explain what it would do
- The emphasis is on the agent USING ggen, not replacing it

## Installation Note

**IMPORTANT**: ggen must be installed from GitHub, not PyPI:
```bash
pip install git+https://github.com/ourofoundation/ggen.git
```

The `pip install ggen` command installs a different, unrelated package.

## Expected Duration

- Simple NaCl generation: 1-2 minutes
- Li-S exploration (12 atoms, 10 trials): 5-10 minutes
