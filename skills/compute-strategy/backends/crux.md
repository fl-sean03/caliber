# Backend: ALCF Crux

Argonne Leadership Computing Facility's Crux cluster — CPU-only HPE Cray EX (dual AMD EPYC Rome, 128 cores/node), PBS Pro. Free with a DOE allocation. The **CPU companion** to Polaris under the same `HydrogenStorage` award; the bulk of our node-hours live here. Use for large CPU MD or many parallel CPU jobs packed onto full nodes.

> Read this page when picking Crux for a job or debugging one. The framework lives in `../SKILL.md`. Verified against ALCF user-guides 2026-05-28; re-check https://docs.alcf.anl.gov/crux/ if anything below fails. Operationally it's a sibling of `polaris.md` — same auth, same PBS Pro, same `/eagle`; the difference is **CPU not GPU**.

## Access

| Item | Value |
|---|---|
| Hostname | `crux.alcf.anl.gov` (login nodes `crux-login-01`, `crux-login-02`) |
| User / account | `sefl-alcf` (same ALCF account as Polaris; differs from Alpine `sefl7948`). Account requested 2026-05-28, **pending ALCF approvals**. |
| Connect | `ssh sefl-alcf@crux.alcf.anl.gov` |
| Authentication | **MobilePASS+ one-time passcode (OTP)** — same as Polaris. Open SafeNet MobilePASS+ → tap token → enter PIN → type the 8-char passcode as the SSH password. Agent **cannot** log in unattended — use a ControlMaster Sean opens once (see below). |
| Project (allocation) | `HydrogenStorage` — `-A HydrogenStorage` on every `qsub` |
| Allocation | DD, **20,000 node-hours** on Crux, expires **2026-11-28** (≈ 2.56M CPU core-hours @ 128 cores/node) |
| Home | `/home/sefl-alcf` — 50 GB, backed up. Binaries + scripts only. |
| Project space | `/eagle/projects/HydrogenStorage/` (shared with Polaris — same Eagle filesystem). Not backed up. Job output here. |
| Scheduler | **PBS Pro** (`qsub` / `qstat` / `qdel`) |

### Auth: same ControlMaster pattern as Polaris

Add a `Host crux` block alongside the `polaris` one in `~/.ssh/config`:
```
Host crux
    HostName crux.alcf.anl.gov
    User sefl-alcf
    ControlMaster auto
    ControlPath ~/.ssh/cm-%r@%h:%p
    ControlPersist 8h
    ServerAliveInterval 60
```
Sean runs `ssh crux` once (enters OTP); the agent reuses `ssh crux '<cmd>'` for the persistence window. If the socket dies, ask Sean to re-auth. Never script the OTP.

## Node architecture (per compute node)

- 2× AMD EPYC 7742 (Rome), **64 cores each = 128 cores/node**, 256 hardware threads (2/core)
- 256 GB DDR4 (128 GB/socket)
- **8 NUMA domains, 16 cores each.** CPU0: NUMA0=0-15, NUMA1=16-31, NUMA2=32-47, NUMA3=48-63. CPU1: NUMA4=64-79, NUMA5=80-95, NUMA6=96-111, NUMA7=112-127 (hyperthread siblings +128). Matters for `--cpu-bind` when packing multiple apps/node.
- 256 nodes total; 1.18 PF peak; Slingshot interconnect.

## Pre-installed software

| Package | Path / module | Notes |
|---|---|---|
| ALCF software | `module use /soft/modulefiles && module avail` | Load `spack-pe-base` for build tools (cmake, etc.). |
| NAMD (CPU) | **confirm on first login** — `ls /soft/applications/` | Crux is CPU-only → use a NAMD multicore or MPI (non-CUDA) build. Don't assume the Polaris GPU path. ALCF can build binaries on request (support@alcf.anl.gov). |

Build code **on compute nodes** (interactive job), not login nodes — especially large parallel builds.

## Queues

You submit to one of these via `-q`.

### Smoke / debugging

| Name | Nodes | Walltime | Use |
|---|---|---|---|
| **`debug`** | 1–8 | 5 min–2 hr | First stop for new configs. 8 exclusive nodes. |

### Production

| Name | Nodes | Walltime | Use |
|---|---|---|---|
| **`workq-route`** | 1–184 | 5 min–24 hr | **Default production.** Routing queue → `workq`. 10 running / 20 queued+running / 100 jobs per project. |
| `preemptable` | 1–10 | 5 min–**72 hr** | Long single jobs ≤10 nodes; killable if `demand` arrives → add `#PBS -r y`. |
| `demand` | 1–64 | ≤1 hr | By request only (email support). Preempts `preemptable`. |

> Note: no separate `prod`-with-10-node-floor like Polaris. On Crux, `workq-route` accepts 1+ node, so single-node CPU jobs are fine here.

## Node-hour accounting (read before sizing)

- **1 node-hour billed per wall-clock hour per node, regardless of cores used.** → **use all 128 cores** (one large system, or pack multiple systems/replicas onto a node).
- Rough cross-machine math (Hendrik 2026-05-28): 1 A100 ≈ 8× a 128-core CPU node for our MD; so **1 Crux node-hour ≈ ⅛ of a single-A100 node-hour of throughput**. Crux's value is *volume* (20k node-hr ≈ 2.56M core-hr) and large/embarrassingly-parallel CPU work, not per-job speed. Reserve latency-sensitive / high-throughput MD for Polaris GPUs.

## Decision examples (Crux specifically)

| Situation | Pick |
|---|---|
| New CPU config, never run | `debug`, 1 node, ≤30 min |
| Large single CPU MD system (fills 128 cores) | `workq-route`, sized walltime |
| Many independent CPU jobs | pack multiple `mpiexec` per node (see multi-app pattern) or job-per-node across a multi-node `workq-route` job |
| Long single CPU run ≤10 nodes | `preemptable`, `#PBS -r y` |
| GPU-suited / high-throughput MD | **not Crux — use Polaris** (`backends/polaris.md`) |

## Submission essentials

```bash
ssh crux 'cd /eagle/projects/HydrogenStorage/<campaign> && qsub run.pbs'   # submit
ssh crux 'qstat -u sefl-alcf'                                              # my jobs
ssh crux 'qstat -f <jobid>'                                                # job detail
ssh crux 'qdel <jobid>'                                                    # cancel
ssh crux 'sbank-list-allocations -p HydrogenStorage'                       # balance
```

## Job script template

MPI+OpenMP fill-the-node (128 cores). Adjust ranks/threads to the app.

```bash
#!/bin/bash -l
#PBS -N <name>
#PBS -l select=1:system=crux
#PBS -l place=scatter
#PBS -l walltime=06:00:00
#PBS -q workq-route               # or debug for smoke
#PBS -A HydrogenStorage
#PBS -l filesystems=home:eagle    # MANDATORY

cd $PBS_O_WORKDIR
NNODES=$(wc -l < $PBS_NODEFILE)
NRANKS_PER_NODE=64; NDEPTH=2; NTHREADS=2     # 64 ranks × 2 threads = 128 cores
NTOTRANKS=$(( NNODES * NRANKS_PER_NODE ))

mpiexec -n ${NTOTRANKS} --ppn ${NRANKS_PER_NODE} --depth=${NDEPTH} --cpu-bind depth \
    --env OMP_NUM_THREADS=${NTHREADS} --env OMP_PROC_BIND=true --env OMP_PLACES=cores \
    ./my_app
```

For **multiple apps/node** (e.g. independent MD replicas), launch several `mpiexec ... --cpu-bind list:<cores>` backgrounded (`&`) over distinct NUMA domains and `wait` — see the ALCF Crux running-jobs doc multi-app example. **Always set `OMP_NUM_THREADS`** — default is 256 and will oversubscribe.

## Common failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| `ssh crux` prompts for password every command | ControlMaster not open/expired | Sean re-runs `ssh crux`, enters OTP |
| Job rejected: filesystems not requested | missing `-l filesystems=home:eagle` | add it (mandatory) |
| Massive slowdown / oversubscription | `OMP_NUM_THREADS` defaulted to 256 | set it explicitly (e.g. 2) |
| No internet from compute node | needs proxy | `export https_proxy=http://proxy.alcf.anl.gov:3128` |
| Job killed without warning on `preemptable` | `demand` job preempted it | `#PBS -r y` to requeue; or use `workq-route` |

Add rows as new failures appear.

## Storage discipline

Same Eagle filesystem as Polaris: `/eagle/projects/HydrogenStorage/<campaign>/` (shared directory quota, not backed up). Home 50 GB, backed up, binaries only. Pull results to local / Globus to CU after each campaign. Acknowledge ALCF in publications.

## Project-level wrappers

ALCF is operated from the hub at `~/work/compute/alcf/` — see `alcf/AGENTS.md` and `STATUS.md` for the full multi-resource allocation. There is no CCM-style wrapper for Crux — drive it through `ssh crux` + PBS directly.
