# Tool: <tool-name>

One-line description: what it does, what version this page covers.

> Read this page when analyzing a smoke run produced by <tool-name>. Pairs with `workflows/smoke-analysis.md` (the framework) — this page tells you which files to read, which numbers to extract, and which thresholds matter.

---

## Diagnostic interfaces

What files / streams the tool produces. For each, what kind of signal it carries.

| File or stream | What's in it | Read with | Best for |
|---|---|---|---|
| | | | |

State *exactly* how to find each. Naming conventions, paths, etc.

## Key log/output patterns

The line types or output structures the agent should grep / parse for. Show 2-5 example lines verbatim.

```
<example log line>
```

Annotate which fields are what. Note variations across versions if relevant.

## Signal extraction recipes

Concrete recipes for each of the four signal categories from `workflows/smoke-analysis.md`.

### A. Physical / scientific observables

For each domain-relevant observable: a snippet that extracts it (`grep`, `awk`, Python with the tool's library), an example of what comes out, and thresholds for green/yellow/red status.

### B. Computational observables

Throughput (units appropriate to the tool: ns/day, samples/sec, etc.), memory, step-time variance, output write success.

**Reference benchmarks** for typical hardware: a small table of "atom count / dataset size → expected throughput on A100/RTX-4090/etc."

### C. Risk indicators

Tool-specific predictors of failure modes. Examples of what to extract and what crossing thresholds means for production behavior.

### D. Reproducibility check

Two-smoke comparison snippet for this tool. Tolerances appropriate to the tool's stochasticity.

## Tool-specific failure modes & how smoke surfaces them

| Failure mode | Manifestation in smoke | What to extract |
|---|---|---|
| | | |

Catalog known patterns. The agent reads this to decide what to look for. Update as new patterns are discovered.

## Standard smoke recipes

How to reduce a production config / script to a smoke variant. Keep the recipe self-contained.

### Recipe 1: <name>

```bash
# Show how to derive smoke from production
sed -e '...' production_config > smoke_config
```

State what's reduced (numsteps, dataset size, epochs, etc.) and what stays full-strength (forcefield, model architecture, integrator, etc.).

### Recipe 2: <name>

(more recipes as needed for different stages of the typical pipeline)

## What goes in a smoke analysis for this tool

Concrete fields for `SMOKE_ANALYSIS_NNN.md` when the campaign uses this tool. Show a sample table:

```markdown
## Measurements extracted

| Signal | Method | Observed | Expected (Layer A) | Status |
|---|---|---|---|---|
| ... | ... | ... | ... | ... |
```

Include the tool-specific observables that should always appear. The agent should be able to copy this and fill in.

## Extrapolation methods specific to this tool

Which method (linear, exponential, convergence, threshold-crossing — see `workflows/smoke-analysis.md`) applies to which observable. This guides the agent's choice without re-deriving each time.

## Cross-references

- `compute-validation/SKILL.md` — parent skill
- `compute-validation/workflows/smoke-analysis.md` — framework
- `compute-validation/workflows/verification.md` — Layer A reasoning
- Tool's own documentation: <link>
- Active community / forum: <link>
