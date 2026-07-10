---
name: ggen
description: Generate candidate crystal structures from a chemical formula and assess their stability using ggen. Use when you need trial structures for a composition with no known experimental structure, or want stability-ranked polymorph candidates before running MD/DFT.
---

# ggen Skill

Crystal structure generation and stability assessment using ggen.

**Validated: 2026-01-24** - API tested and working.

## When to Use This Skill

Use ggen when you need to:
- Generate candidate crystal structures from a chemical formula
- Explore a chemical space (e.g., "find structures in Fe-Mn-Si")
- Assess thermodynamic stability (convex hull analysis)
- Check dynamical stability (phonon calculations)

Use Materials Project / materials-database skill when:
- You need KNOWN structures (already in databases)
- You want experimental data

**ggen generates NEW candidate structures. Materials databases provide KNOWN structures.**

## What ggen Provides

- **Structure generation** - Creates crystal structures using PyXtal
- **Space group exploration** - Systematically tries different symmetries
- **ML relaxation** - Optimizes structures with ORB potentials
- **Convex hull** - Identifies thermodynamically stable phases
- **Phonon checks** - Validates dynamical stability

## Installation

**IMPORTANT**: Install from GitHub, NOT PyPI:
```bash
pip install git+https://github.com/ourofoundation/ggen.git
```

WARNING: `pip install ggen` installs a different package (grid mesh generator).

Requires GPU for efficient relaxation.

### Verification

```bash
python -c "from ggen import GGen; print('ggen:', GGen)"
```

### Model Cache

ORB models cached in: `~/.cache/science-agent/ggen/`

### Showcase Demo

See: `showcases/ggen-integration/workspace/demo_ggen.py`

## Core Concepts

### ChemistryExplorer

High-level systematic exploration:

```python
from ggen import ChemistryExplorer

explorer = ChemistryExplorer(output_dir="./runs")
result = explorer.explore(
    chemical_system="Li-P-S",   # Elements to explore
    max_atoms=20,                # Max atoms per unit cell
    num_trials=25,               # Generation attempts per stoichiometry
    compute_phonons=False        # Skip phonons for speed
)
```

### GGen

Lower-level structure generation:

```python
from ggen import GGen

ggen = GGen()
result = ggen.generate_crystal(
    formula="BaTiO3",
    num_trials=10,
    optimize_geometry=True
)

# result is a dict with these keys:
# - 'formula': str
# - 'structure': pymatgen Structure (best structure)
# - 'final_space_group': int
# - 'final_space_group_symbol': str
# - 'best_crystal_energy': float (eV)
# - 'optimization_steps': int
# - 'final_fmax': float (eV/A)
# - 'all_relaxed_trials': list of dicts (all generated structures)
# - 'cif_content': str (CIF file content)

print(f"Best: {result['final_space_group_symbol']}, E={result['best_crystal_energy']:.4f} eV")
structure = result['structure']  # pymatgen Structure
```

## Common Patterns

### Explore a Chemical System

```python
from ggen import ChemistryExplorer

explorer = ChemistryExplorer(output_dir="./ggen_runs")

result = explorer.explore(
    chemical_system="Li-Co-O",
    max_atoms=24,
    num_trials=30,
    min_fraction={"Li": 0.2},  # At least 20% Li
    compute_phonons=True        # Check stability
)

# Access results
print(f"Generated {result.total_structures} structures")
print(f"On-hull phases: {result.on_hull_count}")

# Get stable structures
for structure in result.stable_structures:
    print(f"{structure.formula}: {structure.energy_above_hull:.3f} eV/atom")
```

### CLI Usage

```bash
# Explore a system
python -m ggen.scripts.explore Fe-Mn-Si --max-atoms 24 --num-trials 25

# Run phonon calculations on candidates
python -m ggen.scripts.phonons --system Li-P-S --e-above-hull 0.05

# Export top candidates
python -m ggen.scripts.export Li-Co-O -n 10

# Generate report
python -m ggen.scripts.report Li-P-S
```

### Get Structures for Further Analysis

```python
from ggen import ChemistryExplorer

explorer = ChemistryExplorer(output_dir="./runs")
result = explorer.explore(chemical_system="Li-P-S", max_atoms=16)

# Get CIF files for stable candidates
for structure in result.get_structures_near_hull(e_above_hull=0.05):
    cif_path = structure.to_cif(f"{structure.formula}.cif")

    # Now use these structures for MD, DFT, etc.
    # with lammps-simulation, quantum-espresso, or mlip-simulation skills
```

## Integration with Other Skills

ggen generates structures. Other skills analyze them:

```
ggen (structure generation)
    │
    ├── mlip-simulation → Quick ML potential checks
    ├── torch-sim → High-throughput screening
    ├── lammps-simulation → Classical MD
    ├── quantum-espresso → DFT validation
    └── data-analysis → Property analysis
```

### Example Workflow

```python
# 1. Generate candidates with ggen
from ggen import ChemistryExplorer
explorer = ChemistryExplorer()
result = explorer.explore("Li-P-S", max_atoms=20)

# 2. Get promising structures
candidates = result.get_structures_near_hull(e_above_hull=0.1)

# 3. Further analyze with other tools (e.g., torch-sim for MD)
from torch_sim import integrate
from torch_sim.models import MACEModel

model = MACEModel.from_pretrained("mace-mp-0-medium")
for candidate in candidates:
    structure = candidate.to_pymatgen()
    # Run MD to check ionic conductivity...
```

## Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_atoms` | 20 | Maximum atoms per unit cell |
| `min_atoms` | 2 | Minimum atoms per unit cell |
| `num_trials` | 15 | Generation attempts per stoichiometry |
| `max_stoichiometries` | 100 | Limit search space |
| `compute_phonons` | False | Run phonon stability checks |
| `min_fraction` | {} | Minimum element fractions |
| `preserve_symmetry` | True | Maintain space group during relaxation |

## Understanding Results

### Convex Hull

- **On hull (e_above_hull = 0)**: Thermodynamically stable
- **Near hull (< 0.05 eV/atom)**: Potentially synthesizable
- **Far from hull (> 0.1 eV/atom)**: Likely unstable

### Dynamical Stability

- **No imaginary phonons**: Dynamically stable
- **Imaginary modes present**: Structure may distort or decompose

## Limitations

- Generation is stochastic (results vary between runs)
- Default 15 trials may be insufficient for complex systems
- Phonon calculations are expensive
- ORB potentials have their own accuracy limits

## Performance Tips

1. **Start with few trials** - Increase if needed
2. **Skip phonons initially** - Add later for promising candidates
3. **Use GPU** - Much faster relaxation
4. **Constrain composition** - Use `min_fraction` / `max_fraction`

## References

- [ggen GitHub](https://github.com/ourofoundation/ggen)
- [Ouro Foundation](https://ouro.foundation)
- [PyXtal](https://pyxtal.readthedocs.io/) - Underlying structure generator

## See Also

- `materials-database` skill - Query known structures
- `mlip-simulation` skill - ML potential calculations
- `torch-sim` skill - High-throughput screening
