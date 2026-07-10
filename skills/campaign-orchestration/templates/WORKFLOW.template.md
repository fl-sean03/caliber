---
campaign: <slug>
project: <project-name>
created: YYYY-MM-DD
last_tick: ""
status: ready                  # pending | ready | running | done | failed | escalated
current_stage: 0-dry-run
escalation_required: false
escalation_reason: ""
budget:
  backend: alpine              # alpine | vast-ai | local
  cap_usd: 0
  spent_usd: 0
notify:
  on_advance: false
  on_escalate: true
references:
  - path: AGENTS.md
    section: HPC operations
  - path: <project-playbook-path>
---

# <Campaign Title>

One-paragraph purpose.

## Stages

| # | Name              | Entry condition       | Exit condition                | Status   | JobID    | Started     | Completed   | Retries |
|---|-------------------|-----------------------|-------------------------------|----------|----------|-------------|-------------|---------|
| 0 | dry-run           | always                | manifest OK                   | pending  | —        | —           | —           | 0       |
| 1 | smoke             | stage 0 done          | exit=0, restart, no FATAL     | pending  | —        | —           | —           | 0       |
| 2 | <prod-stage>      | stage 1 done          | <criterion>                   | pending  | —        | —           | —           | 0       |

## Action queue

- [ ] Run dry-run check on local files.

## Failure log

| Date | Stage | Error class | Error msg | Action taken | Result |
|------|-------|-------------|-----------|--------------|--------|

## Lessons learned

(none yet)

## References

- (link to project playbook)
- (link to AGENTS.md)
