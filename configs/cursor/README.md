# Cursor Configuration

Cursor automatically discovers `AGENTS.md` and `.cursorrules` in the project root.

## Setup

1. Install Cursor from [cursor.com](https://cursor.com)

2. Open project in Cursor:
```bash
cursor .
```

3. Copy rules to project root (optional, AGENTS.md is sufficient):
```bash
cp configs/cursor/.cursorrules .cursorrules
```

## Configuration

Cursor reads:
- `AGENTS.md` - Primary context (auto-discovered)
- `.cursorrules` - Additional rules (optional)

## Environment Variables

Set in your shell before launching Cursor:
```bash
export LMP=/path/to/lammps/bin/lmp
export QE_CPU=/path/to/qe/bin
export MP_API_KEY=your_key
```

## Usage

1. Open a file in the project
2. Use Cmd+K (Mac) or Ctrl+K (Windows/Linux) for inline edits
3. Use Cmd+L for chat with full context

## Skills

Reference skills in your prompts:
```
@skills/lammps-simulation/SKILL.md Calculate the diffusion coefficient of liquid argon.
```
