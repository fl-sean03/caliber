# OpenAI Codex Configuration

Codex automatically discovers `AGENTS.md` in the project root.

## Setup

1. Install Codex CLI:
```bash
npm i -g @openai/codex
# or
brew install --cask codex
```

2. Run from project root:
```bash
codex
```

Codex will automatically read:
- `AGENTS.md` - Primary context
- `skills/*/SKILL.md` - Available skills (reference in prompts)

## Configuration

Codex config is in `~/.codex/config.toml`. See [Codex docs](https://developers.openai.com/codex/config-advanced/).

## Environment Variables

Set in your shell or `.env`:
```bash
export LMP=/path/to/lammps/bin/lmp
export QE_CPU=/path/to/qe/bin
export MP_API_KEY=your_key
```

## Usage

```bash
# Interactive mode
codex

# Auto-edit mode (for benchmarks)
codex --auto-edit -p "Calculate the lattice constant of copper with the Mishin EAM potential"

# Full auto mode
codex --full-auto -p "Calculate argon diffusion coefficient"
```

## Skills

Reference skills in your prompts:
```
Read skills/lammps-simulation/SKILL.md and then calculate the diffusion coefficient of liquid argon.
```
