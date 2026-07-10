---
name: theory-synthesis
description: Synthesize scientific theories from literature corpora using ASTA Theorizer. Use when asked to generate hypotheses, find research gaps, synthesize knowledge across many papers, or create literature-grounded theories for computational testing.
allowed-tools:
  - Read
  - Write
  - Bash
  - WebSearch
  - WebFetch
---

# Theory Synthesis Skill

Synthesize scientific theories from large literature corpora using the ASTA Theorizer system from Allen AI. This enables literature-driven hypothesis generation at scale.

**Trigger**: Use when asked to:
- Generate research hypotheses from literature
- Synthesize knowledge across many papers (10+)
- Identify research gaps in a field
- Create testable theories for simulation validation
- Conduct systematic literature meta-analysis

---

## Overview

ASTA Theorizer extracts structured evidence from ~100 papers and synthesizes:
- **Qualitative theories**: Trends, relationships, mechanisms
- **Quantitative laws**: Mathematical relationships with parameters
- **Research gaps**: What the literature doesn't cover

This is fundamentally different from simple literature search:

| Literature Search | Theory Synthesis |
|-------------------|------------------|
| Find individual papers | Synthesize across corpus |
| Extract specific parameters | Generate new hypotheses |
| Answer "what did paper X say?" | Answer "what does the field know?" |
| Minutes | 30-60 minutes |

---

## Installation

### Prerequisites

```bash
# Requires Python 3.12 (strict requirement)
conda create -n theorizer python=3.12 -y
conda activate theorizer

# Clone and install Theorizer
git clone https://github.com/allenai/asta-theorizer.git
cd asta-theorizer
pip install -r requirements.txt

# Clone and install PaperFinder (uses uv)
cd ..
git clone https://github.com/allenai/asta-paper-finder.git
cd asta-paper-finder
pip install uv
make sync-dev
```

### Required API Keys

Create `asta-theorizer/api_keys.donotcommit.json`:
```json
{
    "openai": "sk-...",
    "anthropic": "sk-ant-...",
    "mistral": "..."
}
```

Create `asta-theorizer/s2_key.donotcommit.txt`:
```
your-semantic-scholar-api-key
```

### Verification

```bash
conda activate theorizer
cd asta-theorizer
python -c "import sys; sys.path.insert(0, 'src'); from Theorizer import Theorizer; print('OK')"
```

### Cache Location

Theorizer cache: `~/.cache/science-agent/theorizer/`

---

## Usage Patterns

### Pattern 1: Generate Research Hypothesis

When you need hypotheses grounded in literature:

```python
from theorizer import TheoryGenerator

# Initialize
generator = TheoryGenerator(mode="accuracy")  # or "novelty"

# Generate theory from query
result = generator.synthesize(
    query="What factors affect hydrogen diffusion in palladium?",
    max_papers=50,
    output_type="quantitative"  # or "qualitative"
)

# Access results
print(result.theory)           # Synthesized theory
print(result.evidence)         # Supporting evidence from papers
print(result.confidence)       # Self-assessed confidence
print(result.gaps)             # Identified knowledge gaps
```

### Pattern 2: Research Gap Analysis

Identify what the literature doesn't cover:

```python
result = generator.synthesize(
    query="Machine learning interatomic potentials for phonon calculations",
    max_papers=100,
    focus="gaps"
)

# Returns gaps like:
# - "Few studies on MLIP phonon accuracy for ternary compounds"
# - "Limited systematic comparison of different MLIP architectures"
# - "Lack of uncertainty quantification for phonon predictions"
```

### Pattern 3: Methodology Consensus

Extract consensus methodology from multiple papers:

```python
result = generator.synthesize(
    query="Best practices for DFT calculation of battery cathode materials",
    max_papers=50,
    output_type="methodology"
)

# Returns consensus on:
# - Recommended functionals (PBE+U, HSE06)
# - K-point densities
# - Pseudopotential choices
# - Convergence criteria
```

---

## Integration with Caliber

### Workflow: Theory-to-Simulation

```
┌─────────────────────────────────────────────────────────────────┐
│  1. THEORIZER: Generate hypothesis from literature              │
│     "Hydrogen diffusion in Pd increases with temperature        │
│      following Arrhenius: D = D0 * exp(-Ea/kT)"                │
│      Ea literature range: 0.2-0.3 eV                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. AGENT: Design simulation to test hypothesis                 │
│     - Set up Pd supercell with H interstitial                  │
│     - Run MD at 300K, 400K, 500K, 600K                         │
│     - Calculate MSD and extract D(T)                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. AGENT: Validate results against theory                      │
│     - Fit D(T) to Arrhenius                                    │
│     - Extract Ea from simulation                               │
│     - Compare to literature range (0.2-0.3 eV)                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. FEEDBACK: Refine understanding                              │
│     - If match: Theory validated computationally               │
│     - If mismatch: Investigate discrepancy                     │
└─────────────────────────────────────────────────────────────────┘
```

### Example: Battery Cathode Discovery

```python
# Step 1: Generate hypotheses about unexplored cathode spaces
hypotheses = generator.synthesize(
    query="Under-explored chemical spaces for high-voltage Li-ion cathodes",
    max_papers=100,
    focus="gaps"
)

# Step 2: Agent uses hypotheses to guide screening
# hypotheses.gaps might include:
# - "Limited study of Li-V-F polyanionic compounds"
# - "Few reports on high-entropy cathode oxides"
# - "Sulfate cathodes under-investigated vs phosphates"

# Step 3: Agent screens suggested chemical spaces
# Step 4: Agent validates promising candidates
```

---

## CLI Usage

### Generate Theory

```bash
# Basic usage
python -m theorizer generate \
    --query "Effect of defects on thermal conductivity in 2D materials" \
    --papers 50 \
    --output theory.json

# With novelty focus
python -m theorizer generate \
    --query "Novel cathode materials for Li-ion batteries" \
    --papers 100 \
    --mode novelty \
    --output cathode_theory.json
```

### Start Server (for MCP integration)

```bash
# Start Theorizer server
python TheorizerServer.py --port 8080

# Server provides endpoints:
# POST /synthesize - Generate theory
# GET /status - Check job status
# GET /theories - List cached theories
```

---

## Output Format

Theorizer returns structured JSON:

```json
{
  "query": "Hydrogen diffusion in palladium",
  "theory": {
    "qualitative": "Hydrogen diffuses through Pd via octahedral interstitial sites...",
    "quantitative": "D = D0 * exp(-Ea/kT) where Ea = 0.23 ± 0.05 eV",
    "confidence": 0.85
  },
  "evidence": [
    {
      "paper_id": "10.1234/example",
      "title": "H Diffusion in Pd",
      "claim": "Ea = 0.22 eV measured by NMR",
      "relevance": 0.95
    }
  ],
  "gaps": [
    "Limited data on H diffusion at grain boundaries",
    "Few studies on H diffusion in Pd alloys"
  ],
  "metadata": {
    "papers_analyzed": 67,
    "generation_time_minutes": 42
  }
}
```

---

## Performance Considerations

### Time and Cost

| Papers | Time | Estimated Cost |
|--------|------|----------------|
| 25 | ~15 min | ~$2-5 |
| 50 | ~30 min | ~$5-10 |
| 100 | ~60 min | ~$10-20 |

**Recommendations**:
- Start with 25-50 papers for exploratory queries
- Use 100 papers for comprehensive synthesis
- Cache results - theories are reusable
- Set API spending limits

### When to Use

**Good use cases**:
- Generating hypotheses for T10/T11 benchmarks
- Literature review for novel material discovery
- Finding consensus parameters across field
- Identifying research gaps to fill

**Not ideal for**:
- Finding a single specific parameter (use literature-search)
- Quick fact lookup (too slow)
- Narrow/specialized queries with few papers

---

## Integration Status

| Integration | Status | Notes |
|-------------|--------|-------|
| CLI usage | Ready | Manual invocation |
| MCP server | Planned | For agent integration |
| Benchmark T9+ | Ready | New benchmarks use this |
| Caching | Supported | Reuse expensive queries |

---

## Troubleshooting

### Common Issues

**"No papers found"**
- Query too specific - broaden terms
- Check Semantic Scholar API status
- Verify S2_API_KEY is set

**"Theory generation failed"**
- Check LLM API keys
- Reduce max_papers if hitting context limits
- Try different LLM (Anthropic vs OpenAI)

**"Slow generation"**
- Normal - 30-60 min for 100 papers
- PDF OCR is the bottleneck
- Consider caching results

### Validation

Always validate Theorizer output:
1. Spot-check cited papers exist
2. Verify key claims against source
3. Cross-reference quantitative values
4. Treat as hypothesis, not fact

---

## Resources

- **ASTA Theorizer**: https://github.com/allenai/asta-theorizer
- **Paper**: https://arxiv.org/abs/2406.06592 ("Theorizer: Literature-Driven Scientific Discovery")
- **Semantic Scholar API**: https://api.semanticscholar.org/
- **ASTA Paper Finder**: https://github.com/allenai/asta-paper-finder
- **Showcase Demo**: `showcases/theory-synthesis/workspace/demo_theorizer.py`
