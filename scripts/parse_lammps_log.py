#!/usr/bin/env python3
"""Parse LAMMPS log files and extract thermodynamic data."""

import sys
import json
import argparse
from pathlib import Path


def parse_lammps_log(logfile: str) -> dict:
    """Parse LAMMPS log file for thermodynamic data.

    Args:
        logfile: Path to LAMMPS log file

    Returns:
        Dictionary with headers, data, and metadata
    """
    data = []
    headers = None
    runs = []
    current_run = None
    in_run = False

    with open(logfile, 'r') as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        line = line.strip()

        # Detect start of thermo output
        if line.startswith('Step'):
            headers = line.split()
            in_run = True
            current_run = {'headers': headers, 'data': []}
            continue

        # Detect end of thermo output
        if in_run:
            if line.startswith('Loop') or line.startswith('ERROR') or not line:
                if current_run and current_run['data']:
                    runs.append(current_run)
                in_run = False
                current_run = None
                continue

            # Try to parse data line
            try:
                values = [float(x) for x in line.split()]
                if len(values) == len(headers):
                    current_run['data'].append(values)
            except ValueError:
                # Not a data line, end of run
                if current_run and current_run['data']:
                    runs.append(current_run)
                in_run = False
                current_run = None

    # Handle case where file ends during a run
    if current_run and current_run['data']:
        runs.append(current_run)

    # Combine all runs
    if runs:
        all_headers = runs[0]['headers']
        all_data = []
        for run in runs:
            if run['headers'] == all_headers:
                all_data.extend(run['data'])

        return {
            'headers': all_headers,
            'data': all_data,
            'n_runs': len(runs),
            'n_steps': len(all_data)
        }

    return {'headers': [], 'data': [], 'n_runs': 0, 'n_steps': 0}


def compute_statistics(result: dict) -> dict:
    """Compute basic statistics for each column."""
    if not result['data']:
        return {}

    import numpy as np

    data = np.array(result['data'])
    stats = {}

    for i, header in enumerate(result['headers']):
        col = data[:, i]
        stats[header] = {
            'mean': float(np.mean(col)),
            'std': float(np.std(col)),
            'min': float(np.min(col)),
            'max': float(np.max(col))
        }

    return stats


def main():
    parser = argparse.ArgumentParser(description='Parse LAMMPS log files')
    parser.add_argument('logfile', help='LAMMPS log file to parse')
    parser.add_argument('--json', '-j', action='store_true',
                        help='Output as JSON')
    parser.add_argument('--stats', '-s', action='store_true',
                        help='Compute statistics')
    parser.add_argument('--output', '-o', help='Output file (default: stdout)')

    args = parser.parse_args()

    if not Path(args.logfile).exists():
        print(f"Error: File '{args.logfile}' not found", file=sys.stderr)
        sys.exit(1)

    result = parse_lammps_log(args.logfile)

    if args.stats:
        result['statistics'] = compute_statistics(result)

    if args.json:
        output = json.dumps(result, indent=2)
    else:
        # Pretty print
        lines = []
        lines.append(f"LAMMPS Log: {args.logfile}")
        lines.append(f"Runs: {result['n_runs']}")
        lines.append(f"Total steps: {result['n_steps']}")
        lines.append(f"Columns: {', '.join(result['headers'])}")

        if args.stats and 'statistics' in result:
            lines.append("\nStatistics:")
            for header, stats in result['statistics'].items():
                lines.append(f"  {header}:")
                lines.append(f"    mean: {stats['mean']:.6g}")
                lines.append(f"    std:  {stats['std']:.6g}")
                lines.append(f"    min:  {stats['min']:.6g}")
                lines.append(f"    max:  {stats['max']:.6g}")

        output = '\n'.join(lines)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
    else:
        print(output)


if __name__ == '__main__':
    main()
