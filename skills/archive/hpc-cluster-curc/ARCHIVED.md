# ARCHIVED: CURC Alpine HPC Skill

**Archived:** 2026-02-20
**Reason:** CURC access deferred; switching to VAST.ai for cloud GPU compute

## What Was Here

This skill provided integration with CU Boulder's Alpine HPC cluster:
- SSH connection management
- SLURM job submission and monitoring
- File transfers (scp/rsync)
- Module system interaction
- Async job tracking

## Replacement

Use **VAST.ai** skill (`skills/vast-cloud/`) for GPU compute needs:
- Immediate access (no queue)
- Pay-per-hour (~$0.25-0.45/hr for RTX 4090)
- Python client: `vast_client.py`
- ~$25 balance available

## Related Benchmarks (Also Archived)

The following benchmark tiers depend on CURC and are not currently runnable:
- Tier 5: HPC Fundamentals (7 benchmarks)
- Tier 6: HPC Scale (5 benchmarks)
- Tier 7: Research Campaigns (T7-001, T7-003)
- Tier 11: HPC+ML Hybrid (7 benchmarks)

See `benchmarks/docs/archive/hpc-proposals/` for original design docs.

## Restoring

If CURC access is restored:
1. Move files back to `skills/hpc-cluster/`
2. Update SSH config with new credentials
3. Re-enable benchmark tiers in status files
