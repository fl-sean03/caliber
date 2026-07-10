# CLAUDE.md

**Follow the instructions in ./AGENTS.md**

This file provides Claude Code-specific configuration. The primary agent context is in `AGENTS.md` (the industry standard).

---

## Claude Code-Specific Notes

### Skills Location

Skills are in `./skills/` (symlinked to `.claude/skills/` for compatibility):

```
skills/
├── compute-strategy/        # WHERE to run: backend selection, smoke-first iteration, partition routing
├── compute-validation/      # IS IT READY: verification + smoke-loop discipline before production
├── campaign-orchestration/  # HOW TO MANAGE: stateless agents over WORKFLOW.md files
├── vast-cloud/              # Vast.ai cloud GPU driver
├── lammps-simulation/       # Molecular dynamics
├── quantum-espresso/        # DFT calculations
├── literature-search/       # Paper search
├── materials-database/      # Materials Project
├── mlip-simulation/         # ML potentials
├── torch-sim/               # PyTorch-based simulation
├── data-analysis/           # Data processing
├── resource-acquisition/    # Finding files/parameters
├── iff-parameters/          # IFF force field search, export, composition
├── theory-synthesis/        # Theory/method synthesis
├── project-update/          # Project state + weekly/PI-meeting update bundles
├── ggen/                    # Generation utilities
└── archive/                 # Deprecated skills (e.g., hpc-cluster-curc, replaced by compute-strategy)
```

The compute trio (`compute-strategy`, `compute-validation`, `campaign-orchestration`) compose: strategy decides backend, validation gates production behind verification + smoke analysis, orchestration manages long-running stateful execution. Read all three when driving a non-trivial compute campaign.

### Configuration Files

| File | Purpose |
|------|---------|
| `.claude/settings.json` | Permissions, env vars, hooks |
| `.mcp.json` | MCP server configuration |
| `config.yaml` | User-specific settings |

### Available MCP Servers

- **Playwright** - Browser automation for downloads
- **Semantic Scholar** - Academic paper search
- **Filesystem** - Extended file access

### Hooks

Pre/post tool hooks are in `.claude/hooks/`:
- `validate_simulation.py` - Pre-Bash validation
- `format_output.py` - Post-Write formatting

---

## Quick Reference

### Run a Simulation

```bash
# LAMMPS
$LMP -in input.lmp

# Quantum ESPRESSO
$QE_CPU/pw.x < input.in > output.out
```

### Run Benchmarks

```bash
python benchmark/suite/native_sweep.py --reps 3 --lanes 3
```

### Verify Infrastructure

```bash
python -m pytest benchmark/scoring -q
```

---

## Examples Directory

**Check `examples/` when starting complex tasks.** It contains canonical examples of good work.

| Task Type | Example to Check |
|-----------|------------------|
| Multi-compound study | `examples/workflows/multi-compound-study.md` |
| Sparse/minimal instructions | `examples/workflows/sparse-input-task.md` |
| Need to revise approach | `examples/workflows/iterative-refinement.md` |
| Error recovery | `examples/patterns/error-recovery.md` |

**Before claiming a task complete**, compare your outputs to the example's deliverables checklist.

---

## For Full Context

See `./AGENTS.md` for:
- Scientific methodology
- Verification procedures
- Documentation standards
- Project structure
- Common sanity checks
