#!/bin/bash
# LAMMPS GPU Setup Script for VAST AI
# Use with nvidia/cuda:12.2.0-devel-ubuntu22.04 image

set -e

echo "=== Setting up LAMMPS GPU ==="

# Install dependencies
apt-get update
apt-get install -y build-essential cmake wget git libopenmpi-dev openmpi-bin

# Download LAMMPS
cd /root
wget -q https://github.com/lammps/lammps/archive/refs/tags/stable_2Aug2023.tar.gz
tar xzf stable_2Aug2023.tar.gz
cd lammps-stable_2Aug2023

# Build with GPU support
mkdir build && cd build
cmake ../cmake \
    -D PKG_GPU=on \
    -D GPU_API=cuda \
    -D PKG_MOLECULE=on \
    -D PKG_KSPACE=on \
    -D PKG_RIGID=on \
    -D PKG_MANYBODY=on \
    -D BUILD_MPI=on

make -j$(nproc)

# Create symlink
ln -sf /root/lammps-stable_2Aug2023/build/lmp /usr/local/bin/lmp

# Verify
echo "=== Verifying LAMMPS GPU ==="
lmp -h | head -5
nvidia-smi

echo "=== LAMMPS GPU Setup Complete ==="
echo "Run with: lmp -sf gpu -pk gpu 1 -in input.lmp"
