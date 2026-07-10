# Backend: CU Boulder Alpine HPC

University of Colorado Research Computing's Alpine cluster. Free with allocation, GPU-rich, SLURM-managed. Primary HPC for any project running on Sean's CU Boulder accounts.

> Read this page when you're picking a partition or debugging an Alpine job. The framework lives in `../SKILL.md`.

## Access

| Item | Value |
|---|---|
| Hostname | `dtn.rc.colorado.edu` (the Data Transfer Node — has full SLURM + scratch/projects). NOT the login node. |
| User | `sefl7948` |
| SSH alias | `cu_alpine` (and `alpine`) → the DTN, configured in `~/.ssh/config` |
| Connect | `ssh cu_alpine` — key-only, **NO Duo**, no password, no VPN |
| Authentication | Public-key, CILogon-registered. Duo-free via the DTN (works on the CU campus network). |
| Login node | `login.rc.colorado.edu` (alias `alpine-login`) needs IdentiKey **password + Duo** — use ONLY for an interactive shell on the login node, not for autonomous work. |
| Scratch | `/scratch/alpine/sefl7948/` (~787 TB free, project-wide) |
| Project space | `/projects/sefl7948/` (~250 GB total, software lives here) |
| SLURM | 24.11.5 (current as of 2026-05) |

The DTN is **Duo-free** — there is no "refresh Duo" step. If `ssh cu_alpine` errors: confirm you're on the CU campus network (the key path requires it) and that the key `~/.ssh/cu_alpine` is present. (Canonical writeup: `~/.claude/skills/cu-hpc-access`.)

## Pre-installed software (project-paid)

| Package | Path | Notes |
|---|---|---|
| NAMD 3.0.2 multicore-CUDA | `/projects/sefl7948/software/NAMD_3.0.2_Linux-x86_64-multicore-CUDA/namd3` | Verified working on `aa100`. Login-node throws `CUDA driver insufficient` (no GPU on login) — ignore. |

Module system has Quantum ESPRESSO, GROMACS, etc. via `module spider <pkg>`. NAMD is **not** in modules — use the path above.

## Partitions

The agent should always pick a partition matched to the *intent* of the job, not the largest one available.

### Smoke / debugging partitions

| Partition | GPU | Max walltime | Use |
|---|---|---|---|
| **`atesting_a100`** | A100 (3g.20gb MIG) | 1 hr | **Smoke tests, GPU debugging.** First stop for any new GPU config. |
| `atesting_mi100` | AMD MI100 | 1 hr | Smoke for AMD-targeted code. NAMD CUDA build won't run here. |
| `atesting` | none (CPU) | 1 hr | CPU-only sanity (file I/O, FF parsing without GPU). 60 nodes. |
| `acompile` | none | 12 hr | Software compilation. |

Smoke partitions use QoS `testing` (auto-applied).

### Production GPU partitions

| Partition | GPU | Max walltime | Default | Capacity | Use |
|---|---|---|---|---|---|
| **`aa100`** | A100 full | 24 hr | 12 hr | 11 nodes / 33 GPUs | **Default for GPU production.** Best for NAMD, MD, MLIP. |
| `al40` | L40 | 24 hr | 12 hr | small | `aa100` overflow / fallback. Slightly slower for FP64. |
| `ami100` | AMD MI100 | 24 hr | 12 hr | small | Only if running an MI100-targeted build. NAMD CUDA does not. |
| `gh200` | Grace Hopper | 7 days | 4 hr | very small | Reserve for *large* systems (> 100 k atoms) or jobs needing > 80 GB GPU memory. Don't use for slab-scale work. |

### CPU production partitions

| Partition | Max walltime | Default | Use |
|---|---|---|---|
| `amilan` | 24 hr | 4 hr | CPU production. |
| `amem` | 7 days | 4 hr | High-memory CPU jobs. |

## QoS

| QoS | Max walltime | Max submit | Use |
|---|---|---|---|
| `normal` | 24 hr | 1000 | **Default for all production jobs.** |
| `long` | 7 days | 200 | Single-shot jobs > 24 hr. **Prefer chained `normal` jobs with restart over `long` for MD.** |
| `testing` | 1 hr | — | Auto-applied on `atesting*` partitions. |

## Decision examples (Alpine specifically)

| Situation | Pick |
|---|---|
| New NAMD config, never run | `atesting_a100`, 30 min walltime |
| Validated NAMD config, 5 ns NPT @ ~50 k atoms | `aa100`, 12 hr walltime |
| 400 ns 1000 K decorrelation @ ~50 k atoms | `aa100` chained jobs (each 24 hr, restart-friendly) |
| 60-job production array (12.5 ns each) | `aa100`, `--array=1-20%5` per surface (cap concurrent at 5) |
| `aa100` queue is jammed (> 4 hr wait) | Same job on `al40` instead |
| > 24 hr single-shot run | `aa100` long QoS *only if* restart isn't viable |

## SLURM essentials

```bash
# Submit
ssh cu_alpine 'cd <jobdir> && sbatch <script>.sh'

# Status (mine)
ssh cu_alpine 'squeue -u sefl7948'

# Status (verbose, with reason for pending)
ssh cu_alpine 'squeue -u sefl7948 --format="%.10i %.10P %.20j %.2t %.10M %R"'

# Recent finished jobs
ssh cu_alpine 'sacct -u sefl7948 -S now-24hours --format=JobID,JobName,State,Elapsed,ExitCode'

# GPU usage on a running job
ssh cu_alpine 'srun --jobid=<JOBID> --pty nvidia-smi'

# Partition snapshot
ssh cu_alpine 'sinfo -p aa100,atesting_a100'

# Cancel a job
ssh cu_alpine 'scancel <JOBID>'
```

## Job script template

Copy this for new GPU jobs; adjust the bracketed fields. Keeps every project's slurm scripts isomorphic.

```bash
#!/bin/bash
#SBATCH --job-name=<name>
#SBATCH --partition=aa100               # or atesting_a100 for smoke
#SBATCH --qos=normal                    # or testing for smoke
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --gres=gpu:1
#SBATCH --time=12:00:00                 # < partition max
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=<email>             # optional, recommended

mkdir -p logs
cd $SLURM_SUBMIT_DIR

echo "=== Job $SLURM_JOB_ID on $(hostname) at $(date) ==="
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader

# ... actual run command ...

echo "=== Exit $? at $(date) ==="
```

## Common failure modes (Alpine-specific)

| Symptom | Likely cause | Fix |
|---|---|---|
| `CUDA driver version is insufficient` on login | login nodes have no GPU | Ignore — only matters on GPU nodes |
| Job pending with reason `Resources` for hours | partition saturated | Switch to `al40` or wait |
| Job pending with reason `QOSMaxJobsPerUserLimit` | hit submit cap | Reduce concurrent jobs |
| Walltime exceeded mid-run | underestimated `--time` | Add restart resilience; chain `--dependency=afterany` for resume |
| `OUT_OF_MEMORY` on GPU | system bigger than GPU memory | Try `gh200` or split run |
| `restart.xsc` missing after walltime hit | NAMD didn't checkpoint | Add `restartFreq 50000` to NAMD config |

## Storage discipline

- **`/scratch/alpine/`**: working data. Auto-purged on a timer (check current policy). Pull DCDs / outputs back to local soon after completion.
- **`/projects/`**: stable storage, software, scripts. Don't put large output here.
- **Home (`/home/sefl7948`)**: small. Don't run from home.

For each campaign use a top-level scratch directory: `/scratch/alpine/sefl7948/<campaign>/`. Don't intermix runs.
