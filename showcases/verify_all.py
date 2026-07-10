#!/usr/bin/env python
"""
Verify all showcases are properly installed and configured.

Usage:
    python verify_all.py

This script checks:
1. ggen - structure generation
2. torch-sim - high-throughput screening
3. theorizer - literature-driven theory synthesis (requires conda env)
"""

import sys
import subprocess
from pathlib import Path


def check_ggen():
    """Check ggen installation."""
    try:
        from ggen import GGen
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        return True, f"OK (device: {device})"
    except ImportError as e:
        return False, f"Not installed: {e}"
    except Exception as e:
        return False, f"Error: {e}"


def check_torch_sim():
    """Check torch-sim installation."""
    try:
        import torch
        from torch_sim import initialize_state, static, optimize
        from torch_sim.models.mace import MaceModel

        device = "cuda" if torch.cuda.is_available() else "cpu"
        gpu_name = torch.cuda.get_device_name(0) if device == "cuda" else "N/A"

        # Check for cached model
        cache_path = Path.home() / ".cache/science-agent/mace/mace_mp_small.model"
        model_status = "cached" if cache_path.exists() else "will download on first use"

        return True, f"OK (device: {device}, GPU: {gpu_name}, model: {model_status})"
    except ImportError as e:
        return False, f"Not installed: {e}"
    except Exception as e:
        return False, f"Error: {e}"


def check_theorizer():
    """Check theorizer installation (requires 'theorizer' conda env)."""
    theorizer_root = Path.home() / "work/agents/science-agent/asta-theorizer"

    if not theorizer_root.exists():
        return False, "asta-theorizer not cloned"

    # Check for API keys
    api_keys_file = theorizer_root / "api_keys.donotcommit.json"
    s2_key_file = theorizer_root / "s2_key.donotcommit.txt"

    api_status = "configured" if api_keys_file.exists() else "missing"
    s2_status = "configured" if s2_key_file.exists() else "missing"

    # Try importing in the theorizer environment
    try:
        result = subprocess.run(
            [
                "bash", "-c",
                "source ~/miniconda3/etc/profile.d/conda.sh && "
                "conda activate theorizer 2>/dev/null && "
                "cd ~/work/agents/science-agent/asta-theorizer && "
                "python -c 'import sys; sys.path.insert(0, \"src\"); from Theorizer import Theorizer; print(\"OK\")'"
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        if "OK" in result.stdout:
            return True, f"OK (api_keys: {api_status}, s2_key: {s2_status})"
        else:
            return False, f"Import failed: {result.stderr}"
    except subprocess.TimeoutExpired:
        return False, "Timeout checking theorizer env"
    except Exception as e:
        return False, f"Error: {e}"


def main():
    print("=" * 60)
    print("Showcase Verification")
    print("=" * 60)

    checks = [
        ("ggen", check_ggen),
        ("torch-sim", check_torch_sim),
        ("theorizer", check_theorizer),
    ]

    results = []
    for name, check_fn in checks:
        print(f"\nChecking {name}...", end=" ")
        success, message = check_fn()
        status = "PASS" if success else "FAIL"
        print(f"{status}")
        print(f"  {message}")
        results.append((name, success, message))

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, success, _ in results if success)
    total = len(results)

    for name, success, _ in results:
        status = "[OK]" if success else "[FAIL]"
        print(f"  {status} {name}")

    print(f"\n{passed}/{total} showcases ready")

    if passed == total:
        print("\nAll showcases verified!")
        return 0
    else:
        print("\nSome showcases need attention.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
