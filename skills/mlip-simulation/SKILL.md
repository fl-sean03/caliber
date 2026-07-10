---
name: mlip-simulation
description: Run molecular dynamics and materials calculations with ML interatomic potentials (MACE, CHGNet, M3GNet) via ASE — near-DFT accuracy at classical-MD cost. Use when asked to run simulations with ML/universal potentials, or when DFT would be too expensive (or is unavailable) but accuracy matters. For high-throughput screening of 10+ structures, see torch-sim.
---

# MLIP Simulation Skill

Run molecular dynamics and materials calculations using Machine Learning Interatomic Potentials (MLIPs) - achieving near-DFT accuracy at classical MD cost.

**Trigger**: Use when asked to run simulations with ML potentials, universal potentials, MACE, CHGNet, M3GNet, or when DFT would be too expensive but accuracy matters.

---

## When to Use This vs torch-sim

This skill uses **ASE** (Atomic Simulation Environment) as the backend. For **high-throughput screening** (10+ structures), consider using the **torch-sim** skill instead:

| Scenario | Recommended | Why |
|----------|-------------|-----|
| 1-5 structures | This skill (ASE) | Simpler setup |
| 10+ structures | torch-sim | 100x faster batching |
| Quick single test | This skill (ASE) | Less overhead |
| Large-scale screening | torch-sim | GPU batching, memory management |
| Learning/prototyping | This skill (ASE) | More examples, familiar |

**Rule of thumb**: For batch operations on many structures, use torch-sim. For single structures or learning, use this ASE-based approach.

See the `torch-sim` skill for high-throughput patterns.

---

## Available Universal Potentials

### MACE-MP-0 (Recommended for General Use)
- **Accuracy**: Highest among universal potentials
- **Parameters**: 4.7M (largest model)
- **Coverage**: 89 elements
- **Best for**: General property prediction, phonons, surfaces

### CHGNet
- **Accuracy**: Good, includes magnetic moments
- **Parameters**: ~400K (smallest, fastest)
- **Best for**: Batteries, Li-ion systems, charged species, oxidation states

### M3GNet
- **Accuracy**: Good generalization
- **Parameters**: ~200K
- **Best for**: Fast screening, structure relaxation

### SevenNet
- **Accuracy**: Best for phonons
- **Best for**: Phonon calculations, vibrational properties

---

## Installation

```bash
# MACE (requires PyTorch with CUDA)
pip install mace-torch

# MatGL (M3GNet, CHGNet)
pip install matgl

# ASE (required for all)
pip install ase

# Phonopy (for phonon calculations)
pip install phonopy

# PyMatGen (structure manipulation)
pip install pymatgen
```

---

## Basic Usage with ASE

### Loading Models

```python
from ase import Atoms
from ase.build import bulk

# MACE
from mace.calculators import mace_mp
calc_mace = mace_mp(model="medium", device="cuda")  # or "cpu"

# CHGNet
from chgnet.model import CHGNetCalculator
calc_chgnet = CHGNetCalculator()

# M3GNet
import matgl
from matgl.ext.ase import M3GNetCalculator
pot = matgl.load_model("M3GNet-MP-2021.2.8-PES")
calc_m3gnet = M3GNetCalculator(pot)
```

### Single-Point Calculation

```python
from ase.build import bulk

# Create structure
atoms = bulk('Cu', 'fcc', a=3.6)

# Attach calculator
atoms.calc = calc_mace

# Get energy and forces
energy = atoms.get_potential_energy()
forces = atoms.get_forces()
stress = atoms.get_stress()

print(f"Energy: {energy:.4f} eV")
print(f"Forces shape: {forces.shape}")
```

### Structure Relaxation

```python
from ase.optimize import BFGS

atoms = bulk('Si', 'diamond', a=5.43)
atoms.calc = calc_mace

# Relax structure
opt = BFGS(atoms, trajectory='relax.traj')
opt.run(fmax=0.01)  # eV/Å

print(f"Relaxed energy: {atoms.get_potential_energy():.4f} eV")
print(f"Relaxed cell:\n{atoms.cell}")
```

### Molecular Dynamics

```python
from ase.md.langevin import Langevin
from ase.md.velocitydistribution import MaxwellBoltzmannDistribution
from ase import units

# Create supercell
atoms = bulk('Cu', 'fcc', a=3.6) * (4, 4, 4)  # 256 atoms
atoms.calc = calc_mace

# Initialize velocities
MaxwellBoltzmannDistribution(atoms, temperature_K=300)

# Setup MD
dyn = Langevin(
    atoms,
    timestep=1.0 * units.fs,
    temperature_K=300,
    friction=0.01
)

# Run MD
def print_energy(a=atoms):
    print(f"E = {a.get_potential_energy():.4f} eV")

dyn.attach(print_energy, interval=100)
dyn.run(1000)  # 1000 steps = 1 ps
```

---

## Common Calculations

### Lattice Constant Optimization

```python
from ase.build import bulk
from ase.eos import EquationOfState
import numpy as np

atoms = bulk('Cu', 'fcc', a=3.6)
atoms.calc = calc_mace

# Calculate E(V) curve
volumes = []
energies = []
for scale in np.linspace(0.95, 1.05, 7):
    atoms_scaled = atoms.copy()
    atoms_scaled.set_cell(atoms.cell * scale, scale_atoms=True)
    atoms_scaled.calc = calc_mace
    volumes.append(atoms_scaled.get_volume())
    energies.append(atoms_scaled.get_potential_energy())

# Fit equation of state
eos = EquationOfState(volumes, energies)
v0, e0, B = eos.fit()
a_opt = (4 * v0) ** (1/3)  # For FCC
print(f"Optimal lattice constant: {a_opt:.4f} Å")
print(f"Bulk modulus: {B / units.GPa:.1f} GPa")
```

### Elastic Constants

```python
from ase.build import bulk

atoms = bulk('Cu', 'fcc', a=3.6)
atoms.calc = calc_mace

# Use stress-strain method
from ase.constraints import StrainFilter
from ase.optimize import BFGS

# First relax
sf = StrainFilter(atoms)
opt = BFGS(sf)
opt.run(fmax=0.001)

# Then calculate elastic constants
# (See ASE documentation for full elastic tensor calculation)
```

### Formation Energy

```python
def formation_energy(compound_atoms, element_energies):
    """
    Calculate formation energy.

    compound_atoms: ASE Atoms object for compound
    element_energies: dict like {'Li': -1.9, 'O': -4.9}
    """
    compound_atoms.calc = calc_mace
    E_compound = compound_atoms.get_potential_energy()

    # Count atoms
    symbols = compound_atoms.get_chemical_symbols()
    from collections import Counter
    counts = Counter(symbols)

    # Reference energy
    E_ref = sum(element_energies[el] * n for el, n in counts.items())

    # Formation energy per atom
    E_form = (E_compound - E_ref) / len(compound_atoms)
    return E_form
```

### Diffusion Coefficient from MD

```python
import numpy as np
from ase.md.langevin import Langevin
from ase import units

def calculate_diffusion(atoms, calc, T, n_steps=10000, dt=1.0):
    """Calculate diffusion coefficient from MSD."""
    atoms = atoms.copy()
    atoms.calc = calc

    # Initialize
    MaxwellBoltzmannDistribution(atoms, temperature_K=T)

    # Setup MD
    dyn = Langevin(atoms, timestep=dt*units.fs, temperature_K=T, friction=0.01)

    # Track positions
    positions = [atoms.get_positions().copy()]

    for i in range(n_steps):
        dyn.run(1)
        if i % 10 == 0:
            positions.append(atoms.get_positions().copy())

    positions = np.array(positions)

    # Calculate MSD
    r0 = positions[0]
    msd = np.mean(np.sum((positions - r0)**2, axis=2), axis=1)

    # Time array
    times = np.arange(len(msd)) * 10 * dt  # fs

    # Fit linear region (skip initial ballistic)
    from scipy.stats import linregress
    start = len(msd) // 4
    slope, _, _, _, _ = linregress(times[start:], msd[start:])

    # D = MSD / (6 * t) for 3D
    D = slope / 6  # Å²/fs
    D_cm2s = D * 1e-4  # Convert to cm²/s

    return D_cm2s
```

---

## Phonon Calculations

### With Phonopy

```python
from phonopy import Phonopy
from phonopy.structure.atoms import PhonopyAtoms
from ase.build import bulk
import numpy as np

# Create structure
atoms = bulk('Si', 'diamond', a=5.43)

# Convert to phonopy format
phonopy_atoms = PhonopyAtoms(
    symbols=atoms.get_chemical_symbols(),
    cell=atoms.cell,
    scaled_positions=atoms.get_scaled_positions()
)

# Create phonopy object with supercell
phonon = Phonopy(phonopy_atoms, supercell_matrix=[[2,0,0],[0,2,0],[0,0,2]])

# Generate displacements
phonon.generate_displacements(distance=0.01)
supercells = phonon.get_supercells_with_displacements()

# Calculate forces for each displacement
forces = []
for sc in supercells:
    # Convert to ASE
    atoms_sc = Atoms(
        symbols=sc.symbols,
        positions=sc.positions,
        cell=sc.cell,
        pbc=True
    )
    atoms_sc.calc = calc_mace
    f = atoms_sc.get_forces()
    forces.append(f)

# Set forces and calculate phonons
phonon.forces = forces
phonon.produce_force_constants()

# Calculate dispersion
path = [[[0,0,0], [0.5,0,0.5], [0.5,0.25,0.75], [0,0,0], [0.5,0.5,0.5]]]
labels = ['$\\Gamma$', 'X', 'K', '$\\Gamma$', 'L']
phonon.run_band_structure(path, labels=labels)

# Plot
phonon.plot_band_structure().savefig('phonon_dispersion.png')
```

---

## Known Limitations

### Systematic Errors

| Property | Typical Error | Notes |
|----------|---------------|-------|
| Formation energy | ~50 meV/atom | Systematic shift possible |
| Lattice constant | ~1% | Usually reliable |
| Bulk modulus | ~10% | Varies by system |
| **Phonon frequencies** | **~15% low** | Known systematic softening |
| Surface energies | ~100 meV/Å² | Less reliable than bulk |
| Alloy mixing | **Poor** | Not well-captured by UIPs |

### When MLIPs Fail

1. **Chemistry far from training data**: Exotic elements, unusual oxidation states
2. **Surfaces and interfaces**: Higher errors than bulk
3. **Alloy thermodynamics**: Binary mixing energies often wrong
4. **Reaction barriers**: May not capture transition states
5. **Long-range interactions**: Charge transfer, van der Waals

### Validation Strategy

Always validate MLIP results against:
1. DFT (at least for a few key structures)
2. Experimental data
3. Materials Project database

```python
# Example: Compare to Materials Project
from mp_api.client import MPRester

with MPRester() as mpr:
    docs = mpr.summary.search(formula="Cu")
    mp_data = docs[0]

print(f"MP formation energy: {mp_data.formation_energy_per_atom:.4f} eV/atom")
print(f"MLIP formation energy: {my_mlip_result:.4f} eV/atom")
print(f"Difference: {abs(mp_data.formation_energy_per_atom - my_mlip_result):.4f} eV/atom")
```

---

## GPU Acceleration

### MACE with CUDA

```python
# Explicitly use GPU
calc = mace_mp(model="medium", device="cuda")

# Check GPU memory
import torch
print(f"GPU memory: {torch.cuda.memory_allocated()/1e9:.2f} GB")
```

### Performance Tips

1. **Batch calculations**: Process multiple structures together
2. **Use appropriate model size**: "small" for screening, "large" for accuracy
3. **GPU memory**: Large systems may need memory management
4. **Parallel MD**: Consider LAMMPS for large-scale GPU MD
5. **High-throughput**: For 10+ structures, use `torch-sim` skill (100x faster)

---

## Integration with LAMMPS

For large-scale MD, MACE can be used with LAMMPS:

```bash
# Convert MACE model for LAMMPS
mace_create_lammps_model --model MACE-MP-0 --output mace.lammps
```

```lammps
# LAMMPS input with MACE
units metal
atom_style atomic

read_data structure.data

pair_style mace
pair_coeff * * mace.lammps Cu

# Run MD
velocity all create 300 12345
fix 1 all nvt temp 300 300 0.1
run 10000
```

---

## Workflow Examples

### High-Throughput Screening

```python
def screen_structures(structures, calc, property_func):
    """Screen many structures for a property."""
    results = []
    for name, atoms in structures.items():
        atoms.calc = calc
        try:
            prop = property_func(atoms)
            results.append({'name': name, 'property': prop, 'status': 'success'})
        except Exception as e:
            results.append({'name': name, 'property': None, 'status': str(e)})
    return results

# Example: Screen for stability
def stability_metric(atoms):
    return atoms.get_potential_energy() / len(atoms)

results = screen_structures(my_structures, calc_mace, stability_metric)
```

### Fine-Tuning (Advanced)

```python
# Fine-tuning requires MACE training code
# See: https://github.com/ACEsuit/mace

# Basic workflow:
# 1. Prepare training data (ASE database or xyz files)
# 2. Load pretrained model
# 3. Fine-tune with small learning rate
# 4. Validate on held-out set

# Example command (simplified):
# mace_run_train \
#   --model="MACE" \
#   --foundation_model="MACE-MP-0" \
#   --train_file="my_data.xyz" \
#   --valid_fraction=0.1 \
#   --lr=0.0001 \
#   --max_num_epochs=100
```

---

## Quick Reference

### Model Selection Guide

| Use Case | Recommended Model |
|----------|-------------------|
| General property prediction | MACE-MP-0 |
| Battery materials | CHGNet |
| Fast screening | M3GNet |
| Phonon calculations | SevenNet or MACE |
| Large-scale MD | M3GNet (fastest) |

### Typical Workflow

1. **Structure preparation**: Build or fetch from Materials Project
2. **Model selection**: Choose based on chemistry and property
3. **Validation**: Compare small test to DFT/experiment
4. **Production**: Run full calculation
5. **Analysis**: Extract properties, compare to literature
6. **Documentation**: Report model used, limitations

---

## Resources

- **MACE**: https://github.com/ACEsuit/mace
- **MatGL**: https://github.com/materialsvirtuallab/matgl
- **Matbench Discovery**: https://matbench-discovery.materialsproject.org/
- **ASE**: https://wiki.fysik.dtu.dk/ase/
- **Phonopy**: https://phonopy.github.io/phonopy/
