# Contributing to Caliber

Welcome! This document contains everything you need to know to contribute effectively.

## Table of Contents
- [Project Philosophy](#project-philosophy)
- [Development Setup](#development-setup)
- [Architecture Overview](#architecture-overview)
- [Developer Tips & Tricks](#developer-tips--tricks)
- [Common Pitfalls](#common-pitfalls)
- [Benchmark Development](#benchmark-development)
- [Testing Your Changes](#testing-your-changes)

---

## Project Philosophy

### Core Thesis

> **The best agentic system is the simplest one that works.**

We don't build complex orchestration. We give Claude:
1. Clear context (CLAUDE.md, skills)
2. Direct tool access (can run simulations, not just plan them)
3. Fast feedback (know when something fails)
4. Domain knowledge (what parameters to use, what's reasonable)

### What Makes This Different

Traditional approaches try to constrain and orchestrate AI agents. We take the opposite approach:

- **Trust the model** - Claude already knows computational science; we just give it tools
- **Minimal scaffolding** - Skills are just markdown files, not complex code
- **Fail fast, iterate** - Benchmarks reveal what's missing; we fix prompts, not code
- **Research-grade output** - The agent should produce work a PhD would accept

### Intelligence as Scaffolding

See `docs/DESIGN_PHILOSOPHY.md` for the full explanation. The key principle:

> **The agent IS the scaffolding.**

We don't build orchestration layers, mode selectors, or state machines. We provide:
- **Knowledge** (AGENTS.md, skills)
- **Tools** (LAMMPS, QE, MLIPs)
- **Tests** (benchmarks)

The LLM's intelligence does the rest. When extending this project:

1. **If you want to change behavior → Edit AGENTS.md or skills**
2. **If you want to add capability → Write a new skill**
3. **If you want to test → Write a benchmark**
4. **If you think you need code → Ask if knowledge would work instead**

This isn't laziness—it's a deliberate architecture. Code scaffolding is brittle and constraining. Knowledge scaffolding is flexible and empowering.

---

## Development Setup

### Prerequisites

```bash
# Required
- Claude Code CLI (subscription)
- Python 3.10+
- LAMMPS (GPU recommended)

# Optional
- Quantum ESPRESSO (for DFT benchmarks)
- HPC cluster access (for T5-T7 benchmarks)
- ML packages: mace-torch, matgl, chgnet (for T8+ benchmarks)
```

### Quick Start

```bash
git clone https://github.com/fl-sean03/caliber.git
cd caliber

# Configure
cp config.example.yaml config.yaml
cp .claude/settings.json.example .claude/settings.json
cp .mcp.json.example .mcp.json

# Edit configs with your paths/keys
vim config.yaml

# Verify
python -m pytest benchmark/scoring -q

# Sweep a model across the benchmark on its native harness
python benchmark/suite/native_sweep.py --reps 3 --lanes 3
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      CLAUDE.md                              │
│         (Researcher persona, methodology, mindset)          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   .claude/skills/                           │
│  Each skill = SKILL.md file with:                          │
│  - When to use it                                          │
│  - Tool locations and commands                             │
│  - Domain-specific knowledge                               │
│  - Examples and patterns                                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       caliber/  (the benchmark)             │
│  harnesses/  - per-model native runners (native-claude/...) │
│  scoring/    - mechanical anchors ⊕ frozen judge, provenance │
│  suite/      - task manifests + sweep/audit tooling         │
│  METHODOLOGY.md - three axes, oracle-escrow, horizon        │
└─────────────────────────────────────────────────────────────┘
        Sealed answer keys live OUTSIDE this repo (private store),
        injected only at grade time — public methodology, private answers.
```

### Key Files

| File | Purpose | When to Edit |
|------|---------|--------------|
| `CLAUDE.md` | Agent persona and methodology | Changing core behavior |
| `.claude/skills/*.md` | Domain-specific knowledge | Adding capabilities |
| `.claude/settings.json` | Permissions, env vars | New tools/paths |
| `benchmark/suite/<gen>/MANIFEST.json` | Public task manifests (no answers) | Proposing tasks |
| `benchmark/harnesses/<name>/` | Per-model native runners | New model/harness |
| `benchmark/scoring/` | Scoring, judge, evidence, provenance | Changing grading |

---

## Developer Tips & Tricks

### Insight #1: Prompt Engineering > Code

Most "bugs" are actually unclear prompts. Before writing code, try:
1. Adding explicit instructions to the benchmark prompt
2. Adding examples to the skill file
3. Adding checklists the agent must complete

**Example fix that worked:**
```yaml
# Before (agent stopped after research):
prompt: |
  Calculate the melting temperature of copper.

# After (agent completed full workflow):
prompt: |
  **CRITICAL INSTRUCTIONS:**
  1. You are EXECUTING this task, not just planning it
  2. You must CREATE all output files listed below
  3. Use TodoWrite to track your checklist

  Calculate the melting temperature of copper.

  **Required outputs:**
  - [ ] simulation files created
  - [ ] simulation executed
  - [ ] results analyzed
  - [ ] report.md written
```

### Insight #2: The Agent is Smart, Just Misinterprets Scope

When benchmarks fail, it's usually because the agent:
- Thought "research and recommend" was the task (vs. "execute end-to-end")
- Optimized for efficiency (ran locally instead of HPC)
- Stopped at a reasonable checkpoint (after setup, before execution)

**Fix pattern:** Be explicit about what "done" means.

### Insight #3: LLM-as-Judge Grading is Powerful

The `llm_grader.py` spawns another Claude agent to evaluate results. This catches:
- Scientific errors a regex can't find
- Missing citations and methodology
- Physically unreasonable results

**Tip:** Grading prompts are in `llm_grader.py` around line 78. Customize for new domains.

### Insight #4: Skills are Just Context Injection

A skill file (`.claude/skills/*/SKILL.md`) is just markdown that gets injected when the agent invokes that skill. No code required.

**To add a new capability:**
1. Create `.claude/skills/new-skill/SKILL.md`
2. Write what the agent needs to know
3. Include examples and common patterns
4. That's it - the skill is now available

### Insight #5: Environment Variables for Portability

All paths should use environment variables:
```bash
# In .claude/settings.json
"env": {
  "LMP": "${LAMMPS_PATH:-/usr/local/bin/lmp}",
  "QE_CPU": "${QE_PATH:-/usr/local/qe/bin}"
}
```

The agent then uses `$LMP` in commands, making the system portable.

---

## Common Pitfalls

### Pitfall #1: Hardcoding Paths

**Wrong:**
```markdown
Run LAMMPS at `/home/myuser/lammps/bin/lmp`
```

**Right:**
```markdown
Run LAMMPS using `$LMP` (configured in settings.json)
```

### Pitfall #2: Vague Success Criteria

**Wrong:**
```yaml
prompt: |
  Analyze the simulation results.
```

**Right:**
```yaml
prompt: |
  Analyze the simulation results. Create:
  1. analysis.py - script that calculates diffusion coefficient
  2. results.txt - D value with units and uncertainty
  3. comparison.md - compare to literature value with citation
```

### Pitfall #3: Not Testing on Real Infrastructure

HPC benchmarks (T5-T7) require actual cluster access. The agent will find creative workarounds (run locally) if HPC isn't available. This isn't wrong - it's smart - but it bypasses what you're testing.

**Fix:** Add explicit requirements:
```yaml
prompt: |
  **CRITICAL: HPC EXECUTION REQUIRED**
  You MUST execute on the HPC cluster, NOT locally.
```

### Pitfall #4: Expecting Deterministic Output

The agent may:
- Use different file names
- Choose alternative methods
- Produce results in different formats

**Fix:** Grade on outcomes, not exact outputs:
```yaml
grading:
  - name: scientific_accuracy
    criteria:
      - Result within 10% of literature value
      - Method is physically appropriate
      - Sources are cited
```

---

## Contributing to Caliber (the benchmark)

Caliber grades autonomous materials-science agents on three axes (correctness gate ×
pass^k × cost-efficiency). **Public methodology, private answers:** task prompts and
reporting keys are public (`benchmark/suite/<name>/MANIFEST.json`); the sealed
reference values, tolerances, and grading keys live in a separate private store and are
never committed here.

### Proposing a task
Open an issue with: the physical quantity, the difficulty **horizon** it targets
(H1 trivial → H6+ frontier reproduction/discovery; see `benchmark/METHODOLOGY.md`), the
reporting keys the agent must surface, and how ground truth is obtained (the grader
computes a high-compute reference — oracle-escrow — not the agent's own numbers). Accepted
tasks are sealed by a maintainer: the prompt + keys land in a public MANIFEST, the answer
and tolerance go to the private store.

### Task design principles
1. **One horizon, cleanly.** A task's difficulty comes from its coupled-stage count, not
   from combining unrelated physics.
2. **Oracle-gradeable.** There must be a defensible high-compute reference and a tolerance
   set to that reference's own uncertainty (never a global epsilon).
3. **Grade observable outcomes, not methods.** Multiple valid approaches should pass.
4. **Contamination-aware.** Prefer parameterized families instantiated fresh per
   fresh; never leak the answer through the prompt, reporting keys, or provided files.

### Contributing a harness or skill
- **Harness** (new model/vendor): add `benchmark/harnesses/<name>/`; every run records
  `harness:{name,version,config_hash}` provenance.
- **Skill** (agent capability): add `skills/<name>/SKILL.md`. The capability layer is
  versioned independently of the benchmark.

## Testing your changes

```bash
# scoring / evidence / provenance tests
python -m pytest benchmark/scoring -q

# sweep a model across the benchmark on its native harness
python benchmark/suite/native_sweep.py --reps 3 --lanes 3

# audit a completed run (wake pattern, cost anatomy, artifact integrity)
python benchmark/suite/native_audit.py <run_dir> --brief
```

Before submitting a PR: run the scoring tests, update `ROADMAP.md` if you completed a
roadmap item, and ensure no hardcoded local paths, secrets, or sealed answers leaked in.

## Questions?

- Check `docs/` for detailed guides
- See `ROADMAP.md` for what we're building toward

Welcome to the project!
