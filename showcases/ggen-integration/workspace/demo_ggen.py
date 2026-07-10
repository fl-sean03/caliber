#!/usr/bin/env python
"""
ggen Demo Script - Structure Generation Showcase

This script demonstrates ggen's crystal structure generation capability.
Run this to verify ggen integration is working.

Usage:
    python demo_ggen.py [--simple | --explore]

Options:
    --simple   Quick demo with NaCl (1-2 min)
    --explore  Full Li-S exploration (5-10 min)
"""

import sys
import time


def demo_simple():
    """Quick demo: Generate NaCl structures."""
    print("=" * 60)
    print("ggen Demo: Simple Structure Generation")
    print("=" * 60)

    try:
        from ggen import GGen
    except ImportError:
        print("\nERROR: ggen not installed!")
        print("Install with: pip install git+https://github.com/ourofoundation/ggen.git")
        print("NOTE: Do NOT use 'pip install ggen' - that's a different package!")
        return False

    print("\n1. Initializing ggen...")
    ggen = GGen()

    print("\n2. Generating NaCl structures (5 trials)...")
    start = time.time()

    result = ggen.generate_crystal(
        formula="NaCl",
        num_trials=5,
        optimize_geometry=True
    )

    elapsed = time.time() - start

    print(f"\n3. Results (completed in {elapsed:.1f}s):")

    # result is a dict with structure info
    print(f"   Formula: {result['formula']}")
    print(f"   Final space group: {result['final_space_group_symbol']} (#{result['final_space_group']})")
    print(f"   Best energy: {result['best_crystal_energy']:.4f} eV")
    print(f"   Optimization steps: {result['optimization_steps']}")
    print(f"   Final fmax: {result['final_fmax']:.6f} eV/A")

    # Show structure info
    structure = result['structure']
    print(f"\n   Structure:")
    print(f"   - Formula: {structure.composition.reduced_formula}")
    print(f"   - Volume: {structure.volume:.2f} A^3")
    print(f"   - Lattice: a={structure.lattice.a:.3f}, b={structure.lattice.b:.3f}, c={structure.lattice.c:.3f}")

    # Show all trials
    if 'all_relaxed_trials' in result:
        print(f"\n   All trials ({len(result['all_relaxed_trials'])} structures):")
        for i, trial in enumerate(result['all_relaxed_trials']):
            print(f"   - Trial {i+1}: {trial['space_group_symbol']} (#{trial['space_group_number']}), "
                  f"E={trial['energy_per_atom']:.4f} eV/atom")

    print("\n" + "=" * 60)
    print("DEMO COMPLETE: ggen simple generation working!")
    print("=" * 60)
    return True


def demo_explore():
    """Full demo: Explore Li-S chemical space."""
    print("=" * 60)
    print("ggen Demo: Chemical Space Exploration")
    print("=" * 60)

    try:
        from ggen import ChemistryExplorer
    except ImportError:
        print("\nERROR: ggen not installed!")
        print("Install with: pip install git+https://github.com/ourofoundation/ggen.git")
        print("NOTE: Do NOT use 'pip install ggen' - that's a different package!")
        return False

    print("\n1. Initializing ChemistryExplorer...")
    explorer = ChemistryExplorer(output_dir="./ggen_demo_output")

    print("\n2. Exploring Li-S system (max_atoms=12, num_trials=5)...")
    print("   This may take 5-10 minutes...")
    start = time.time()

    result = explorer.explore(
        chemical_system="Li-S",
        max_atoms=12,
        num_trials=5
    )

    elapsed = time.time() - start

    print(f"\n3. Results (completed in {elapsed:.1f}s):")

    # Check available attributes
    print(f"   Result type: {type(result)}")
    if hasattr(result, '__dict__'):
        for key, val in result.__dict__.items():
            if not key.startswith('_'):
                if isinstance(val, (int, float, str)):
                    print(f"   {key}: {val}")
                elif isinstance(val, list):
                    print(f"   {key}: {len(val)} items")

    print("\n" + "=" * 60)
    print("DEMO COMPLETE: ggen exploration working!")
    print("=" * 60)
    return True


def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == "--explore":
            return demo_explore()
        elif sys.argv[1] == "--simple":
            return demo_simple()

    # Default to simple demo
    print("Running simple demo (use --explore for full exploration)")
    print()
    return demo_simple()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
