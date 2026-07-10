#!/usr/bin/env python3
"""
Pre-execution validation hook for simulation commands.

Validates commands before execution to prevent:
- Dangerous operations
- Invalid file paths
- Resource-intensive runs without warning
"""

import json
import re
import subprocess
import sys
from pathlib import Path


def validate_command(command: str) -> tuple:
    """
    Validate a command before execution.

    Returns:
        (is_valid, warning_message)
    """
    warnings = []
    errors = []

    # Check for dangerous patterns
    dangerous_patterns = [
        (r'rm\s+-rf\s+/', "Dangerous: Recursive delete from root"),
        (r'>\s*/dev/(?!null\b|stdout\b|stderr\b|tty\b|fd/)', "Dangerous: Writing to device"),
        (r'dd\s+if=', "Dangerous: Direct disk access"),
        (r'mkfs', "Dangerous: Filesystem creation"),
    ]

    for pattern, message in dangerous_patterns:
        if re.search(pattern, command):
            errors.append(message)

    # Check for long LAMMPS runs
    if 'lmp' in command:
        # Check for very long runs
        run_match = re.search(r'-var\s+nsteps\s+(\d+)', command)
        if run_match:
            nsteps = int(run_match.group(1))
            if nsteps > 1000000:
                warnings.append(f"Long run detected: {nsteps} steps. Consider using background execution.")

    # Check for QE runs without output redirect
    if 'pw.x' in command:
        if '>' not in command and 'tee' not in command:
            warnings.append("QE output not redirected. Consider: pw.x < input > output")

    # Deterministic input lint (2026-01-17 CRASH class; see
    # a 2026-01 crash postmortem). Extract `< input` / `-in input`
    # and lint it; a BLOCK becomes an error (hook exit 2).
    m = re.search(r'(?:pw\.x[^|;&]*<\s*(\S+))|(?:\blmp\b[^|;&]*-in\s+(\S+))', command)
    if m:
        input_file = m.group(1) or m.group(2)
        kind = 'qe' if m.group(1) else 'lammps'
        lint = Path(__file__).resolve().parent.parent.parent / 'scripts' / 'lint_sim_input.py'
        if lint.exists() and Path(input_file).exists():
            r = subprocess.run([sys.executable, str(lint), kind, input_file],
                               capture_output=True, text=True, timeout=10)
            if r.returncode == 1:
                errors.append(f"Input lint BLOCK: {r.stdout.strip()}")

    return errors, warnings


def main():
    try:
        input_data = json.load(sys.stdin)
        tool_name = input_data.get('tool_name', '')
        tool_input = input_data.get('tool_input', {})

        # Only validate Bash commands
        if tool_name != 'Bash':
            sys.exit(0)

        command = tool_input.get('command', '')
        errors, warnings = validate_command(command)

        # Print warnings (non-blocking)
        for warning in warnings:
            print(f"WARNING: {warning}", file=sys.stderr)

        # Block on errors
        if errors:
            for error in errors:
                print(f"BLOCKED: {error}", file=sys.stderr)
            sys.exit(2)

        sys.exit(0)

    except Exception as e:
        # Don't block on validation errors
        print(f"Validation error (non-blocking): {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == '__main__':
    main()
