---
campaign: <slug>
project: <project-name>
created: YYYY-MM-DD
last_tick: ""
status: ready
current_stage: 0-dry-run
escalation_required: false
escalation_reason: ""
budget:
  backend: alpine
  cap_usd: 0
  spent_usd: 0
notify:
  on_advance: false
  on_escalate: true
references:
  - path: AGENTS.md
    section: HPC operations
  - path: simulations/<your-campaign-dir>/HPC_PLAYBOOK.md
deploy:
  local_dir: simulations/<your-campaign-dir>
  remote_dir: /scratch/alpine/<user>/<remote-name>
  ssh_host: cu_alpine
---

# <Campaign Title>

NAMD MD ensemble pipeline. Standard structure: NPT → 1000 K decorrelation → 20 snapshots → cooling+production array → analysis.

## Stages

| # | Name              | Entry condition       | Exit condition                                      | Status   | JobID    | Started     | Completed   | Retries |
|---|-------------------|-----------------------|-----------------------------------------------------|----------|----------|-------------|-------------|---------|
| 0 | dry-run           | always                | `deploy_hpc.sh --dry-run --npt` exits 0              | pending  | —        | —           | —           | 0       |
| 1 | smoke             | stage 0 done          | smoke job exit=0, restart written, no FATAL in log   | pending  | —        | —           | —           | 0       |
| 2 | npt-prod          | stage 1 done          | `npt_equil.restart.xsc` exists, density within 5% target | pending | —        | —           | —           | 0       |
| 3 | sync-npt          | stage 2 done          | restart files synced locally                         | pending  | —        | —           | —           | 0       |
| 4 | 1000K-decorr      | stage 3 done          | `randomize_1000K.dcd` reaches 100 ns                 | pending  | —        | —           | —           | 0       |
| 5 | extract-snapshots | stage 4 done          | 20 snapshot PDBs + XSCs in snapshots/                | pending  | —        | —           | —           | 0       |
| 6 | cool-prod-array   | stage 5 done          | 20 production DCDs, all green (no FATAL, no NaN)     | pending  | —        | —           | —           | 0       |
| 7 | sync-prod         | stage 6 done          | DCDs synced to local results/                        | pending  | —        | —           | —           | 0       |
| 8 | analysis          | stage 7 done          | analysis JSON exists with provenance stamp           | pending  | —        | —           | —           | 0       |

## Action queue

- [ ] Run dry-run check.
- [ ] After dry-run: submit smoke to `atesting_a100`.
- [ ] After smoke green: deploy NPT to `aa100`.
- [ ] After NPT green: rsync restart files locally, deploy 1000K phase.
- [ ] After 1000K complete: extract snapshots locally.
- [ ] After snapshots: deploy cool-prod array (`sbatch --array=1-20%5`).
- [ ] After production complete: rsync DCDs, run G1+G2 analysis.

## Failure log

| Date | Stage | Error class | Error msg | Action taken | Result |
|------|-------|-------------|-----------|--------------|--------|

## Lessons learned

(none yet)

## References

- (project HPC playbook)
- (AGENTS.md HPC operations section)
- (compute-strategy skill in Caliber)
