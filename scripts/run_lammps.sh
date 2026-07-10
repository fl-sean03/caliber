#!/bin/bash
# LAMMPS execution wrapper script
# Usage: ./run_lammps.sh input.lmp [gpu|cpu] [additional args...]

set -e

# Default = the working bare-metal build (22Jul2025-U4, smoke-verified 2026-07-02).
# The old gpu-tests binary does NOT run (libmpi.so.40 missing; rebase A-04 refuted)
# and was archived 2026-07-03 to ~/work/archive/gpu-tests-wsl/1-GPUTests (M-3).
LMP="${LMP:?set LMP to your lammps binary}"

if [ $# -lt 1 ]; then
    echo "Usage: $0 <input_file> [gpu|cpu] [additional_args...]"
    echo "  input_file: LAMMPS input script"
    echo "  gpu|cpu: Execution mode (default: cpu)"
    exit 1
fi

INPUT_FILE="$1"
MODE="${2:-cpu}"
shift 2 2>/dev/null || shift 1

if [ ! -f "$INPUT_FILE" ]; then
    echo "Error: Input file '$INPUT_FILE' not found"
    exit 1
fi

echo "=== LAMMPS Execution ==="
echo "Input: $INPUT_FILE"
echo "Mode: $MODE"
echo "========================"

if [ "$MODE" = "gpu" ]; then
    echo "Running with GPU acceleration..."
    $LMP -sf gpu -pk gpu 1 neigh yes -in "$INPUT_FILE" "$@"
else
    echo "Running on CPU..."
    $LMP -in "$INPUT_FILE" "$@"
fi

echo "=== Execution Complete ==="
