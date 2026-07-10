# Backend: Local (WSL2 / native)

The local machine. Free, instant, but limited. Default for sub-hour CPU work, light prep, debugging.

> Read this page when picking the local box for a job. The framework lives in `../SKILL.md`.

## Hardware (as of 2026-05)

| Item | Value |
|---|---|
| Machine | Lenovo laptop, WSL2 on Windows |
| OS | Ubuntu 22.04 (WSL2) |
| Kernel | 6.6.x microsoft-standard-WSL2 |
| GPU | NVIDIA RTX 5080 Laptop (16 GB VRAM) |
| CPU | Modern Intel/AMD laptop (24 cores typical) |
| RAM | Reasonable (check `free -h` if unsure) |

If the user's machine changes (new laptop, different GPU), update this page.

## When local wins

- Sub-30 min jobs of any kind
- CPU work: file munging, structure prep, FF lint, plotting
- GPU work that fits in 16 GB VRAM and runs in < 1 hr
- Iterating on inputs before any cloud / HPC submission
- Debugging an output file or trajectory locally
- Running analysis pipelines that don't need cluster-scale parallelism

## When local loses

- Long-running compute (> 1–2 hr) — your laptop is not a workstation
- Memory-hungry jobs (> 16 GB VRAM, > 32 GB RAM)
- Wide ensembles (run 1 instance locally; HPC arrays for fan-out)
- Anything that needs to run unattended overnight / weekend (laptops sleep, lose network, etc.)
- Production trajectories you want to reproduce — repro on shared compute is cleaner

## WSL2 quirks (relevant for compute)

- **Memory limit defaults to half the host RAM.** Configurable via `~/.wslconfig` — check before assuming you can run a 32 GB job.
- **GPU passthrough works** for CUDA but driver versions can drift. If a build that worked yesterday is broken today, check the host's NVIDIA driver.
- **Network performance varies** for WSL ↔ external (Vast.ai, HPC). Use `rsync -av` with `--partial --inplace` for resumable transfers.
- **REPEX / replica-exchange jobs** can OOM on WSL2 with 16+ replicas. Cap iterations at ≤ 250 if you must. (Project memory: feedback_repex_memory.)

## Iteration loop on local

Same shape as HPC / Vast.ai, just smaller scales:

| Stage | Recipe |
|---|---|
| 0 — Sanity | Local lint, dry-run, syntax check |
| 1 — Smoke | 5–10 ps run on the laptop GPU. Confirm physics, output, throughput. |
| 2 — Single small production | Real run if it fits in 1 hr and 16 GB. Otherwise advance to HPC / Vast.ai. |
| 3 — Fan out | Don't fan out locally. The laptop is one job at a time. |

If Stage 2 outgrows the laptop, the smoke result still validates the config — push to HPC or Vast.ai for the real run.

## Software / paths

Most binaries are managed via conda (`miniconda3`), nvm, rustup, juliaup. CUDA is system-wide 12.x with NVHPC at `~/hpc-sdk/`. See top-level CLAUDE.md for the full inventory.

## Common failure modes (local)

| Symptom | Likely cause | Fix |
|---|---|---|
| `CUDA out of memory` | system bigger than 16 GB | Use HPC `aa100` or Vast.ai A100 |
| WSL2 laggy / freezing | Windows host under load | Close other apps; if persistent, restart WSL with `wsl --shutdown` from PowerShell |
| Conda env clobbered | dependency conflict | Recreate env; document in `environments/` if reusable |
| Network sync slow | WSL ↔ external bottleneck | Use `rsync -av --partial`; consider rsyncing from Windows side |
| Job killed overnight | laptop slept | Run on HPC or Vast.ai for unattended work |

## Default to using local for

- Pre-flight: `deploy_hpc.sh --dry-run`, syntax checks, file manifests
- Post-flight: pulling DCDs / outputs from HPC, running analysis pipelines
- Plotting, manuscript figure generation
- Interactive debugging of a small reproducer
- Any work where you want to iterate at conversation pace
