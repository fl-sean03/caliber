# Aider Configuration

Aider uses `.aider.conf.yml` for configuration.

## Setup

1. Install Aider:
```bash
pip install aider-chat
```

2. Copy config to project root:
```bash
cp configs/aider/.aider.conf.yml .aider.conf.yml
```

3. Run from project root:
```bash
aider
```

## Configuration

The `.aider.conf.yml` file configures:
- Auto-loading of `AGENTS.md` context
- Available skills as read-only files
- Model settings

## Environment Variables

Set in your shell or `.env`:
```bash
export OPENAI_API_KEY=your_key  # or ANTHROPIC_API_KEY
export LMP=/path/to/lammps/bin/lmp
export QE_CPU=/path/to/qe/bin
export MP_API_KEY=your_materials_project_key
```

## Usage

```bash
# Interactive mode
aider

# With specific model
aider --model claude-3-5-sonnet

# With message
aider --message "Calculate argon diffusion coefficient"
```

## Skills

Skills are auto-loaded via `.aider.conf.yml`. Reference them in conversation:
```
Using the LAMMPS skill, calculate the diffusion coefficient of liquid argon.
```
