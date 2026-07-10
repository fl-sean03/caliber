#!/usr/bin/env python3
"""
Post-execution hook for formatting and logging.

- Logs simulation outputs
- Formats Python files if modified
- Captures metrics for benchmarking
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def log_operation(tool_name: str, file_path: str, success: bool):
    """Log operation to session log."""
    log_dir = Path(os.environ.get('CLAUDE_PROJECT_DIR', '.')) / 'logs'
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / 'operations.log'

    timestamp = datetime.now().isoformat()
    status = "SUCCESS" if success else "FAILURE"

    with open(log_file, 'a') as f:
        f.write(f"{timestamp} | {status} | {tool_name} | {file_path}\n")


def format_file(file_path: str):
    """Format file if it's a Python or config file."""
    if not os.path.exists(file_path):
        return

    try:
        if file_path.endswith('.py'):
            # Try to format with black (non-blocking)
            subprocess.run(
                ['black', '--quiet', file_path],
                capture_output=True,
                timeout=30
            )
    except Exception:
        pass  # Non-blocking


def main():
    try:
        input_data = json.load(sys.stdin)
        tool_name = input_data.get('tool_name', '')
        tool_input = input_data.get('tool_input', {})
        tool_response = input_data.get('tool_response', {})

        # Get file path if applicable
        file_path = tool_input.get('file_path', '')

        # Check if operation succeeded
        exit_code = tool_response.get('exit_code', 0)
        success = exit_code == 0 if exit_code is not None else True

        # Log the operation
        if file_path:
            log_operation(tool_name, file_path, success)

        # Format files after Write/Edit
        if tool_name in ('Write', 'Edit') and file_path and success:
            format_file(file_path)

        sys.exit(0)

    except Exception as e:
        # Non-blocking
        sys.exit(0)


if __name__ == '__main__':
    main()
