# Backend: ALCF Polaris

Argonne Leadership Computing Facility's Polaris cluster (NVIDIA A100, PBS Pro). Free with a DOE allocation. Capability-class GPU HPC; the readiness vehicle toward ALCC/INCITE. **Not interchangeable with Alpine** — different scheduler (PBS Pro, not SLURM), different auth (one-time token, not cached key), and node-hour accounting that charges the *whole node* regardless of GPUs used.

> Read this page when picking Polaris for a job or debugging one. The framework lives in `../SKILL.md`. Verified against ALCF user-guides 2026-05-28; re-check the live docs (https://docs.alcf.anl.gov/polaris/) if anything below fails.

## Access

| Item | Value |
|---|---|
| Hostname | `polaris.alcf.anl.gov` |
| User / account | `sefl-alcf` (note: differs from Alpine's `sefl7948`). Account requested 2026-05-28, **pending ALCF approvals** — not active until approved. |
| Connect | `ssh <alcf_username>@polaris.alcf.anl.gov` |
| Authentication | **MobilePASS+ one-time passcode (OTP).** Open the SafeNet MobilePASS+ app → tap the token → enter PIN → app shows an 8-char passcode → type it as the SSH password. Do **not** enter the PIN at the SSH prompt. |
| Project (allocation) | `HydrogenStorage` — pass as `-A HydrogenStorage` on **every** `qsub` |
| Allocation | DD, 5,000 node-hours, expires **2026-11-28** |
| Home | `/home/<alcf_username>` — 50 GB quota, Lustre, **backed up**. Small files + binaries only; not for job I/O. |
| Project space | `/eagle/projects/HydrogenStorage/` (a.k.a. `/lus/eagle/projects/HydrogenStorage/`) — directory quota (shared across team), **not backed up**. Job output + large files go here. Confirm exact path with `ls /eagle/projects/` after first login. |
| Node-local scratch | `/local/scratch` — 1.6 TB NVMe per compute node, xfs, **wiped between jobs**. Stage hot I/O here during a run, copy results to `/eagle` before exit. |
| Scheduler | **PBS Pro** (`qsub` / `qstat` / `qdel`) |

### Authentication is the operational gotcha

Unlike `cu_alpine` (cached public-key + ControlMaster), **every fresh connection to Polaris needs a live OTP from Sean's phone.** The agent cannot log in unattended. Workflow:

1. **Sean opens a persistent master connection once per session**, then the agent reuses it. Add to `~/.ssh/config`:
   ```
   Host polaris
       HostName polaris.alcf.anl.gov
       User <alcf_username>
       ControlMaster auto
       ControlPath ~/.ssh/cm-%r@%h:%p
       ControlPersist 8h
       ServerAliveInterval 60
   ```
   Sean runs `ssh polaris` once (enters OTP), leaves it open. For the persistence window the agent can run `ssh polaris '<cmd>'` without a new passcode.
2. If `ssh polaris '<cmd>'` errors with `Permission denied` or `control socket ... not found`, the master died — **ask Sean to re-run `ssh polaris` and complete the OTP.** Do not try to fix it without him.
3. Never script the OTP. There is no token to cache.

## Pre-installed software

| Package | Path / module | Notes |
|---|---|---|
| NAMD 3.x prebuilt binaries | `/soft/applications/namd/` | Three builds: `Linux-x86_64-netlrts-smp-CUDA` (**GPU-resident** — our default), `Linux-x86_64-ofi-smp-CUDA` (GPU-offload, multi-node single replica), `…-CUDA-memopt` (>100 M atoms). |
| `charmrun` | next to the `namd3` binary in each build dir | Launches multi-copy (replica) runs. |
| CUDA toolkit | `/soft/compilers/cudatoolkit/cuda-12.2.2` | For self-builds only. |
| Additional `/soft` modules | `module use /soft/modulefiles && module avail` | ALCF software outside the Cray PE. |

**Prefer the prebuilt `namd3`** — ALCF recommends it. Self-build instructions exist (swap to `PrgEnv-gnu`, build Charm++ `netlrts` for GPU-resident or `ofi-crayshasta` for offload) but only if a feature is missing. Confirm the exact subdir name under `/soft/applications/namd/` after first login; pin it like we pin the Alpine path.

> **GPU-resident vs offload for our workload:** GPU-resident (`netlrts-smp-CUDA`) keeps the whole step on-GPU and is dramatically faster for a single ~50 k system — ALCF measured **45 ns/day on a 1 M-atom** system, so our 50 k system should land well above that. But a *single* GPU-resident replica runs on **one node only**. Our ensembles are embarrassingly parallel (independent replicas), so we use **multi-copy GPU-resident** via `charmrun` — N replicas spread across nodes, 1 GPU each. This is the right mode. (Offload mode is only for one giant system spanning many nodes — not us.)

## Node architecture (per compute node)

- 1× AMD EPYC Milan 7543P, 32 cores / **64 hardware threads**, 512 GB DDR4
- **4× NVIDIA A100 40 GB**, NVLink-connected (all-to-all NV4)
- GPU↔CPU NUMA affinity (from `nvidia-smi topo -m`): GPU0→cores 24-31,56-63 · GPU1→16-23,48-55 · GPU2→8-15,40-47 · GPU3→0-7,32-39. Matters for `+pemap` / `CUDA_VISIBLE_DEVICES` when packing 4 replicas/node.
- 560 nodes total.

## Queues

**You submit to one of these via `-q`.** Note the surprising constraint for our scale: **`prod` requires ≥10 nodes.** A single 20-replica ensemble is 5 nodes (4 replicas/node), which is *below* `prod`'s floor.

### Smoke / debugging

| Name | Nodes | Walltime | Use |
|---|---|---|---|
| **`debug`** | 1–2 | 5 min–1 hr | **First stop for any new config.** 8 dedicated nodes (+16 if prod is free). |
| `debug-scaling` | 1–10 | 5 min–1 hr | Scaling tests; 1 job per user. Use to verify 4-replica/node packing on ≥1 node. |

### Production

| Name | Nodes | Walltime | Use |
|---|---|---|---|
| `prod` | **10–496** | 5 min–24 hr | Routing queue (→ small/medium/large). **≥10 nodes only** — pack ≥2 ensembles (≥40 replicas) to qualify. 10 jobs running / 100 queued per project. |
| **`preemptable`** | 1–10 | 5 min–**72 hr** | **Best fit for a single 5-node ensemble.** Killable if `demand` jobs arrive — add `#PBS -r y` to auto-requeue. 20 jobs/project. |
| `capacity` | 1–4 | 5 min–**168 hr** | Long single-ensemble runs up to 4 nodes (16 replicas). Max 32 nodes across all jobs; 1 running/user. |
| `demand` | 1–56 | ≤1 hr | By request only; preempts `preemptable`. Not for us. |

## Node-hour accounting (read before sizing)

- **1 node-hour is charged per wall-clock hour per reserved node, regardless of how many of its 4 GPUs you use.** Running 1 replica on a node still burns a full node-hour. → **Always pack 4 replicas/node.**
- A 20-replica ensemble = 5 nodes. At (say) 100 ns/day GPU-resident, 12.5 ns ≈ 3 hr wall → ~15 node-hours/ensemble. The 5,000-node-hour award is large; the real budget question is benchmark throughput, not node count. **Benchmark first (smoke), then project the budget.**

## Decision examples (Polaris specifically)

| Situation | Pick |
|---|---|
| New NAMD config, never run on Polaris | `debug`, 1 node, 1 replica, 30 min — verify exit 0 + finite energies + restart written |
| Verify 4-replica/node packing + GPU affinity | `debug-scaling`, 1–2 nodes, 30 min |
| Benchmark throughput (ns/day) for budget projection | `debug`, 1 node, short run, read NAMD `Benchmark time` lines |
| One 20-replica ensemble, 12.5 ns each | `preemptable`, 5 nodes, `+replicas 20`, `#PBS -r y`, walltime sized to benchmark + margin |
| Two+ ensembles batched (≥40 replicas) | `prod`, ≥10 nodes |
| Single long unattended ensemble ≤16 replicas | `capacity`, 4 nodes, up to 168 hr |
| `preemptable` keeps getting preempted | batch into `prod` (≥10 nodes) or move to `capacity` |

## Submission essentials

```bash
# Submit (from the job's directory)
ssh polaris 'cd /eagle/projects/HydrogenStorage/<campaign> && qsub run.pbs'

# Status (mine)
ssh polaris 'qstat -u <alcf_username>'

# Detailed status of one job
ssh polaris 'qstat -f <jobid>'

# Why is it pending / queue details
ssh polaris 'qstat -Qf preemptable'

# Cancel
ssh polaris 'qdel <jobid>'

# Allocation balance (node-hours left)
ssh polaris 'sbank-list-allocations -p HydrogenStorage'   # or: myprojectquotas, myquota
```

## Job script template

Multi-copy GPU-resident ensemble (the canonical shape for our 20-replicate runs). Adjust bracketed fields. `NREP` replicas across `select` nodes, 4 replicas/node, 1 GPU each.

```bash
#!/bin/bash -l
#PBS -N <name>
#PBS -l select=5:system=polaris          # 5 nodes × 4 GPUs = 20 replicas
#PBS -l place=scatter
#PBS -l walltime=06:00:00                 # < queue max; size from benchmark
#PBS -q preemptable                       # single ensemble; prod needs >=10 nodes
#PBS -r y                                  # rerunnable (preemptable can be killed)
#PBS -A HydrogenStorage
#PBS -l filesystems=home:eagle             # MANDATORY — job won't run without it

cd ${PBS_O_WORKDIR}

NAMD=/soft/applications/namd/<build-dir>/namd3
CHARMRUN=/soft/applications/namd/<build-dir>/charmrun
NREP=20
PPN=4                                       # replicas per node (= GPUs per node)

$CHARMRUN ++mpiexec ++np ${NREP} ++ppn ${PPN} $NAMD \
    +replicas ${NREP} \
    init.conf --source production.namd \
    +pemap 0-63 +setcpuaffinity +devices 0,1,2,3 +devicesperreplica 1 \
    +stdout output/%d/run.%d.log
```

- `+devicesperreplica 1` is **critical** — without it each replica grabs all 4 GPUs.
- `init.conf` is NAMD's replica bootstrap; per-replica config in `production.namd`. Mirror the ALCF REMD example layout, but our replicas are *independent* (not exchanging), so each replica reads its own input dir.
- For a single-system smoke, drop charmrun: `mpiexec -n 1 --ppn 1 --depth=16 --cpu-bind=depth $NAMD +p 15 +devices 3,2,1,0 smoke.namd > smoke.out`.

## Common failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| `ssh polaris` asks for password every command | ControlMaster not open / expired | Sean re-runs `ssh polaris`, enters OTP; agent reuses the socket |
| Job rejected: filesystems not requested | missing `-l filesystems=home:eagle` | Add it — mandatory on every job |
| Job rejected: queue node count | `prod` submitted with <10 nodes | Use `preemptable`/`capacity`, or batch to ≥10 nodes |
| Job killed without warning on `preemptable` | a `demand` job preempted it | Expected risk; `#PBS -r y` requeues it. Move hot runs to `prod`/`capacity` |
| Each replica binds all 4 GPUs / OOM | missing `+devicesperreplica 1` | Add the flag |
| No internet from compute node (e.g. pip) | compute nodes need proxy | `export https_proxy=http://proxy.alcf.anl.gov:3128` (see getting-started proxy block) |
| `/local/scratch` data gone after job | node-local, wiped per job | Copy results to `/eagle` before the job exits |
| Charm++ "insufficient CUDA driver" on login node | login nodes have no GPU | Ignore — only build/submit on login; run on compute |

Add rows as new failures appear.

## Storage discipline

- **`/eagle/projects/HydrogenStorage/`**: campaign working data + output. Directory quota is shared across the team — watch total usage (`myprojectquotas`). Not backed up → pull DCDs back to local (`~/ccm-results/...`) and/or Globus to CU after each campaign. ALCF scratch retention is short; don't park data here long-term.
- **`/local/scratch`** (per node): stage hot I/O here during a run; copy out before exit.
- **Home (50 GB, backed up)**: binaries + scripts only. Never run jobs from home.
- Per campaign: `/eagle/projects/HydrogenStorage/<campaign>/` — don't intermix runs.
- **Data egress**: use Globus + ALCF DTN for large trajectory transfers to CU Boulder. Acknowledge ALCF in any publication using these results (allocation policy).

## Project-level wrappers

ALCF/Polaris is operated from a dedicated hub: **`~/work/compute/alcf/`**. The applied playbook is `alcf/docs/POLARIS_PLAYBOOK.md` — bring-up checklist, stage tracking, NAMD launch examples, validation-gate artifacts, lessons learned; `alcf/AGENTS.md` has hub boundaries; `alcf/deploy/templates/` has PBS job templates. This page is the cross-project backend reference; the hub is where Polaris operational state lives. There is no CCM-style wrapper for Polaris yet — drive it through `ssh polaris` + PBS directly.
