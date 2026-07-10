# Showcases

> These are real runs from the project's original evaluation suite (2026 H1),
> preserved as capability demonstrations. The current benchmark is [Caliber](../benchmark/).

Real examples of autonomous research conducted by the Caliber (then the Agentic Science Worker). Each showcase demonstrates end-to-end capability on a challenging scientific task.

> **Note:** Showcases represent specific successful runs. Complex autonomous benchmarks show variability - the same benchmark may score differently on different runs. These showcases demonstrate what the agent CAN achieve.

## Featured Showcases

### 1. [Novel Li-Ion Cathode Discovery](novel-cathode-discovery/)
**Benchmark:** T10-001 | **Score:** 75/100 | **Time:** 22 min

The agent autonomously discovered **9 novel high-voltage cathode materials** not in the Materials Project database. The top discovery, Li2Ni(PO4)(SO4), achieves 5.1V with excellent stability.

**What it demonstrates:**
- Literature-driven hypothesis generation
- High-throughput computational screening (88 candidates)
- MLIP-based stability filtering
- Novelty verification against databases
- Publication-quality research report

---

### 2. [XRD Structure Determination](xrd-structure-determination/)
**Benchmark:** T10-002 | **Score:** 72/100 | **Time:** 8 min

Given only an XRD pattern, the agent determined the crystal structure is **layered R-3m LiNiO2** through systematic analysis and pattern matching against 23 candidate structures.

**What it demonstrates:**
- Cross-modal scientific reasoning (experimental -> computational)
- Bragg's law calculations and systematic absence analysis
- Database queries and structure comparison
- Publication-quality figures

---

### 3. [Cloud GPU Automation](cloud-gpu-automation/)
**Benchmark:** T17-001 | **Score:** 97/100 | **Time:** 5 min

The agent autonomously provisioned a cloud GPU (VAST.ai), verified functionality, and properly cleaned up resources - demonstrating infrastructure management capability.

**What it demonstrates:**
- Autonomous cloud resource provisioning
- Cost-aware GPU selection
- Proper resource cleanup (no orphaned instances)
- Infrastructure reliability

---

## How to Explore

Each showcase includes:
- `README.md` - Summary and key findings
- `outputs/` or `images/` - Key files and visualizations
- Evaluation details with category scores
- Session statistics (duration, cost, turns)
- Complete file listings

## Observability

Every benchmark run captures detailed data for reproducibility and analysis:

| Data Type | Location | Contents |
|-----------|----------|----------|
| **Grading Details** | `result.json` | Category scores, evidence, reasoning |
| **Session Stats** | `result.json` | Turns, duration, cost by model |
| **Files Created** | `result.json` | Complete list of all outputs |
| **Workspace Artifacts** | run workspace | Actual deliverables (CIF, JSON, MD) |
| **Conversation Transcript** | `transcript.md` | Step-by-step actions (when available) |

### Example: What You Can Learn

From `result.json` you can see:
- **How long** the agent worked (e.g., 37 turns over 22 minutes)
- **How much** it cost (e.g., $4.14 across 3 models)
- **What it created** (e.g., 123 files including 88 CIF structures)
- **Where it excelled** (e.g., "Comprehensive MLIP screening")
- **Where it struggled** (e.g., "DFT validation not executed")

## Running Your Own

These showcases came from the original (v1) evaluation suite, preserved here as
demonstrations of the agent's capabilities. The current benchmark is **Caliber**
(`caliber/`):

```bash
python benchmark/suite/native_sweep.py --reps 3 --lanes 3
```

## Benchmark Scores Explained

| Score | Meaning |
|-------|---------|
| 90-100 | Exceptional - exceeds expectations |
| 70-89 | Good - solid scientific work |
| 50-69 | Adequate - meets basic requirements |
| <50 | Needs improvement |

All showcases achieved **passing scores** (threshold: 40) on first attempt.
