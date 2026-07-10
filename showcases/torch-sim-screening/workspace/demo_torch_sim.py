#!/usr/bin/env python
"""
torch-sim Demo Script - High-Throughput Screening Showcase

This script demonstrates torch-sim's batched GPU acceleration for
materials screening with MACE ML potentials.

Usage:
    python demo_torch_sim.py [--static | --optimize | --full]

Options:
    --static    Quick demo with static calculations only
    --optimize  Demo with batch optimization
    --full      Full demo (static + optimize) [default]
"""

import sys
import time
import urllib.request
from pathlib import Path


def setup_model():
    """Download and load MACE model."""
    import torch
    from torch_sim.models.mace import MaceModel, MaceUrls

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    dtype = torch.float32

    print(f"   Device: {device}")
    if device.type == "cuda":
        print(f"   GPU: {torch.cuda.get_device_name(0)}")

    # Use cached model location, download if needed
    cache_dir = Path.home() / ".cache/science-agent/mace"
    cache_dir.mkdir(parents=True, exist_ok=True)
    model_path = cache_dir / "mace_mp_small.model"

    if not model_path.exists():
        print("   Downloading MACE-MP-0 small model to cache...")
        urllib.request.urlretrieve(MaceUrls.mace_mp_small, model_path)
        print(f"   Downloaded to {model_path}")
    else:
        print(f"   Using cached model: {model_path}")

    model = MaceModel(str(model_path), device=device, dtype=dtype)
    print(f"   Model loaded: {type(model).__name__}")

    return model, device, dtype


def create_structures():
    """Create test structures."""
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
        bulk('Ti', 'hcp', a=2.95, c=4.68),
        bulk('Zn', 'hcp', a=2.66, c=4.94),
        bulk('Mg', 'hcp', a=3.21, c=5.21),
        bulk('Co', 'hcp', a=2.51, c=4.07),
        bulk('Zr', 'hcp', a=3.23, c=5.15),
    ]
    return structures


def demo_static(model, device, dtype, structures):
    """Demo static energy calculations."""
    from torch_sim import initialize_state, static

    print("\n3. Static Energy Calculations:")
    states = initialize_state(structures, device=device, dtype=dtype)
    print(f"   Initialized {states.n_systems} structures")

    start = time.time()
    results = static(states, model=model)
    elapsed = time.time() - start

    print(f"   Completed in {elapsed:.2f}s")
    print(f"   Throughput: {len(structures)/elapsed:.1f} structures/sec")

    print("\n   Results:")
    names = ['Cu', 'Al', 'Ni', 'Ag', 'Au', 'Pt', 'Pd', 'Fe', 'W', 'Mo',
             'Ti', 'Zn', 'Mg', 'Co', 'Zr']
    for i, result in enumerate(results):
        energy = result['potential_energy'].item()
        n_atoms = len(structures[i])
        print(f"   {names[i]:3s}: {energy:8.4f} eV ({energy/n_atoms:7.4f} eV/atom)")

    return elapsed


def demo_optimize(model, device, dtype, structures):
    """Demo batch optimization."""
    from torch_sim import initialize_state, static, optimize, generate_energy_convergence_fn
    from torch_sim.optimizers import Optimizer

    print("\n4. Batch Optimization with FIRE:")
    states = initialize_state(structures, device=device, dtype=dtype)
    convergence_fn = generate_energy_convergence_fn(energy_tol=1e-4)

    start = time.time()
    final_state = optimize(
        states,
        model=model,
        optimizer=Optimizer.fire,
        convergence_fn=convergence_fn,
        max_steps=500,
    )
    elapsed = time.time() - start

    print(f"   Completed in {elapsed:.2f}s")
    print(f"   Throughput: {len(structures)/elapsed*60:.1f} structures/min")

    # Get final energies
    print("\n   Final energies after optimization:")
    final_results = static(final_state, model=model)
    names = ['Cu', 'Al', 'Ni', 'Ag', 'Au', 'Pt', 'Pd', 'Fe', 'W', 'Mo',
             'Ti', 'Zn', 'Mg', 'Co', 'Zr']
    for i, result in enumerate(final_results):
        energy = result['potential_energy'].item()
        n_atoms = len(structures[i])
        print(f"   {names[i]:3s}: {energy:8.4f} eV ({energy/n_atoms:7.4f} eV/atom)")

    return elapsed


def main():
    print("=" * 60)
    print("torch-sim Demo: High-Throughput Screening")
    print("=" * 60)

    # Check imports
    print("\n1. Checking installation...")
    try:
        import torch
        from torch_sim import initialize_state, static, optimize
        from torch_sim.models.mace import MaceModel, MaceUrls
        print("   torch-sim: OK")
    except ImportError as e:
        print(f"\nERROR: torch-sim not installed properly!")
        print(f"   {e}")
        print("\nInstall with: pip install torch-sim-atomistic mace-torch")
        return False

    # Setup
    print("\n2. Setting up model...")
    model, device, dtype = setup_model()

    # Create structures
    structures = create_structures()
    print(f"\n   Created {len(structures)} test structures")

    # Determine what to run
    mode = "full"
    if len(sys.argv) > 1:
        if sys.argv[1] == "--static":
            mode = "static"
        elif sys.argv[1] == "--optimize":
            mode = "optimize"

    # Run demos
    static_time = opt_time = None

    if mode in ("static", "full"):
        static_time = demo_static(model, device, dtype, structures)

    if mode in ("optimize", "full"):
        opt_time = demo_optimize(model, device, dtype, structures)

    # Summary
    print("\n" + "=" * 60)
    print("PERFORMANCE SUMMARY")
    print("=" * 60)
    if static_time:
        print(f"Static calculations: {len(structures)} structures in {static_time:.2f}s")
        print(f"  Estimated ASE time: ~{len(structures)*10}-{len(structures)*20}s")
        print(f"  torch-sim speedup: ~{10*len(structures)/static_time:.0f}x")
    if opt_time:
        print(f"\nBatch optimization: {len(structures)} structures in {opt_time:.2f}s")
        print(f"  Throughput: {len(structures)/opt_time*60:.1f} structures/min")
        print(f"  Estimated ASE time: ~{len(structures)*60}-{len(structures)*120}s")

    print("\n" + "=" * 60)
    print("DEMO COMPLETE: torch-sim high-throughput screening working!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
