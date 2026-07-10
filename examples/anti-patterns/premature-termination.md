# Anti-Pattern: Premature Termination

## What It Looks Like

**Task:** "Calculate formation energies for NaCl, KCl, and RbCl"

**Bad behavior:**
```
✓ Downloaded Na and Cl pseudopotentials
✓ Set up NaCl structure
"I've established the framework. The KCl and RbCl calculations would
follow the same pattern..."

[STOPS]
```

**What's wrong:** Agent stopped after setup for ONE compound. Two compounds not done at all.

## Why This Happens

1. **Pattern recognition**: Agent sees the pattern, assumes rest is "obvious"
2. **Effort conservation**: Doing 3x the work seems redundant
3. **Misunderstanding "completion"**: Thinks demonstrating capability = doing work
4. **Context limits**: May be trying to "save tokens"

## The Damage

- User gets 0/3 compounds calculated
- No actual results produced
- Documentation incomplete
- No efficiency improvements demonstrated (main point of task)

## How to Avoid

### Before Starting
Ask yourself: "What are ALL the deliverables?"
```
Deliverables for this task:
[ ] NaCl formation energy + documentation
[ ] KCl formation energy + documentation
[ ] RbCl formation energy + documentation
[ ] Comparison/summary
```

### During Work
Track progress explicitly:
```
NaCl: [DONE] E_f = -4.26 eV
KCl:  [IN PROGRESS]
RbCl: [NOT STARTED]
```

### Before Claiming Complete
Check your list:
```
[ ] All deliverables have checkmarks?
[ ] Actual numbers/results exist (not just "would be similar")?
[ ] Files created match what was requested?
```

## Correct Behavior

**Task:** "Calculate formation energies for NaCl, KCl, and RbCl"

**Good behavior:**
```
Starting NaCl calculation...
- Downloaded pseudopotentials
- Running SCF... converged
- E_f(NaCl) = -4.26 eV
- Documented in nacl/calculation.md
[1/3 complete]

Starting KCl calculation...
- Reusing Cl pseudopotential
- Downloaded K pseudopotential
- Running SCF... converged
- E_f(KCl) = -4.32 eV
- Applied mixing lesson from NaCl
- Documented in kcl/calculation.md
[2/3 complete]

Starting RbCl calculation...
- Downloaded Rb pseudopotential
- Running SCF... converged
- E_f(RbCl) = -4.18 eV
- Documented efficiency gains
- Documented in rbcl/calculation.md
[3/3 complete]

Compiling results...
- Created results/formation_energies.csv
- Created learning_summary.md

ALL DELIVERABLES COMPLETE.
```

## Red Flags to Watch For

If you catch yourself thinking:
- "The pattern is established..." → STOP. Do the work.
- "The rest would be similar..." → STOP. Do the work.
- "I've demonstrated the approach..." → STOP. Do the work.
- "To save time/tokens..." → STOP. Do the work.

## The Rule

**If asked to do N things, do N things. Not 1 thing and a promise.**
