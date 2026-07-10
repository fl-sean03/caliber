# Examples Directory

This directory contains canonical examples of good work. **Check here when starting a complex task.**

## When to Use Examples

| Task Type | Example to Check |
|-----------|------------------|
| Multi-compound/multi-system study | `workflows/multi-compound-study.md` |
| Task with sparse/minimal instructions | `workflows/sparse-input-task.md` |
| Need to revise approach mid-task | `workflows/iterative-refinement.md` |
| Something went wrong, need to recover | `patterns/error-recovery.md` |
| Need to document methodology | `patterns/documentation.md` |
| Validating your own results | `patterns/verification.md` |

## Directory Structure

```
examples/
├── README.md              # This file
├── workflows/             # Multi-step task patterns
│   ├── multi-compound-study.md
│   ├── sparse-input-task.md
│   └── iterative-refinement.md
├── patterns/              # Common good practices
│   ├── error-recovery.md
│   ├── documentation.md
│   └── verification.md
└── anti-patterns/         # What NOT to do
    ├── premature-termination.md
    └── missing-outputs.md
```

## Quick Reference

### Starting a Task
1. Identify task type from table above
2. Read relevant example(s)
3. Note the deliverables and structure
4. Proceed with work

### During Work
- Track progress against example structure
- Document issues as they occur
- Apply lessons from earlier steps to later ones

### Before Claiming Complete
- Compare your outputs to example's "Final Deliverables" section
- Verify all required files exist
- Check results against expectations
