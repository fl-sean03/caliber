---
name: vast-cloud
description: Run jobs on VAST AI cloud GPUs. Use when you need GPU compute immediately without queue times, for short-to-medium jobs (<4 hours), or when HPC is unavailable. Pay-per-hour pricing.
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - WebSearch
  - WebFetch
---

# VAST AI Cloud GPU Access

You have access to VAST AI, an on-demand GPU cloud marketplace. Rent GPUs by the hour, get instant access (no queue), full SSH control.

## Quick Reference

| Item | Value |
|------|-------|
| **CLI** | `vastai` 1.2.0 — in the `science-tools` conda env, symlinked at `~/.local/bin/vastai` (installed 2026-07-04) |
| **API Key** | CLI 1.2.0 resolution order: `VAST_API_KEY` env → `~/.config/vastai/vast_api_key` → `~/.vast_api_key`. The bundled `vast_client.py` reads `~/.config/vastai/api_key`. All four exist and match (2026-07-04). |
| **SSH Key** | Registered (ID: 614140) |
| **Balance** | check `vastai show user` (`show credit` was removed in CLI 1.2.0) |
| **Billing** | Per-hour, stops when you destroy instance |

---

## When to Use VAST AI

### Use VAST When:

| Situation | Why VAST |
|-----------|----------|
| Need GPU now | No queue, instant allocation |
| HPC unreachable | Network/VPN issues |
| Short job (<4h) | Cost-effective for quick runs |
| Testing/debugging | Rapid iteration, cheap |
| Urgent deadline | Time > money |

### Use HPC Instead When:

| Situation | Why HPC |
|-----------|---------|
| Long production runs (>8h) | Free allocation, reliability |
| Massive scale (1000+ cores) | HPC has more resources |
| Budget constrained | HPC is free (with allocation) |
| Queue is short | No cost advantage to VAST |

### Use Local Instead When:

| Situation | Why Local |
|-----------|-----------|
| Small jobs (<30 min) | Setup overhead not worth it |
| No GPU needed | Local CPU is fine |
| Testing inputs | Don't pay for debugging |

---

## Cost Reference

| GPU | Typical $/hr | Good For |
|-----|-------------|----------|
| RTX 3090 | $0.15-0.25 | Light ML, small LAMMPS |
| RTX 4090 | $0.25-0.45 | MACE, CHGNet, medium LAMMPS |
| A100 40GB | $0.80-1.50 | Large models, QE GPU |
| A100 80GB | $1.20-2.00 | Very large models |
| H100 | $2.00-4.00 | Maximum performance |

**Cost Estimation:**
```bash
# 4090 for 2 hours ≈ $0.70
# A100 for 2 hours ≈ $2.00
# Always destroy instances when done!
```

---

## Basic Workflow

### 1. Search for Available GPUs

```bash
# Find RTX 4090s under $0.50/hr, sorted by price
vastai search offers "gpu_name=RTX_4090 rentable=True dph<0.5" -o "dph+"

# Find A100s
vastai search offers "gpu_name=A100 rentable=True" -o "dph+"

# Find any cheap GPU
vastai search offers "gpu_ram>20 rentable=True dph<0.3" -o "dph+"
```

**Key Fields in Output:**
- `ID` - Offer ID (use this to rent)
- `dph` - Dollars per hour
- `gpu_name` - GPU model
- `gpu_ram` - VRAM in GB
- `cpu_ram` - System RAM in GB
- `disk_space` - Available disk in GB

### 2. Create Instance

```bash
# Rent an instance (replace ID with actual offer ID from search)
vastai create instance <offer_id> \
  --image nvidia/cuda:12.2.0-devel-ubuntu22.04 \
  --disk 50 \
  --ssh

# Wait for it to boot (usually 1-3 minutes)
# Check status:
vastai show instances
```

**Recommended Images:**
```
nvidia/cuda:12.2.0-devel-ubuntu22.04  # General GPU work
pytorch/pytorch:2.1.0-cuda12.1-cudnn8-devel  # ML potentials
python:3.11  # CPU-only Python work
```

### 3. Connect and Work

```bash
# Get SSH command
vastai ssh-url <instance_id>
# Output: ssh -p PORT root@HOST

# Connect
ssh -p <port> root@<host>

# Once connected, you have root access:
# - Install software
# - Run jobs
# - Transfer files
```

### 4. Transfer Files

```bash
# Upload to instance
scp -P <port> local_file.txt root@<host>:/root/

# Download from instance
scp -P <port> root@<host>:/root/results.tar.gz ./

# Use rsync for directories
rsync -avz -e "ssh -p <port>" ./project/ root@<host>:/root/project/
```

### 5. DESTROY WHEN DONE (Critical!)

```bash
# Stop billing!
vastai destroy instance <instance_id>

# Verify it's gone
vastai show instances
```

**WARNING:** Instances bill until destroyed. Always destroy when done.

---

## Running Simulations

### LAMMPS on VAST

```bash
# On the instance:

# Install LAMMPS (GPU version)
apt-get update && apt-get install -y build-essential cmake wget git

# Quick LAMMPS GPU install
wget https://github.com/lammps/lammps/archive/stable_2Aug2023.tar.gz
tar xzf stable_2Aug2023.tar.gz
cd lammps-stable_2Aug2023
mkdir build && cd build
cmake ../cmake -D PKG_GPU=on -D GPU_API=cuda
make -j$(nproc)

# Run simulation
./lmp -sf gpu -pk gpu 1 -in input.lmp
```

**Faster Alternative - Use Pre-built:**
```bash
# If simulation is simple, use conda:
apt-get install -y wget
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh -b
~/miniconda3/bin/conda install -c conda-forge lammps
```

### ML Potentials on VAST

```bash
# On the instance (using pytorch image):

# Install MACE
pip install mace-torch

# Install CHGNet
pip install chgnet

# Install M3GNet
pip install matgl

# Run ASE with MLIP
python << 'EOF'
from ase.build import bulk
from mace.calculators import mace_mp

atoms = bulk('Cu', 'fcc', a=3.6)
calc = mace_mp(model="medium", device="cuda")
atoms.calc = calc
print(f"Energy: {atoms.get_potential_energy():.3f} eV")
EOF
```

### QE on VAST

```bash
# QE GPU installation (longer setup)
apt-get update && apt-get install -y build-essential gfortran libopenmpi-dev

# Download QE
wget https://github.com/QEF/q-e/releases/download/qe-7.2/qe-7.2-ReleasePack.tar.gz
tar xzf qe-7.2-ReleasePack.tar.gz
cd qe-7.2

# Configure with GPU
./configure --enable-cuda
make pw

# Run
./bin/pw.x < input.in > output.out
```

---

## Python Client

Use the included Python client for programmatic access:

```python
import sys
sys.path.insert(0, 'skills/vast-cloud')
from vast_client import VastClient

# Initialize
vast = VastClient()

# Search for cheap 4090s
offers = vast.search_offers(gpu_name="RTX_4090", max_price=0.40)
print(f"Found {len(offers)} offers")

# Rent the cheapest
instance = vast.create_instance(
    offer_id=offers[0]['id'],
    image="nvidia/cuda:12.2.0-devel-ubuntu22.04",
    disk_gb=50
)
print(f"Instance ID: {instance['id']}")

# Wait for ready
vast.wait_until_ready(instance['id'])

# Get SSH connection
ssh_cmd = vast.get_ssh_command(instance['id'])
print(f"Connect with: {ssh_cmd}")

# When done:
vast.destroy_instance(instance['id'])
```

---

## Common Patterns

### Pattern 1: Quick GPU Test

```bash
# Find cheapest available GPU
OFFER=$(vastai search offers "rentable=True gpu_ram>10 dph<0.3" -o "dph+" --raw | head -1 | jq -r '.id')

# Rent it
INSTANCE=$(vastai create instance $OFFER --image nvidia/cuda:12.2.0-devel-ubuntu22.04 --disk 20 --raw | jq -r '.new_contract')

# Wait and connect
sleep 120  # Wait 2 min for boot
SSH_CMD=$(vastai ssh-url $INSTANCE)
echo "Connect: $SSH_CMD"

# After testing, destroy
vastai destroy instance $INSTANCE
```

### Pattern 2: MACE Simulation Job

```bash
# 1. Create instance
vastai create instance <id> --image pytorch/pytorch:2.1.0-cuda12.1-cudnn8-devel --disk 30

# 2. Upload files
scp -P <port> structure.cif root@<host>:/root/
scp -P <port> run_mace.py root@<host>:/root/

# 3. Run job
ssh -p <port> root@<host> "pip install mace-torch ase && python run_mace.py"

# 4. Download results
scp -P <port> root@<host>:/root/results/* ./results/

# 5. Destroy
vastai destroy instance <id>
```

### Pattern 3: Long-Running Job (Use Screen)

```bash
# Connect and start screen session
ssh -p <port> root@<host>
screen -S myjob

# Run long job
python long_simulation.py

# Detach: Ctrl+A, then D
# Reconnect later: screen -r myjob
```

---

## Budget Management

### Check Balance

```bash
vastai show user   # `show credit` was removed in CLI 1.2.0; balance is a field of `show user`
```

### Estimate Cost Before Renting

```bash
# Before renting, check price
vastai search offers "id=<offer_id>" --raw | jq '.dph_total'
# Multiply by expected hours
```

### Set Spending Alerts

Keep track of spending manually:
1. Note start time when creating instance
2. Check elapsed time periodically
3. Destroy before budget exceeded

---

## Troubleshooting

### Instance Won't Start

```bash
# Check instance status
vastai show instance <id>

# If stuck "loading", might be host issue - try different offer
vastai destroy instance <id>
# Try another offer from search
```

### SSH Connection Failed

```bash
# Get current SSH info
vastai ssh-url <id>

# If port changed, use new port
# If host changed, instance may have restarted
```

### Out of Disk Space

```bash
# On instance:
df -h

# Clean up
rm -rf /root/.cache/*
apt-get clean
```

### GPU Not Detected

```bash
# Check NVIDIA driver
nvidia-smi

# If not working, instance may not have GPU properly attached
# Destroy and try different offer
```

---

## Safety Rules

1. **Always destroy when done** - Instances bill until destroyed
2. **Don't store important data only on VAST** - Instances are ephemeral
3. **Set time limits** - Plan when to destroy before starting
4. **Check balance** - Don't exceed prepaid amount
5. **Use SSH keys** - Already configured, don't use passwords

---

## Quick Commands Reference

| Command | Purpose |
|---------|---------|
| `vastai search offers "..."` | Find available GPUs |
| `vastai create instance <id> --image <img>` | Rent a GPU |
| `vastai show instances` | List your instances (CLI 1.2.0 prefers `show instances-v1`; both work) |
| `vastai ssh-url <id>` | Get SSH connection |
| `vastai destroy instance <id>` | Stop billing! |
| `vastai show user` | Check balance |
| `vastai logs <id>` | View instance logs |

---

## Integration with Workflow

### Choosing Between VAST and HPC

```
Decision Tree:
1. Is job GPU-intensive?
   NO → Use local or HPC CPU
   YES → Continue

2. Is HPC available?
   NO → Use VAST
   YES → Continue

3. What's HPC queue time?
   < 30 min → Use HPC (free)
   30 min - 2 hr → Consider VAST if urgent
   > 2 hr → Use VAST

4. Is job > 4 hours?
   YES → Consider HPC (more reliable)
   NO → VAST is fine
```

### Compute Decision Documentation

When using VAST, document:
```markdown
## Compute Choice: VAST AI

**Rationale:** HPC queue showing 3-hour wait, job expected to take 45 minutes.
VAST RTX 4090 available at $0.35/hr. Estimated cost: $0.35.
Time savings: ~2+ hours.

**Instance:** <id>
**Start Time:** <timestamp>
**Expected Duration:** 45 min
```

---

## Example Session

```bash
# Goal: Run MACE relaxation on 100 structures

# 1. Find cheap 4090
$ vastai search offers "gpu_name=RTX_4090 dph<0.4 rentable=True" -o "dph+"
# Found offer 12345678 at $0.32/hr

# 2. Rent it
$ vastai create instance 12345678 --image pytorch/pytorch:2.1.0-cuda12.1-cudnn8-devel --disk 30
# Created instance 87654321

# 3. Wait and check
$ sleep 90
$ vastai show instances
# Instance 87654321: running

# 4. Connect
$ SSH_INFO=$(vastai ssh-url 87654321)
$ echo $SSH_INFO
# ssh -p 12345 root@123.45.67.89

# 5. Upload and run
$ scp -P 12345 -r structures/ root@123.45.67.89:/root/
$ scp -P 12345 relax_all.py root@123.45.67.89:/root/
$ ssh -p 12345 root@123.45.67.89 "pip install mace-torch ase && python relax_all.py"

# 6. Download results
$ scp -P 12345 root@123.45.67.89:/root/results.tar.gz ./

# 7. DESTROY!
$ vastai destroy instance 87654321
# Destroyed. Total cost: ~$0.50 for ~1.5 hours
```
