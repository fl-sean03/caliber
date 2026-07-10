#!/usr/bin/env python
"""
ASTA Theorizer Demo Script - Literature-Driven Theory Synthesis

This script demonstrates ASTA Theorizer's ability to:
1. Search for relevant papers via Semantic Scholar
2. Extract evidence from paper PDFs
3. Generate literature-supported scientific theories

Usage:
    python demo_theorizer.py [--quick | --full]

Options:
    --quick   Use 10 papers for faster results (~5 min)
    --full    Use 25 papers for more comprehensive analysis (~15 min) [default]

Requirements:
    - API keys configured in asta-theorizer/api_keys.donotcommit.json
    - Semantic Scholar key in asta-theorizer/s2_key.donotcommit.txt
"""

import sys
import os
import time
import json
from pathlib import Path

# Add theorizer source to path
THEORIZER_ROOT = Path.home() / "work/agents/science-agent/asta-theorizer"
sys.path.insert(0, str(THEORIZER_ROOT / "src"))


def check_api_keys():
    """Check if API keys are configured."""
    api_keys_file = THEORIZER_ROOT / "api_keys.donotcommit.json"
    s2_key_file = THEORIZER_ROOT / "s2_key.donotcommit.txt"

    issues = []

    if not api_keys_file.exists():
        issues.append(f"Missing: {api_keys_file}")
    else:
        with open(api_keys_file) as f:
            keys = json.load(f)
            for key_name in ["openai", "anthropic", "mistral"]:
                if key_name not in keys or "placeholder" in keys.get(key_name, ""):
                    issues.append(f"API key '{key_name}' is placeholder or missing")

    if not s2_key_file.exists():
        issues.append(f"Missing: {s2_key_file}")
    else:
        with open(s2_key_file) as f:
            content = f.read().strip()
            if "placeholder" in content:
                issues.append("Semantic Scholar key is placeholder")

    return issues


def format_time(seconds):
    """Format seconds as mm:ss."""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}m {secs}s"


def demo_theorizer(max_papers=25):
    """Run the theorizer demo."""
    print("=" * 60)
    print("ASTA Theorizer Demo: Literature-Driven Theory Synthesis")
    print("=" * 60)

    # Check API keys
    print("\n1. Checking API keys...")
    issues = check_api_keys()
    if issues:
        print("   ERROR: API keys not properly configured!")
        for issue in issues:
            print(f"   - {issue}")
        print("\n   Please configure your API keys:")
        print(f"   - {THEORIZER_ROOT}/api_keys.donotcommit.json")
        print(f"   - {THEORIZER_ROOT}/s2_key.donotcommit.txt")
        return False
    print("   API keys: OK")

    # Import and initialize
    print("\n2. Initializing Theorizer...")
    os.chdir(THEORIZER_ROOT)  # Need to be in theorizer dir for relative paths

    from Theorizer import Theorizer
    theorizer = Theorizer()
    print("   Theorizer initialized: OK")

    # Define the theory query
    query = """
    What factors affect the accuracy of machine learning interatomic potentials
    (MLIPs) for predicting phonon properties in materials? Specifically:
    - How do different MLIP architectures compare for phonon calculations?
    - What are the known limitations and failure modes?
    - What training data characteristics are most important for phonon accuracy?
    """

    print(f"\n3. Submitting theory query ({max_papers} papers max)...")
    print(f"   Query: {query[:100]}...")

    start_time = time.time()

    # Submit the theory query
    theorizer.submit_theory_query(
        query=query,
        max_papers_to_retrieve=max_papers,
        extraction_evaluation_year=2025,
        extraction_evaluation_month=6,
    )

    print("   Query submitted. Starting paper search and analysis...")

    # Poll for completion
    print("\n4. Processing (this may take several minutes)...")
    last_status = ""
    while theorizer.is_busy():
        time.sleep(5)  # Poll every 5 seconds

        statuses = theorizer.get_workflow_statuses()
        active = statuses.get("active_workflows", [])

        if active:
            current = active[0]
            step = current.get("current_step", "unknown")
            status = current.get("status_str", "")
            runtime = current.get("runtime_sec", 0)
            cost = current.get("cost", 0)

            status_line = f"   [{format_time(runtime)}] Step: {step}"
            if status and status != last_status:
                print(status_line)
                if status:
                    print(f"            {status}")
                last_status = status

    elapsed = time.time() - start_time
    print(f"\n   Completed in {format_time(elapsed)}")

    # Get results
    print("\n5. Retrieving generated theories...")
    statuses = theorizer.get_workflow_statuses()
    completed = statuses.get("completed_workflows", [])

    if not completed:
        print("   ERROR: No completed workflows found")
        return False

    workflow_result = completed[0]
    has_errors = workflow_result.get("has_errors", False)

    if has_errors:
        print("   ERROR: Workflow completed with errors:")
        for error in workflow_result.get("errors", []):
            print(f"   - {error}")
        return False

    # Display results
    print("\n" + "=" * 60)
    print("GENERATED THEORIES")
    print("=" * 60)

    # Get theories from theory store
    theories = theorizer.theory_store.get_all_theories()

    if not theories:
        print("\n   No theories generated.")
        return False

    for i, theory in enumerate(theories, 1):
        print(f"\n--- Theory {i}: {theory.name} ---")
        print(f"Type: {theory.type}")
        print(f"\nDescription:\n{theory.description}")

        # Print components if available
        components = theory.components
        if components:
            if "key_findings" in components:
                print("\nKey Findings:")
                for finding in components.get("key_findings", []):
                    print(f"  - {finding}")

            if "research_gaps" in components:
                print("\nResearch Gaps:")
                for gap in components.get("research_gaps", []):
                    print(f"  - {gap}")

            if "proposed_investigations" in components:
                print("\nProposed Investigations:")
                for inv in components.get("proposed_investigations", []):
                    print(f"  - {inv}")

        print(f"\nSupporting evidence: {len(theory.supporting_evidence_ids)} papers")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Papers analyzed: {max_papers}")
    print(f"Theories generated: {len(theories)}")
    print(f"Processing time: {format_time(elapsed)}")
    print(f"Total cost: ${workflow_result.get('cost', 0):.2f}")

    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)

    return True


def main():
    # Determine mode
    max_papers = 25  # default
    if len(sys.argv) > 1:
        if sys.argv[1] == "--quick":
            max_papers = 10
        elif sys.argv[1] == "--full":
            max_papers = 25

    print(f"Mode: {'quick' if max_papers == 10 else 'full'} ({max_papers} papers)")

    success = demo_theorizer(max_papers=max_papers)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
