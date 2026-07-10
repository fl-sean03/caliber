#!/bin/bash
# Quick GPU Test Script for VAST AI
# Verifies GPU is accessible and working

set -e

echo "=== VAST AI Instance Quick Test ==="
echo "Hostname: $(hostname)"
echo "Date: $(date)"
echo ""

echo "=== GPU Information ==="
nvidia-smi

echo ""
echo "=== CUDA Version ==="
nvcc --version 2>/dev/null || echo "nvcc not in PATH (normal for runtime images)"

echo ""
echo "=== System Info ==="
echo "CPU: $(nproc) cores"
echo "RAM: $(free -h | grep Mem | awk '{print $2}')"
echo "Disk: $(df -h / | tail -1 | awk '{print $4}') available"

echo ""
echo "=== Test Complete ==="
