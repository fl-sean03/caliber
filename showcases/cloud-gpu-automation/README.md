# Showcase: Cloud GPU Automation

**Benchmark:** BENCH-T17-001 | **Score:** 97/100 | **Duration:** 5 minutes

## The Challenge

> Autonomously provision a cloud GPU on VAST.ai, verify it works, and properly clean up - demonstrating infrastructure management without human intervention.

This tests the agent's ability to manage cloud compute resources safely and cost-effectively.

## Result: Perfect Lifecycle Management

The agent successfully:

1. **Searched** for cost-effective GPU options
2. **Provisioned** an RTX 4090 instance at $0.35/hr
3. **Verified** GPU functionality with nvidia-smi
4. **Executed** a test calculation
5. **Destroyed** the instance leaving no orphans

### Performance Summary

| Metric | Result |
|--------|--------|
| Instance provisioned | Yes |
| GPU verified | Yes |
| Test passed | Yes |
| Instance destroyed | Yes |
| Orphan instances | **0** |
| Total cost | ~$0.03 |

## Agent Workflow

```
1. Check Existing      -> vastai show instances (check for orphans)
2. Search GPUs         -> vastai search offers "gpu_name=RTX_4090 dph<0.50"
3. Select Instance     -> Cost-benefit analysis, pick best option
4. Create Instance     -> vastai create instance with CUDA image
5. Wait for Ready      -> Poll until SSH available
6. Verify GPU          -> SSH + nvidia-smi
7. Run Test            -> Python calculation on GPU
8. Cleanup             -> vastai destroy instance
9. Verify Cleanup      -> Confirm 0 instances remain
```

### Key Commands Executed

```bash
# Search for affordable GPUs
vastai search offers "gpu_name=RTX_4090 dph<0.50 rentable=true"

# Create instance with proper labeling
vastai create instance <offer_id> --image nvidia/cuda:12.2.0-devel-ubuntu22.04 \
  --label "BENCH-T17-001"

# Verify and cleanup
ssh root@<host> nvidia-smi
vastai destroy instance <id>
```

## Why This Matters

Cloud GPU management is critical for computational science at scale:

1. **Cost efficiency** - Select cheapest GPU that meets requirements
2. **Reliability** - Handle SSH connection issues gracefully
3. **Safety** - ALWAYS clean up to avoid runaway costs
4. **Automation** - No human intervention needed

### Cost Safety Features

The agent demonstrates:
- Instance labeling (`BENCH-*`) for tracking
- Post-run verification of cleanup
- Awareness of existing user instances (won't touch non-benchmark instances)

## Scaling Up

This same capability enables:

| Benchmark | What It Does |
|-----------|--------------|
| T17-002 | Full environment setup (conda, MACE, ASE) |
| T17-003 | File transfer workflow (local -> cloud -> local) |
| T17-004 | Cost-aware GPU selection |
| T17-005 | Multi-instance parallel jobs |
| T17-006 | Error recovery from cloud failures |
| T17-007 | Long jobs with checkpointing |
| T17-008 | Hybrid local-cloud research pipelines |

## Evaluation Details

The benchmark uses LLM-as-judge grading with detailed category scoring:

| Category | Score | Weight | Key Evidence |
|----------|-------|--------|--------------|
| Provisioning | 95 | 25% | RTX 4090 at $0.2605/hr, from 19 offers, 99.7% reliability |
| Verification | 100 | 25% | Full nvidia-smi output, specs match offer exactly |
| Cleanup | 100 | 30% | Instance destroyed 8 sec after verification, zero orphans |
| Documentation | 95 | 20% | Complete timeline, cost tracking, recommendations |

### Strengths (from LLM evaluation)

- Complete lifecycle execution: provision -> verify -> destroy -> confirm cleanup
- GPU verification includes full nvidia-smi output showing exact specs match
- Explicit cleanup verification with `vastai show instances` showing empty table
- Cost tracking shows actual balance change ($66.60 -> $66.59 = $0.01)
- Prompt resource cleanup - only 8 seconds between verification and destruction

### Areas for Improvement

- Selection logic could explain WHY this offer was chosen over others
- Search/create commands not shown verbatim (only destroy)
- No error handling documentation

## Session Statistics

| Metric | Value |
|--------|-------|
| **Duration** | 5 minutes |
| **Agent Turns** | 29 |
| **Total Cost** | $0.79 |
| **Files Created** | 2 |
| **Models Used** | Claude Opus 4.5, Haiku 4.5 |

### Agent Timeline (from transcript)

```
00:32:00  Started task
00:33:15  Balance verified: $66.60
00:33:30  Searched 19 GPU offers
00:34:00  Selected RTX 4090 at $0.2605/hr (Hong Kong, 99.7% reliability)
00:34:15  Created instance ID 31913120
00:36:03  SSH ready detected
00:36:25  GPU verified via nvidia-smi (RTX 4090, 24GB, CUDA 12.4)
00:36:33  Instance destroyed
00:36:38  Cleanup verified: 0 instances
00:36:40  Final balance: $66.59 ($0.01 spent)
```

### Files Generated

```
the run workspace BENCH-T17-001/
├── instance_log.md      # Full operation timeline with nvidia-smi output
└── cost_analysis.md     # Cost tracking and efficiency analysis
```

## Reproduce This Result

```bash
cd /path/to/caliber
# historical v1 run id: BENCH-T17-001 (v1 suite retired; see caliber/)

# Check for orphan instances after
vastai show instances | grep BENCH
# Should return nothing
```

**Full results:** the archived v1 run records
**Note:** Requires VAST.ai account with API key configured.
