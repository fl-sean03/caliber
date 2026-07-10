---
name: torch-sim
description: High-throughput batch atomistic simulation with ML potentials on GPU using torch-sim. Use when screening many structures (10+), running batch relaxations/MD where per-structure ASE loops are too slow, or when GPU-parallel MLIP throughput is the bottleneck. For single-system MLIP work, see mlip-simulation.
---

# torch-sim Skill

High-throughput atomistic simulation with ML potentials using torch-sim.

**Validated: 2026-01-24** - API tested and working.

## When to Use This Skill

Use torch-sim when:
- Screening many structures (10+)
- Need batch GPU acceleration
- Performance is critical
- Using ML potentials (MACE, CHGNet, ORB, etc.)

Use mlip-simulation (ASE-based) when:
- Working with 1-5 structures
- Simplicity matters more than speed
- torch-sim is not available

**Rule of thumb**: For 10+ structures, prefer torch-sim. For quick single-structure tests, ASE is simpler.

## What torch-sim Provides

- **50-100x faster** than ASE for batch operations
- **PyTorch-native** - runs on GPU seamlessly
- **Auto-batching** - handles memory management
- **Multiple MLIPs** - MACE, CHGNet, ORB, SevenNet, NequIP, MatterSim

## Installation

```bash
pip install torch-sim-atomistic

# For specific models:
pip install mace-torch        # MACE
pip install chgnet            # CHGNet
pip install orb-models        # ORB
```

### Verification

```bash
python -c "from torch_sim import initialize_state, static; print('torch-sim: OK')"
```

### Model Cache

MACE models cached in: `~/.cache/science-agent/mace/`

The demo script automatically downloads models to cache on first run.

### Showcase Demo

See: `showcases/torch-sim-screening/workspace/demo_torch_sim.py`

## Core Concepts

### Imports

```python
import torch
from torch_sim import initialize_state, static, optimize
from torch_sim import generate_energy_convergence_fn, generate_force_convergence_fn
from torch_sim.models.mace import MaceModel, MaceUrls
from torch_sim.optimizers import Optimizer
```

### Device and Model Setup

**IMPORTANT**: Models require downloading the file first, then passing the local path:

```python
import urllib.request
from pathlib import Path

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
dtype = torch.float32

# Download model (only needed once)
model_path = Path("./mace_mp_small.model")
if not model_path.exists():
    urllib.request.urlretrieve(MaceUrls.mace_mp_small, model_path)

# Load model
model = MaceModel(str(model_path), device=device, dtype=dtype)
```

Available MACE URLs:
- `MaceUrls.mace_mp_small` - Fast, general materials
- `MaceUrls.mace_mpa_medium` - Better accuracy
- `MaceUrls.mace_off_small` - Organic molecules

### Creating States

**IMPORTANT**: Use `initialize_state()`, NOT `SimState.from_ase()`:

```python
from torch_sim import initialize_state
from ase.build import bulk

# Create ASE atoms
structures = [
    bulk('Cu', 'fcc', a=3.6),
    bulk('Al', 'fcc', a=4.05),
    bulk('Ni', 'fcc', a=3.52),
]

# Convert to batched SimState
states = initialize_state(structures, device=device, dtype=dtype)
print(f"Batch size: {states.n_systems}")
```

## High-Level Runners

### Static Energy Calculations

**IMPORTANT**: `static()` returns `list[dict[str, torch.Tensor]]`, not SimState:

```python
from torch_sim import static

results = static(states, model=model)

# Access results
for i, result in enumerate(results):
    energy = result['potential_energy'].item()  # NOT 'energy'
    forces = result['forces']  # Tensor
    stress = result['stress']  # Tensor
    print(f"Structure {i}: {energy:.4f} eV")
```

### Geometry Optimization

**IMPORTANT**:
- Use `Optimizer.fire` enum, not string
- Use convergence functions for criteria
- Returns single state, not tuple

```python
from torch_sim import optimize, generate_energy_convergence_fn
from torch_sim.optimizers import Optimizer

# Create convergence function
convergence_fn = generate_energy_convergence_fn(energy_tol=1e-4)

# Run optimization
final_state = optimize(
    states,
    model=model,
    optimizer=Optimizer.fire,  # or Optimizer.gradient_descent
    convergence_fn=convergence_fn,
    max_steps=500,
)

# Get final energies
final_results = static(final_state, model=model)
```

## Complete Working Example

```python
"""torch-sim batch optimization example"""
import torch
import urllib.request
from pathlib import Path
from ase.build import bulk
from torch_sim import initialize_state, static, optimize, generate_energy_convergence_fn
from torch_sim.models.mace import MaceModel, MaceUrls
from torch_sim.optimizers import Optimizer

# Setup
device = torch.device("cuda")
dtype = torch.float32

# Download and load model
model_path = Path("./mace_mp_small.model")
if not model_path.exists():
    urllib.request.urlretrieve(MaceUrls.mace_mp_small, model_path)
model = MaceModel(str(model_path), device=device, dtype=dtype)

# Create test structures
structures = [
    bulk('Cu', 'fcc', a=3.6),
    bulk('Al', 'fcc', a=4.05),
    bulk('Ni', 'fcc', a=3.52),
    bulk('Fe', 'bcc', a=2.87),
    bulk('W', 'bcc', a=3.16),
]

# Static calculations
states = initialize_state(structures, device=device, dtype=dtype)
results = static(states, model=model)

print("Initial energies:")
for i, result in enumerate(results):
    print(f"  {i}: {result['potential_energy'].item():.4f} eV")

# Optimization
states = initialize_state(structures, device=device, dtype=dtype)
convergence_fn = generate_energy_convergence_fn(energy_tol=1e-4)

final_state = optimize(
    states,
    model=model,
    optimizer=Optimizer.fire,
    convergence_fn=convergence_fn,
    max_steps=500,
)

final_results = static(final_state, model=model)
print("\nOptimized energies:")
for i, result in enumerate(final_results):
    print(f"  {i}: {result['potential_energy'].item():.4f} eV")
```

## Autobatching

For large batches, use autobatchers to manage GPU memory:

```python
from torch_sim.autobatching import InFlightAutoBatcher

autobatcher = InFlightAutoBatcher(memory_fraction=0.8)

final_state = optimize(
    states,
    model=model,
    optimizer=Optimizer.fire,
    autobatcher=autobatcher,
    max_steps=500,
)
```

## Convergence Functions

Two options for convergence criteria:

```python
from torch_sim import generate_energy_convergence_fn, generate_force_convergence_fn

# Energy-based (default) - converge when energy change < tolerance
convergence_fn = generate_energy_convergence_fn(energy_tol=1e-4)

# Force-based - converge when max force < tolerance
# NOTE: Requires cell_forces in state, may not work with all models
convergence_fn = generate_force_convergence_fn(force_tol=0.05)
```

## Converting Results Back

```python
# SimState to ASE Atoms
atoms_list = final_state.to_atoms()

# SimState to Pymatgen Structures
structures = final_state.to_structures()
```

## Performance (Validated on RTX 5080)

| Operation | 10 structures | Notes |
|-----------|---------------|-------|
| Static energy | ~2s | ~48x faster than sequential ASE |
| FIRE optimization | ~1s | >600 structures/min throughput |

## Comparison with ASE

| Aspect | torch-sim | ASE |
|--------|-----------|-----|
| Speed (batch) | 50-100x faster | Baseline |
| GPU support | Native | Limited |
| Batching | Automatic | Manual |
| Memory mgmt | Autobatcher | Manual |
| Simplicity | More setup | Simpler |
| Best for | 10+ structures | 1-5 structures |

## Common Issues

### Model Loading Error
```
FileNotFoundError: ...
```
**Solution**: Download model file first, don't pass URL directly to MaceModel.

### Missing cell_forces
```
ValueError: cell_forces not found in state
```
**Solution**: Use `generate_energy_convergence_fn()` instead of `generate_force_convergence_fn()`.

### Unpack Error
```
ValueError: too many values to unpack
```
**Solution**: `optimize()` returns single state, not tuple.

## References

- [torch-sim Documentation](https://torchsim.github.io/torch-sim/)
- [torch-sim GitHub](https://github.com/TorchSim/torch-sim)
- [MACE Models](https://github.com/ACEsuit/mace)

## See Also

- `mlip-simulation` skill - Simpler ASE-based ML potential usage
- `data-analysis` skill - Analyzing torch-sim outputs
