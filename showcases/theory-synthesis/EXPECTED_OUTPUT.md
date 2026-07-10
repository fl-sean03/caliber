# Expected Output: Theory Synthesis

## Success Criteria

The demo should produce:

### 1. Theory Statement
A coherent 2-3 paragraph synthesis of what literature says about the topic,
with specific citations to papers.

Example structure:
```
Machine learning interatomic potentials have shown remarkable accuracy for
predicting phonon dispersions in simple systems [Paper1, Paper2]. However,
systematic benchmarks reveal that accuracy degrades for [specific cases]...
```

### 2. Research Gaps
2-3 specific, actionable gaps identified from the literature:

Example:
```
Gap 1: No systematic comparison of MLIP phonon accuracy across different
       crystal symmetries (cubic vs hexagonal vs monoclinic)

Gap 2: Limited understanding of how training data coverage affects
       phonon prediction at Brillouin zone boundaries
```

### 3. Proposed Investigations
Concrete computational experiments to address the gaps:

Example:
```
Investigation 1: Benchmark MACE, CHGNet, and M3GNet on a curated set of
                 50 compounds spanning all crystal systems, comparing
                 phonon dispersions against DFT references
```

### 4. Metadata
- Number of papers analyzed
- Key citations
- Processing time

## Performance Benchmarks

| Mode | Papers | Time | Cost (approx) |
|------|--------|------|---------------|
| Quick | 15 | 5-10 min | ~$0.50 |
| Full | 50+ | 15-30 min | ~$2.00 |

## Common Issues

1. **API key errors**: Check api_keys.donotcommit.json format
2. **S2 rate limiting**: Use S2_API_KEY for higher limits
3. **Timeout**: Some papers may fail OCR, this is normal

## Sample Output (Quick Mode)

```
=== ASTA Theorizer Demo ===

Topic: MLIP phonon calculation accuracy

Analyzing literature... (15 papers)
- [1/15] Retrieving: "Machine learning potentials phonon..."
- [2/15] Processing: "Benchmark study of neural network..."
...

=== Generated Theory ===

[2-3 paragraph synthesis with citations]

=== Research Gaps ===

1. [Gap description]
2. [Gap description]

=== Proposed Investigations ===

1. [Investigation description]
2. [Investigation description]

=== Metadata ===
Papers analyzed: 15
Processing time: 7m 23s
Key citations: [list]
```
