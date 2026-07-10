# ggen Integration Showcase - Expected Output

## Success Criteria

This showcase is successful when:

1. [x] Agent recognizes structure generation is needed
2. [x] Agent identifies ggen as the appropriate tool
3. [x] Agent calls ggen correctly (Python API)
4. [x] Agent interprets ggen output (structures, energies, hull distances)
5. [x] Agent provides scientific analysis of candidates
6. [x] Agent suggests reasonable next steps

## What the Agent Should Do

### 1. Understand the Task
- Recognize this is a materials discovery problem
- Identify that structure generation is the first step
- Know that ggen handles this type of exploration

### 2. Check/Install ggen
```bash
# ggen must be installed from GitHub, NOT PyPI
pip install git+https://github.com/ourofoundation/ggen.git
```

### 3. Use ggen

**Simple Generation (GGen class)**:
```python
from ggen import GGen

ggen = GGen()
result = ggen.generate_crystal(
    formula="NaCl",
    num_trials=5,
    optimize_geometry=True
)
print(f"Generated {len(result.structures)} structures")
```

**Chemical Space Exploration (ChemistryExplorer)**:
```python
from ggen import ChemistryExplorer

explorer = ChemistryExplorer(output_dir="./ggen_runs")
result = explorer.explore(
    chemical_system="Li-S",  # Binary system (faster than ternary)
    max_atoms=12,
    num_trials=10
)

print(f"Total structures: {result.total_structures}")
print(f"On-hull phases: {result.on_hull_count}")
```

### 4. Analyze Results
- Look at structures on/near the convex hull
- Identify promising stoichiometries
- Note space groups and structural features

### 5. Report Findings
- Top candidate structures with properties
- Scientific discussion of potential applications
- Suggested validation steps (phonons, MD, DFT)

## Example Output Markers

Look for:
- "Using ggen to explore the Li-S system"
- ggen API invocations (GGen or ChemistryExplorer)
- Discussion of convex hull / formation energies
- Stoichiometries like Li2S, LiS2, etc.
- Scientific reasoning about battery applications

## If ggen Is Not Installed

The agent should:
- Note that ggen is required but not installed
- Provide correct installation command: `pip install git+https://github.com/ourofoundation/ggen.git`
- **NOT** use `pip install ggen` (that's a different package!)
- Explain what it would do if ggen were available

## What This Showcases

- Agent knows when to use external tools
- Agent can integrate with external tools (ggen)
- Agent provides value beyond what ggen does (analysis, next steps)
- Complementary positioning: ggen generates, agent analyzes

## Not Required

- Perfect numerical results (ggen exploration has randomness)
- Specific file formats
- Running actual phonon calculations (that would be a follow-up)

## Performance Notes

| System | Stoichiometries | Expected Time |
|--------|-----------------|---------------|
| NaCl (simple) | 1 | 1-2 min |
| Li-S (binary) | ~10-15 | 5-10 min |
| Li-P-S (ternary) | ~242 | 30+ min (too slow for demo) |

For quick demos, use simple structures or binary systems.
