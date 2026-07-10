#!/bin/bash
# MACE/ML Potential Setup Script for VAST AI
# Use with pytorch/pytorch:2.1.0-cuda12.1-cudnn8-devel image

set -e

echo "=== Setting up ML Potentials Environment ==="

# Update pip
pip install --upgrade pip

# Install ML potential packages
pip install mace-torch
pip install chgnet
pip install matgl

# Install ASE and other utilities
pip install ase
pip install pymatgen
pip install numpy scipy matplotlib

# Verify installation
python -c "
import torch
print(f'PyTorch: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'CUDA device: {torch.cuda.get_device_name(0)}')

from mace.calculators import mace_mp
print('MACE: OK')

from chgnet.model import CHGNet
print('CHGNet: OK')

import matgl
print('MatGL (M3GNet): OK')
"

echo "=== Setup Complete ==="
