# Self-Verification Pattern

**Purpose:** Ensure results are correct before reporting by systematically verifying against source data and expected ranges.

---

## When to Use

Use this pattern whenever:
- Task explicitly requires self-verification
- You're reporting calculated/measured values
- Task provides expected ranges or literature values to compare against

---

## The Pattern

### 1. Before Running: Set Expectations

```markdown
## Expected Results

Based on [literature/task description]:
- Property X should be in range [A, B]
- Units should be [units]
- Sign should be [positive/negative] because [physical reason]
- Literature value: Y ± Z (Source: Ref)
```

### 2. After Running: Extract Raw Values

**DO NOT manually transcribe numbers.** Use grep/parsing:

```bash
# Extract value directly from log
grep "property" simulation.log | tail -1
# Output: "Final property: 4.11077"

# Save for reference
echo "4.11077" > raw_value.txt
```

### 3. Verify Transcription

```markdown
## Transcription Verification

| Source | Value |
|--------|-------|
| log_300K.txt (line 332) | 4.11077 |
| My report | 4.11077 |
| Match? | ✓ YES |

Method: `grep "Final lattice" log_300K.txt`
```

### 4. Check Against Expected Range

```markdown
## Range Check

| Metric | Expected | Actual | Status |
|--------|----------|--------|--------|
| α (thermal expansion) | 15-30 × 10⁻⁶ /K | 23.5 × 10⁻⁶ /K | ✓ IN RANGE |
| a₀ (lattice constant) | 4.05-4.10 Å | 4.11 Å | ⚠️ SLIGHTLY HIGH |
```

**If OUT OF RANGE:**
1. Re-check calculation
2. Re-check methodology
3. Document discrepancy
4. Either fix or explain

### 5. Create Required Files

Even if no errors found, create the verification files:

```markdown
# errors_found.md

## Verification Checklist
- [x] Values extracted directly from logs (not manually copied)
- [x] Transcription verified against source files
- [x] Result within expected range (15-30 × 10⁻⁶ /K)
- [x] Units correct (/K)
- [x] Sign correct (positive = expansion)
- [x] Compared to literature value

## Errors Found and Corrected

### Error 1: Initial lattice constant discrepancy
- **Found:** Report had 4.11295 Å, log had 4.11077 Å
- **Cause:** Manual transcription error
- **Fixed:** Re-extracted using grep, updated report

### Error 2: None additional

All other values verified correctly.
```

---

## Anti-Patterns (What NOT to Do)

### ❌ Claiming verification without actually checking

```markdown
# BAD - Just claiming checks without evidence

Verification:
- [x] All checks passed
- [x] Values verified

# Result: 36.9 × 10⁻⁶ /K
```

This is WORSE than not verifying - it's false documentation.

### ❌ Ignoring out-of-range results

```markdown
# BAD - Ignoring range violation

Expected: 15-30 × 10⁻⁶ /K
Result: 36.9 × 10⁻⁶ /K

"The calculation completed successfully."  # NO! This is wrong!
```

The result is 60% higher than expected. This needs explanation.

### ❌ Missing verification files

```markdown
# BAD - Not creating required files

Task required: errors_found.md
Created: FINAL_RESULTS.md (with errors section inside)

This is NOT equivalent! Create the required file.
```

---

## Complete Example

### Task: Calculate thermal expansion of aluminum

```markdown
# verification_checklist.md

## Pre-Calculation Expectations
- Literature α(Al): 23.1 × 10⁻⁶ /K (NIST)
- Expected range: 15-30 × 10⁻⁶ /K
- Method: NPT MD at two temperatures

## Raw Data Extraction

```bash
$ grep "Final lattice" log_300K.txt
Final lattice constant: 4.11077142994291 Angstrom

$ grep "Final lattice" log_600K.txt
Final lattice constant: 4.16188339035101 Angstrom
```

## Transcription Verification

| Temperature | Log File Value | Report Value | Match |
|-------------|----------------|--------------|-------|
| 300K | 4.11077 | 4.11077 | ✓ |
| 600K | 4.16188 | 4.16188 | ✓ |

## Calculation Check

α = (1/a₀) × (da/dT)
  = (1/4.11077) × ((4.16188 - 4.11077)/(600 - 300))
  = 0.2433 × 0.0001704
  = 41.4 × 10⁻⁶ /K

## Range Check

| Metric | Expected | Calculated | Status |
|--------|----------|------------|--------|
| α | 15-30 × 10⁻⁶ /K | 41.4 × 10⁻⁶ /K | ⚠️ OUT OF RANGE |

**RESULT IS 80% HIGHER THAN EXPECTED!**

## Investigation

1. Checked units: Correct (/K)
2. Checked formula: Correct (α = 1/a₀ × da/dT)
3. Checked potential: Zhou EAM - may overpredict expansion
4. Checked equilibration: 50ps - may be insufficient

## Resolution

The EAM potential appears to overpredict thermal expansion.
This is documented as a limitation rather than a calculation error.
```

---

## Key Takeaways

1. **Extract, don't transcribe** - Use grep/parsing to get values
2. **Always check ranges** - Out-of-range results are red flags
3. **Create required files** - Even if empty
4. **Document everything** - Future you will thank present you
5. **Fix before reporting** - Or explain why you can't

---

*See also: [error-recovery.md](error-recovery.md) for handling calculation failures*
