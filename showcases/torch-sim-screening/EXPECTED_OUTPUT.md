# torch-sim Screening Showcase - Expected Output

## Success Criteria

This showcase is successful when:

1. [x] Agent recognizes this is a high-throughput screening task
2. [x] Agent identifies torch-sim as the right tool for scale
3. [x] Agent uses torch-sim's batched operations correctly
4. [x] Agent demonstrates performance advantage over ASE
5. [x] Agent produces ranked results with analysis
6. [x] Agent identifies potential outliers/issues

## What the Agent Should Do

### 1. Understand the Task
- Recognize this requires screening many structures
- Know that torch-sim is optimal for batch operations
- Understand MACE model selection

### 2. Setup (VALIDATED API)

```python
import torch
import urllib.request
from pathlib import Path
from torch_sim import initialize_state, static, optimize, generate_energy_convergence_fn
from torch_sim.models.mace import MaceModel, MaceUrls
from torch_sim.optimizers import Optimizer

# Device setup
device = torch.device("cuda")
dtype = torch.float32

# Download model (required - can't pass URL directly)
model_path = Path("./mace_mp_small.model")
if not model_path.exists():
    urllib.request.urlretrieve(MaceUrls.mace_mp_small, model_path)

# Load model
model = MaceModel(str(model_path), device=device, dtype=dtype)
```

### 3. Create/Get Structures

```python
from ase.build import bulk

structures = [
    bulk('Cu', 'fcc', a=3.6),
    bulk('Al', 'fcc', a=4.05),
    bulk('Ni', 'fcc', a=3.52),
    bulk('Ag', 'fcc', a=4.09),
    bulk('Au', 'fcc', a=4.08),
    bulk('Pt', 'fcc', a=3.92),
    bulk('Pd', 'fcc', a=3.89),
    bulk('Fe', 'bcc', a=2.87),
    bulk('W', 'bcc', a=3.16),
    bulk('Mo', 'bcc', a=3.15),
    # ... more structures
]
```

### 4. Static Calculations (VALIDATED API)

```python
# Initialize batched state
states = initialize_state(structures, device=device, dtype=dtype)

# Run static calculations
results = static(states, model=model)

# Access energies (key is 'potential_energy', NOT 'energy')
for i, result in enumerate(results):
    energy = result['potential_energy'].item()
    print(f"Structure {i}: {energy:.4f} eV")
```

### 5. Batch Optimization (VALIDATED API)

```python
# Re-initialize state
states = initialize_state(structures, device=device, dtype=dtype)

# Create convergence function (NOT fmax parameter!)
convergence_fn = generate_energy_convergence_fn(energy_tol=1e-4)

# Run optimization (returns single state, NOT tuple)
final_state = optimize(
    states,
    model=model,
    optimizer=Optimizer.fire,  # Use enum, not string
    convergence_fn=convergence_fn,
    max_steps=500,
)

# Get final energies
final_results = static(final_state, model=model)
```

### 6. Report Performance

```python
import time

start = time.time()
# ... optimization code ...
elapsed = time.time() - start

print(f"Optimized {len(structures)} structures in {elapsed:.2f}s")
print(f"Throughput: {len(structures)/elapsed*60:.1f} structures/min")
```

## Example Output Markers

Look for:
- "Using torch-sim for batched optimization"
- `from torch_sim import initialize_state, static, optimize`
- `from torch_sim.models.mace import MaceModel, MaceUrls`
- `Optimizer.fire` (enum, not string)
- `generate_energy_convergence_fn()` (not `fmax` parameter)
- Performance metrics (structures/second, total time)
- Comparison statement to ASE ("50x faster", etc.)
- Ranked results table

## IMPORTANT: Correct API vs Wrong API

| Aspect | WRONG (Old Docs) | CORRECT (Validated) |
|--------|------------------|---------------------|
| Import | `MACEModel` | `MaceModel` |
| Load model | `MaceModel(url)` | Download file first, then `MaceModel(path)` |
| Create state | `SimState.from_ase()` | `initialize_state()` |
| Energy key | `result['energy']` | `result['potential_energy']` |
| Optimize conv | `fmax=0.05` | `convergence_fn=generate_energy_convergence_fn()` |
| Optimize return | `state, traj = optimize()` | `state = optimize()` |

## Performance Expectations (RTX 5080)

| Metric | torch-sim (GPU) | ASE Sequential |
|--------|-----------------|----------------|
| 10 structures static | ~1-2s | ~100s |
| 10 structures optimize | ~1s | ~100-200s |
| Throughput | >600 struct/min | ~0.5 struct/min |

The showcase should demonstrate this difference.

## If torch-sim Is Not Installed

The agent should:
- Note that torch-sim is required
- Explain what performance advantage it would provide
- Optionally fall back to ASE with note about slower speed
- Suggest installation: `pip install torch-sim-atomistic mace-torch`

## What This Showcases

- Agent knows when scale requires specialized tools
- Agent can use torch-sim for high-throughput work
- Agent understands performance trade-offs
- torch-sim enables workflows impossible with ASE alone

## Not Required

- Exact performance numbers (hardware dependent)
- Specific structure sources
- Particular MACE model version
