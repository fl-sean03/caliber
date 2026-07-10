#!/bin/bash
# Quantum ESPRESSO execution wrapper script
# Usage: ./run_qe.sh input.in output.out [gpu|cpu] [nprocs]

set -e

# NOTE (2026-07-04): QE 7.5 local builds, rebuilt from source 2026-07-03
# CPU build is MPI-capable;
# GPU build is SERIAL-ONLY by design (no MPI, runtime libs resolve via RPATH —
# no environment sourcing needed). Env vars $QE_CPU/$QE_GPU override defaults.
QE_CPU="${QE_CPU:?set QE_CPU to your QE CPU bin dir}"
QE_GPU="${QE_GPU:?set QE_GPU to your QE GPU bin dir}"

if [ $# -lt 2 ]; then
    echo "Usage: $0 <input_file> <output_file> [gpu|cpu] [nprocs]"
    echo "  input_file: QE input file"
    echo "  output_file: Output file path"
    echo "  gpu|cpu: Execution mode (default: cpu)"
    echo "  nprocs: Number of MPI processes (default: 1)"
    exit 1
fi

INPUT_FILE="$1"
OUTPUT_FILE="$2"
MODE="${3:-cpu}"
NPROCS="${4:-1}"

if [ ! -f "$INPUT_FILE" ]; then
    echo "Error: Input file '$INPUT_FILE' not found"
    exit 1
fi

echo "=== Quantum ESPRESSO Execution ==="
echo "Input: $INPUT_FILE"
echo "Output: $OUTPUT_FILE"
echo "Mode: $MODE"
echo "Processes: $NPROCS"
echo "==================================="

if [ "$MODE" = "gpu" ]; then
    QE_BIN="$QE_GPU"
    if [ "$NPROCS" -gt 1 ]; then
        echo "Error: GPU build is serial-only by design (no MPI). Use nprocs=1 or cpu mode."
        exit 1
    fi
else
    QE_BIN="$QE_CPU"
fi

if [ "$NPROCS" -gt 1 ]; then
    echo "Running with MPI ($NPROCS processes)..."
    mpirun -np "$NPROCS" "$QE_BIN/pw.x" < "$INPUT_FILE" > "$OUTPUT_FILE"
else
    echo "Running serial..."
    "$QE_BIN/pw.x" < "$INPUT_FILE" > "$OUTPUT_FILE"
fi

echo "=== Execution Complete ==="
echo "Output written to: $OUTPUT_FILE"
