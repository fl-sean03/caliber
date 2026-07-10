# Caliber

> Autonomous AI research agents for computational materials science — and the benchmark
> that proves what they can do.

[![CI](https://github.com/fl-sean03/caliber/actions/workflows/ci.yml/badge.svg)](https://github.com/fl-sean03/caliber/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Agents](https://img.shields.io/badge/agents-Claude%20Code%20%7C%20Aider%20%7C%20Cursor-8A2BE2.svg)](#supported-agents)

Caliber is one project with two tightly-coupled halves:

- **The capability core** (`skills/`, `AGENTS.md`) — a portable layer that turns a coding
  agent into an autonomous computational researcher: it plans methodology, sources
  parameters, runs and verifies DFT / MD / ML-potential calculations, and executes
  long-horizon campaigns durably. Rides on any modern coding agent.
- **The benchmark** (`benchmark/`) — a measurement instrument for such agents, graded on
  real research outcomes against sealed high-compute reference answers. **Public
  methodology, private answers.**

The unit of work is a *research outcome* — a converged calculation, a verified property, a
tested hypothesis — never a chat reply.

*(Formerly published as the Agentic Science Worker; that repository is archived and all
development continues here.)*

---

## Contents

- [The benchmark](#the-benchmark)
- [The capability core](#the-capability-core)
- [How it works](#how-it-works)
- [Supported agents](#supported-agents)
- [Quick start](#quick-start)
- [Skills](#skills)
- [Repository structure](#repository-structure)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Citing](#citing)
- [License](#license)

## The benchmark

Every run is scored on **three orthogonal axes**, because a frontier agent can be
correct-but-unreliable or correct-but-ruinously-expensive:

| Axis | What it measures |
|---|---|
| **Correctness gate** | Load-bearing physical quantities land inside sealed tolerances, checked against a **high-compute reference the grader computes** (oracle-escrow). Mechanical, all-or-nothing; a process judge can never overturn it. |
| **Reliability — pass^k** | The task is run *k* independent times; we report the probability the agent passes **all** *k* trials — not one lucky run. |
| **Cost-efficiency** | Dollars and tokens **per correct solution**, on an accuracy-vs-cost Pareto frontier. |

Difficulty is a **dial, not a bar**: tasks sit on a coupled-stage *horizon* from H1 (a
single property calculation) to H6+ (end-to-end paper reproduction, bounded discovery),
and the headline metric is the stage count at which pass-rate crosses 50% — a scale that
moves as models improve rather than saturating.

- **[benchmark/METHODOLOGY.md](benchmark/METHODOLOGY.md)** — scoring, oracle-escrow
  grading, the difficulty horizon, contamination defenses
- **[benchmark/TASK_VERSIONING.md](benchmark/TASK_VERSIONING.md)** — per-task `N-X`
  versioning + named generations
- **[benchmark/LEADERBOARD.md](benchmark/LEADERBOARD.md)** — frozen-generation entries
  only; empty until generation 2026.2 freezes

Each model is measured through its **own native harness** (`benchmark/harnesses/`),
recorded per-run as `harness:{name,version,config_hash}`. Sealed answers, tolerances,
oracles, and the held-out verification slate live in a separate private repository
(`caliber-private`) — never here.

## The capability core

- **Novel materials discovery** — autonomously proposed and screened Li-ion cathode
  candidates, including Li₂Ni(PO₄)(SO₄) at ~5.1 V.
- **Cross-modal reasoning** — determined a crystal structure from an XRD pattern using
  first-principles methods.
- **Durable long-horizon execution** — launches, detaches, and harvests multi-hour DFT/MD
  campaigns that outlive a single agent turn, resuming cleanly across interruptions.
- **Verifiable results** — every reported value is anchored to the exact inputs that
  produced it.
- **Cloud burst** — full VAST.ai GPU lifecycle for overflow compute.

See it in action: **[Showcases »](showcases/)**

## How it works

```
┌──────────────────────────────────────────────────────────────┐
│                         Coding Agent                         │
│         Claude Code  ·  Aider  ·  Cursor  ·  Codex           │
│      AGENTS.md defines researcher behavior & methodology     │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                            Skills                            │
│   simulation · DFT · MLIP · literature · databases · data    │
│   compute strategy · long-compute · campaign orchestration   │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                        External Tools                        │
│  LAMMPS · Quantum ESPRESSO · MACE/CHGNet/M3GNet · VAST · Web  │
└──────────────────────────────────────────────────────────────┘
```

The agent reads `AGENTS.md` as its primary context, then composes **skills** —
self-contained capability modules (`skills/<name>/SKILL.md`) — to plan and execute.
Long-running work is handled by a durable execution discipline: jobs are detached so they
survive a turn ending, their state lives in files, and the agent is woken to harvest
results. Everything the agent claims is recorded so it can be walked back to its inputs.

## Supported agents

| Agent | Status | Configuration |
|-------|--------|---------------|
| [Claude Code](https://claude.com/claude-code) | Full support | `AGENTS.md`, `.claude/` |
| [Aider](https://aider.chat) | Full support | `AGENTS.md`, `configs/aider/` |
| [Cursor](https://cursor.com) | Full support | `AGENTS.md`, `.cursorrules` |
| [OpenAI Codex](https://openai.com/codex) | Planned | `AGENTS.md` |

All agents read [`AGENTS.md`](AGENTS.md) — the [industry-standard](https://agents.md)
agent context file — as their primary instructions.

## Quick start

### Prerequisites

- A supported coding agent (Claude Code, Aider, or Cursor)
- Python 3.10+
- The `science-tools` conda environment: `conda env create -f environments/science-tools.yml`
- [LAMMPS](https://www.lammps.org/) (GPU build recommended) for molecular dynamics
- [Quantum ESPRESSO](https://www.quantum-espresso.org/) (optional) for DFT
- A [Materials Project](https://next-gen.materialsproject.org/api) API key

### Installation

```bash
git clone https://github.com/fl-sean03/caliber.git
cd caliber

# copy and fill in local configuration (paths + API keys stay out of git)
cp config.example.yaml config.yaml
cp .claude/settings.json.example .claude/settings.json
cp .mcp.json.example .mcp.json
```

Verify the setup:

```bash
python -m pytest benchmark/scoring -q     # scoring/evidence/provenance tests
```

### Run the agent

```bash
claude                      # Claude Code
aider --read AGENTS.md      # Aider
cursor .                    # Cursor
```

Example prompts:

```
Calculate the self-diffusion coefficient of liquid argon at 94 K.
Find the lattice constant of copper using the Mishin EAM potential.
Compute the band structure of silicon.
```

### Run the benchmark

```bash
# sweep a model across the sealed task set on its native harness
python benchmark/suite/native_sweep.py --reps 3 --lanes 3

# audit a completed run (wake pattern, cost anatomy, artifact integrity)
python benchmark/suite/native_audit.py <run_dir> --brief
```

Task prompts and reporting keys are public in
[`benchmark/suite/batch1/MANIFEST.json`](benchmark/suite/batch1/MANIFEST.json); grading
requires access to the sealed key store.

## Skills

Skills are self-contained capability modules under [`skills/`](skills/). Each has a
`SKILL.md` the agent reads on demand.

| Domain | Skills |
|--------|--------|
| Simulation | `lammps-simulation`, `quantum-espresso`, `mlip-simulation`, `torch-sim` |
| Compute discipline | `compute-strategy`, `compute-validation`, `long-compute`, `campaign-orchestration` |
| Knowledge | `literature-search`, `materials-database`, `iff-parameters`, `theory-synthesis` |
| Execution | `vast-cloud`, `resource-acquisition`, `data-analysis` |

The four compute-discipline skills compose: **strategy** picks the backend, **validation**
gates production behind smoke tests, **long-compute** detaches jobs that outlive a turn,
and **campaign-orchestration** manages long-running stateful execution.

## Repository structure

```
caliber/
├── AGENTS.md            # primary agent context (methodology, conventions)
├── skills/              # capability modules (SKILL.md each) — the capability core
├── benchmark/           # the benchmark
│   ├── METHODOLOGY.md   # three-axis scoring, oracle-escrow grading, difficulty horizon
│   ├── harnesses/       # per-model native runners (native-claude/; more added over time)
│   ├── scoring/         # scoring, frozen judge, evidence store, provenance graph
│   └── suite/           # versioned task generations (batch1/, ...) + sweep/audit tooling
├── examples/            # canonical worked examples
├── showcases/           # capability demonstrations with full write-ups
├── environments/        # conda environment specs
├── configs/             # per-agent configuration (aider, cursor, codex)
├── templates/           # scaffolding for new tasks/skills
├── scripts/             # utilities
└── tests/               # tests
```

Sealed benchmark answers live in a separate private repository, never here.

## Roadmap

See [ROADMAP.md](ROADMAP.md). In short: benchmark generation 2026.2 (oracle-escrowed,
procedurally-generated task families reaching multi-day reproduction), environment sealing
for graded runs, and deeper durable execution — where reliability and cost, not one-shot
correctness, are the real frontier.

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for how skills,
benchmark tasks, and harnesses are structured. Please open an issue to discuss substantial
changes first.

## Citing

If you use Caliber in academic work, please cite it (see [CITATION.cff](CITATION.cff)):

```bibtex
@software{florez_caliber_2026,
  author  = {Florez, Sean},
  title   = {Caliber: autonomous computational materials science agents and the
             benchmark that measures them},
  year    = {2026},
  url     = {https://github.com/fl-sean03/caliber},
  license = {MIT}
}
```

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgments

Built on the shoulders of the open computational-materials stack: LAMMPS, Quantum
ESPRESSO, ASE, pymatgen, MACE, CHGNet, M3GNet, and the Materials Project.
