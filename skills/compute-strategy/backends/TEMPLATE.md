# Backend: <NAME>

One-line description: who runs it, what type (HPC / cloud / local), free or paid.

> Read this page when picking <NAME> for a job. The framework lives in `../SKILL.md`.

## Access

| Item | Value |
|---|---|
| Hostname / endpoint | |
| User / account | |
| Connect command | |
| Authentication | (key, MFA, token, …) |
| Scratch / working dir | |
| Long-term storage | |
| Scheduler | (SLURM / PBS / k8s / none) |

State exactly how to authenticate. If MFA is involved, say what triggers a prompt and how to recover from a stale auth.

## Pre-installed software

| Package | Path / module | Notes |
|---|---|---|
| | | |

If users compile their own software, say where (`/projects/<user>/software/` etc.).

## Partitions / queues / instance types

### Smoke / debugging

| Name | GPU/CPU | Max walltime | Use |
|---|---|---|---|
| | | | First stop for new configs |

### Production

| Name | GPU/CPU | Max walltime | Default | Capacity | Use |
|---|---|---|---|---|---|
| | | | | | |

### Long / specialty

| Name | Walltime | Use |
|---|---|---|
| | | |

## QoS / priority tiers (if any)

| Name | Walltime cap | Submit cap | Use |
|---|---|---|---|
| | | | |

## Decision examples

Concrete recommendations for jobs of different shapes — fill in for this backend.

| Situation | Pick |
|---|---|
| New config, never run | |
| Validated short production | |
| Validated long production | |
| Embarrassingly-parallel ensemble | |
| Backend-specific overflow | |

## Submission essentials

```bash
# Submit
# Status (mine)
# Recent finished
# Cancel
# Partition snapshot
```

## Job script / submission template

Backend-appropriate template. Keep it minimal but complete: name, partition, walltime, output path, notification, the actual run line.

## Common failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| | | |

Add rows as you encounter new failures.

## Storage discipline

What lives where. What gets purged when. Where the agent should put per-campaign work.

## Project-level wrappers (if any)

If projects in this user's environment wrap this backend through a higher-level tool (e.g., CCM for Vast.ai), name them and point at the wrapper. Project rules ("never use raw X") go here.
