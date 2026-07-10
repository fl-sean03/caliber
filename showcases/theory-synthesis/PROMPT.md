# Theory Synthesis Demo Prompt

## Task

Use the theory-synthesis skill to analyze current literature and generate
a research hypothesis about machine learning interatomic potentials (MLIPs).

## Specific Request

1. **Topic**: Accuracy of machine learning interatomic potentials for phonon calculations

2. **Synthesize** what the literature says about:
   - Current accuracy benchmarks for MLIP phonon predictions
   - Comparison between different MLIP architectures (MACE, CHGNet, M3GNet)
   - Known failure modes or limitations

3. **Identify** 2-3 specific research gaps that haven't been addressed

4. **Propose** computational investigations that could address these gaps

## Constraints

- Use `--quick` mode (15 papers max) for faster results (~5-10 min)
- Full mode uses 50+ papers but takes longer and costs more

## Expected Time

- Quick mode: 5-10 minutes
- Full mode: 15-30 minutes

## API Keys Required

Before running, ensure these are configured in the api_keys.donotcommit.json:
- OpenAI API key
- Mistral API key (for PDF processing)
- Semantic Scholar API key (s2_key.donotcommit.txt)
