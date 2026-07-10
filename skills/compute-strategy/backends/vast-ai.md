# Backend: Vast.ai cloud GPUs

On-demand GPU marketplace. No queue, instant allocation, pay per hour.

> Read this page when picking a Vast.ai instance. The framework lives in `../SKILL.md`. Concrete CLI / templates / examples live in the sibling skill `skills/vast-cloud/SKILL.md` — this page is the *strategy* layer (what to ask Vast.ai for and why).

## When Vast.ai wins over HPC

- HPC unreachable (network, VPN, allocation expired)
- Job is short (< 4 hr) and HPC queue is multi-hour
- Time-critical: need result in the next hour, not tomorrow morning
- Embarrassingly-parallel ensemble where HPC concurrency cap is the bottleneck (rent 20 instances, run 20 jobs simultaneously)

## When HPC still wins

- Long jobs (> 8 hr) where Vast.ai cost surpasses HPC convenience
- Restart-friendly multi-day campaigns
- Tight budget (HPC is free with allocation; Vast.ai isn't)
- HPC queue is short and the job isn't urgent

## When local wins

- Sub-30 min CPU jobs (file munging, plotting, FF lint)
- Jobs that don't actually need a GPU
- Iterating on inputs before any GPU run

## Instance selection — pricing snapshot

Prices are per-hour spot-market values. Sanity-check at submit time with `vastai search offers` (rates fluctuate).

| GPU | Typical $/hr | Use for |
|---|---|---|
| RTX 3090 | $0.15–0.25 | Light ML, small LAMMPS / MLIP |
| RTX 4090 | $0.25–0.45 | MACE, CHGNet, medium LAMMPS, NAMD up to ~30 k atoms |
| A100 40GB | $0.80–1.50 | Large MD, QE GPU |
| A100 80GB | $1.20–2.00 | Very large MD, NAMD up to ~100 k atoms |
| H100 | $2.00–4.00 | Maximum performance, large LLM / large MLIP |

**Cost discipline:** an 8-hour run on A100 80GB is ~$10–16. An 8-hour run on Alpine `aa100` is $0. Use Vast.ai when the time saved outweighs the cost; not by default.

## Reliability filtering

Vast.ai offers wide reliability variance. Default to filtering for stability:

```bash
# Reliability ≥ 0.99 — drops the bad-host tail
vastai search offers "gpu_name=RTX_4090 rentable=True reliability>0.99 dph<0.5" -o "dph+"

# CUDA ≥ 12.6 — required for modern NAMD NGC builds
vastai search offers "gpu_name=A100 rentable=True cuda_vers>=12.6 reliability>0.99" -o "dph+"
```

Cheaper-tier hosts can fail mid-run; the reliability filter pays for itself in not having to re-run.

## Project-level wrappers

Some projects wrap Vast.ai access through a higher-level tool. **If a project says "use the wrapper, not raw vastai," respect that.**

Known wrappers in this user's environment:
- **CCM (CloudComputeManager)** at `~/work/compute/ccm/`: hardened wrapper covering submission, daemon, sync, recovery. Used by the Pt-NEC LOHC project. The project rule there is **never call vastai CLI directly** — use `ccm jobs submit`, `ccm status`, `ccm exec`. CCM has a checkpoint-restart system, reliability filtering, async recovery.

If your project doesn't have a wrapper, the lower-level recipes in `skills/vast-cloud/SKILL.md` are the canonical entry point.

## Iteration loop on Vast.ai

The smoke-first principle still applies. The "smoke partition" mapping for Vast.ai:

| Stage | Recipe |
|---|---|
| 0 — Local sanity | Same as any backend: dry-run, file lint |
| 1 — Smoke | **Cheapest GPU that fits**, ≤ 1 hr instance, run 5–10 ps physics. Destroy instance immediately on completion. ~$0.20–0.50. |
| 2 — Single production | Right-sized GPU, single job. Validate end-to-end on one input before fanning out. |
| 3 — Fan out | Multiple instances if embarrassingly parallel; OR multiple jobs on one instance if sequential. |

**Always destroy instances when done.** Vast.ai bills until you destroy. The single biggest cost mistake is leaving an instance running idle.

## Submission hygiene (Vast.ai-specific)

### Always

- Set a **billing budget** when submitting via CCM or whatever wrapper you use
- **Filter by reliability** ≥ 0.99 unless you have a specific reason not to
- **Sync output** periodically during long runs — Vast.ai instances can be preempted
- **Destroy on completion**, even if the job failed

### Never

- ❌ Leave a paid instance running idle "just in case I need to debug" — instead, copy logs locally and destroy
- ❌ Submit production work to a host with reliability < 0.95
- ❌ Bypass the project's wrapper (CCM etc.) when the project has one

## Common failure modes (Vast.ai-specific)

| Symptom | Likely cause | Fix |
|---|---|---|
| Instance dies mid-run | Spot-market preemption, low-reliability host | Use `reliability_min=0.99`; add periodic sync |
| `CUDA version mismatch` | Host CUDA driver too old for NGC container | Filter `cuda_vers>=12.6` |
| File transfer hangs | Network bottleneck on bad host | Pick a different geographic region |
| Surprise bill | Forgot to destroy instance | Set budget caps; add a destroy-on-exit hook in run scripts |
| Inconsistent throughput between hosts | GPU thermal throttling, shared resources | Filter reliability; benchmark a smoke before committing to long run |

## Cost / time decision quick-reference

> "Should I run this on Vast.ai or HPC?" — if any of these apply, lean Vast.

- HPC queue wait > 4 hr AND job < 8 hr
- Job < 1 hr AND HPC requires queue
- HPC unreachable
- Need result in the next 90 minutes
- Concurrency-bound work hitting HPC submit caps

> Otherwise lean HPC.

When in doubt, ask the user — cost decisions deserve human input.
