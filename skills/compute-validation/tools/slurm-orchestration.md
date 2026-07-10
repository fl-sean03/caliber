# Tool: SLURM Orchestration

SLURM-specific reasoning hints for the orchestration-safety workflow (Layer A'). Read this when validating any submission pattern destined for a SLURM cluster — single jobs, arrays, dependency chains, watchdog scripts, in-script resubmits.

> **Critical framing: this page seeds reasoning, not linting.** It is NOT a hardcoded checklist. Hardcoded checks only catch known patterns. The point of this page is to prime an agent's thinking about SLURM-specific failure modes — categories of risk, concrete examples of how each has broken in practice, recommended patterns with honest tradeoffs. The agent applies general reasoning to the specific submission in hand. Variation in conclusions per submission is expected and correct.

Pairs with `workflows/orchestration-safety.md` (the four-phase agentic workflow). Sister page to `tools/namd.md` (which is physics-focused; this one is orchestration-focused). For Alpine-specific partitions, QoS rules, and real-world cluster limits, see `compute-strategy/backends/alpine.md` — don't duplicate.

---

## Section 1: Categories of SLURM orchestration risk

Five categories an agent should think through for any non-trivial SLURM submission. Each has a definition, why it matters, concrete failure modes that have hit it, and reasoning questions to ask.

### 1.1 Self-propagation patterns

**Definition.** Any submission element that can spawn another submission. The four canonical shapes are: in-script `sbatch` calls (resubmit-on-failure, resubmit-on-success), job arrays, dependency chains (`--dependency=afterany:...`), and watchdog or polling scripts that periodically submit.

**Why it matters.** This is the #1 source of runaway disasters on SLURM. A fast-failing job + an unconditional resubmit produces hundreds to thousands of submissions per hour. Even bounded patterns can compound badly when combined (in-script resubmit AND a pre-chained dependency both firing on the same trigger).

**The four-guardrails principle.** Every self-propagating element should have, simultaneously:

1. **Bounded counter** — an explicit iteration cap (e.g., a counter file or env var checked at the top of the script; halt when exceeded). Without this, no theoretical upper bound on submissions.
2. **Rate ceiling** — submissions per unit time cannot exceed a configured cap. A 1-second-fail loop without rate ceiling produces 3600 submissions/hour.
3. **Failure ceiling** — consecutive failures trigger halt before retry. Distinguishes "infrastructure hiccup, retry once" from "systematic bug, stop now."
4. **Notification cap** — emails / Slack / webhooks per time window. Missing this is what turns "runaway" into "16,000-email inbox flood."

Missing any one → think harder. Missing two → almost certainly a future incident.

**Failure modes that have hit this category:**
- In-script `sbatch ... slurm.sh` triggered on `exit != 0`, no counter — 8,366 submissions in ~8 hours when the underlying job fast-failed (config typo).
- Job array of size 1000 with `--mail-type=END,FAIL` — every element fires emails (2 per failure, sometimes more).
- Pre-chained `afterany` dependencies stacked 50 deep alongside an in-script resubmit — both fire when one job ends, race condition on restart-file writes corrupts data.

**Reasoning questions:**
- Does this submission contain or trigger an `sbatch` call from within a running job?
- If a job fails in 1 second, how many times will the pattern fire in the next hour?
- Is there an explicit halt condition reachable from any failure path?

### 1.2 Walltime cliff and signal handling

**Definition.** SLURM enforces `--time` by sending SIGTERM, then SIGKILL after a grace period (cluster default usually 30s, sometimes 60s, occasionally configurable). Any bash code after the main job command — restart-file housekeeping, resubmit logic, cleanup, log copying — has no guarantee of running if SIGKILL arrives first.

**Why it matters.** Many in-script resubmit patterns are written as `$EXE ... ; sbatch resubmit.sh` with the assumption that the second statement always runs. At walltime cliff, it often does not. The chain silently dies. The user only notices hours or days later when expected output never materializes.

**Failure modes that have hit this category:**
- A 12-hour NAMD job with post-run `sbatch` to start the next 12 hours — chain stalls because the resubmit line never executed after walltime SIGKILL.
- Restart-file writes interrupted by SIGKILL mid-write; restart file present but truncated; next chain link reads garbage.
- Cleanup of temporary files in `$SLURM_TMPDIR` skipped on SIGKILL, leaving orphaned data the scheduler cleans up — but state assumed by downstream stages is gone.

**Mitigations to consider:**
- Request `--signal=B:USR1@<seconds>` to trigger an early bash trap before walltime cliff; the trap performs cleanup and resubmit gracefully.
- Pre-chain follow-up jobs instead of relying on post-work bash.
- Write restart files frequently and use temp-file + atomic-rename idiom so a partial write doesn't poison the chain.

**Reasoning questions:**
- If the main job hits walltime, will any bash code after it run?
- Are restart files written frequently enough that a SIGKILL costs less than ~1 hour of redo?
- Is there a signal trap installed? Is it tested?

### 1.3 Dependency semantics

**Definition.** SLURM `--dependency` types include `afterany`, `afterok`, `aftercorr`, `afternotok`, `after`, and `singleton`. They differ in when downstream jobs become eligible to run.

| Type | Downstream runs when prev... |
|---|---|
| `after` | starts (any state) |
| `afterany` | terminates (success OR failure) |
| `afterok` | terminates with exit 0 |
| `afternotok` | terminates with exit != 0 |
| `aftercorr` | array element N of upstream completes (downstream array element N eligible) |
| `singleton` | no other job with same name/user is running |

**Why it matters.** `afterany` is the most-used and most-dangerous: it propagates the chain regardless of upstream success. If the upstream produced corrupt restart files, the downstream uses them. Chain proceeds, data is silently bad.

**Race conditions:** when multiple jobs become eligible simultaneously (e.g., an in-script resubmit AND a pre-chained `afterany` both trigger on the same upstream end), they may both attempt to read/write the same restart files. SLURM does not serialize them.

**Failure modes that have hit this category:**
- `afterany` used for a chain where step N writes a coordinate file step N+1 needs. Step N fails partway; step N+1 reads partial file and produces wrong-physics output without erroring.
- Chain with `afterany` proceeds for 14 of 15 ensemble members; one member's upstream fast-failed, downstream chain ran on uninitialized state.
- Both in-script resubmit and pre-chained `afterany` fire on the same upstream — two downstream jobs eligible simultaneously, both load same restart, both write same outputs, last-writer-wins corrupts.

**Reasoning questions:**
- Is `afterany` the right semantic, or do you actually want `afterok`?
- If the upstream succeeds but produces nonsense, will the chain notice?
- Is there any path by which two jobs become eligible at the same time?

### 1.4 Resource and quota limits

**Definition.** Every cluster imposes limits: max submitted jobs per user (`QoSMaxSubmitJobPerUserLimit`), max running jobs, partition GPU caps, walltime limits per partition, fairshare allocations, association limits. These interact across QoS, partition, and user-association tables.

**Why it matters.** Limits manifest in two distinct ways:
- **Silent rejection** — `sbatch` exits non-zero, prints a brief reason to stderr, no job created. If your script doesn't check the exit code, the chain silently breaks.
- **Queue position penalty** — accepted but flagged with reason (`QOSMaxJobsPerUserLimit`, `Priority`, `Resources`, `AssocGrpCPUMinutesLimit`). Job sits indefinitely behind other work.

For pre-chained patterns: submitting 50 jobs upfront can hit `QoSMaxSubmitJobPerUserLimit` even though queueing them is the entire point of the pattern.

**Failure modes that have hit this category:**
- 60-element pre-chain hits a 50-job-per-user limit; jobs 51-60 silently rejected; chain runs 50 steps then stops without any error.
- `atesting` partition has a much smaller submit cap than the main partition; agent assumes its prior experience with normal partition applies; submission rejected.
- Fairshare exhaustion from a fast-fail loop pushes future jobs to position 200+ in the queue for a week.

**Reasoning questions:**
- What's the per-user submit cap for the target partition / QoS?
- Does the planned submission rate or pre-chain depth exceed any cap?
- After this campaign, will fairshare be in a state that punishes the next campaign?

### 1.5 Notification volume

**Definition.** `--mail-type` controls when SLURM emails the user. Options: `BEGIN`, `END`, `FAIL`, `REQUEUE`, `ALL`, `TIME_LIMIT`, `TIME_LIMIT_90`, etc. Each event triggers one email per job (or per array element).

**Why it matters.** Notifications scale with the number of submissions. A 100-element array with `--mail-type=END,FAIL` produces at minimum 100 emails on a clean run (END) and up to 200 emails if anything fails (END + FAIL). Combined with self-propagation, the multiplier compounds: 1000 fast-fail resubmissions × 2 events = 2000 emails, often delivered in minutes.

The cluster's MTA may rate-limit, mark messages as spam, or briefly blacklist the recipient. Users miss real failure notifications buried in noise.

**Failure modes that have hit this category:**
- 8,366 fast-fail jobs × ~2 emails each = ~16,000+ emails, inbox flooded for hours.
- Pre-chained 100-step ensemble with `--mail-type=ALL` produced ~500 emails for a normal-completion run, drowning out a real failure on step 73.
- Gmail filters trip and start dumping legitimate cluster mail into spam after a flood event; future real failures go unseen.

**Mitigations to consider:**
- Drop `--mail-type` on chain links entirely; configure mail only on a known terminal job, or on a separate sentinel script.
- Use a per-campaign sentinel: have the final job in the chain be the only one with notifications.
- Route mail to a campaign-specific address or filter folder, not the main inbox.

**Reasoning questions:**
- How many mail events fire if the campaign runs to clean completion?
- How many fire if it fails-fast on the first job?
- Is there any path to more than ~10 emails for a normal run? More than ~100 for a worst-case?

---

## Section 2: Specific failure-mode worked examples

Compact patterns of SLURM orchestration failure with the shape an agent might recognize in a new submission.

### 2.1 Mail flood from in-script resubmit + fast-fail simulation

**Symptom.** User reports inbox at thousands of emails over hours. `sacct -u <user> -S now-8hour -X` shows hundreds of completed jobs with `Elapsed` < 1 minute. Job names all identical.

**Root cause.** Submit script ends with `$EXE ... || sbatch --dependency=afterany:$SLURM_JOB_ID slurm.sh`. The simulation has a config typo (or missing input file) that crashes within 1-2 seconds of start. Each failure triggers an immediate resubmit. `--mail-type=END,FAIL` fires twice per cycle. No bounded counter, no rate ceiling, no failure ceiling.

**Observed real incident (2026-05-10).** ~8,366 jobs, ~16,000 emails in roughly 8 hours.

**Mitigation.**
- Immediate: `scancel -u <user>` to halt the chain, then `scontrol hold` any pending jobs, then debug the underlying fast-fail before re-enabling resubmit.
- Structural: add a counter file (`$WORKDIR/.iter`) checked at top of script; abort if > N. Add `sleep 30` before resubmit so worst-case rate is 120/hour not 3600/hour. Drop `--mail-type` from chain links. Add a consecutive-failure detector that halts after 3.

**Generalization.** Self-propagating action + fast-fail mode + no guardrails = inevitable disaster. The four guardrails (bounded counter, rate ceiling, failure ceiling, notification cap) all need to be present for any in-script resubmit.

### 2.2 Silent chain death at walltime

**Symptom.** Multi-day chain reaches walltime on step 3 of 15. Step 3's output files exist. No step-4 job ever appears in the queue. No error message in any log. User notices only after expected step-15 output never lands.

**Root cause.** Submit script structure: `$EXE production.namd ; sbatch next_step.sh`. The NAMD run consumes the entire 12-hour walltime. SLURM sends SIGTERM at walltime, then SIGKILL ~30s later. The `sbatch next_step.sh` line never runs because the shell was killed before reaching it.

**Mitigation.**
- Pre-chain all 15 follow-up jobs upfront with `--dependency=afterok:<prev_jobid>`. Each link is a queued job whose eligibility is gated on the previous step.
- Or: use `--signal=B:USR1@120` to receive SIGUSR1 two minutes before walltime; install a trap that performs graceful resubmit before SIGKILL arrives. Test the trap actually fires.

**Generalization.** Any logic placed after a long-running command in a SLURM script is at risk of being SIGKILLed. Don't put load-bearing logic there. Either pre-chain, or use signal traps with verified timing.

### 2.3 Race condition between in-script resubmit and pre-chained dependency

**Symptom.** Two jobs start within a few seconds of each other, both targeting the same restart-file directory. The next chain step reads inconsistent state (one job's coordinates, another's velocities) and produces non-deterministic, non-reproducible output.

**Root cause.** The submit pattern combined a defensive in-script `sbatch --dependency=afterany:$SLURM_JOB_ID resubmit.sh` AND a pre-chained `sbatch --dependency=afterok:<this_job> next.sh` queued at campaign start. When this job ends, both downstream jobs become eligible. SLURM does not serialize them.

**Mitigation.**
- Pick one pattern. Either pre-chain OR in-script-resubmit, not both.
- If both are required for some defensive reason, use `singleton` dependency on the downstream jobs and ensure unique job names so SLURM serializes them.
- Use atomic-write idiom for restart files (write to `.tmp`, fsync, rename) so a partial write doesn't corrupt state.

**Generalization.** Self-propagation patterns compose badly. Adding a second mechanism for the same purpose multiplies the failure surface rather than adding safety.

### 2.4 QoSMaxSubmitJobPerUserLimit hit unexpectedly

**Symptom.** `sbatch` returns non-zero and prints something like `Batch job submission failed: Job violates accounting/QOS policy (job submit limit, user's size and/or time limits)`. If the script doesn't check exit code, the chain silently fails to extend.

**Root cause.** A partition or QoS imposes a per-user submitted-jobs cap (commonly 50, sometimes much lower on testing partitions like `atesting`). Agent assumes prior experience with the main partition transfers. Pre-chain attempts to submit 60 follow-up jobs; jobs 51-60 are rejected.

**Detection.**
- Pre-check: `scontrol show partition <name>` and `sacctmgr show qos <qos_name>` for `MaxSubmitJobsPerUser` and `MaxJobsPerUser`.
- Post-submit: always check `$?` after every `sbatch`, not just the first one. Capture stderr.

**Mitigation.**
- Stay below the cap by structuring as rolling chains: submit chunks of N, with the last job in each chunk submitting the next chunk's worth.
- Or, request a QoS elevation if the campaign genuinely needs higher concurrency.

**Generalization.** Cluster limits are cluster-specific and partition-specific. Don't reuse submission patterns across partitions without re-validating limits.

### 2.5 `afterany` instead of `afterok` causing chain to proceed on bad data

**Symptom.** Final chain output looks plausible in shape but is scientifically wrong. RMSD jumps unphysically between steps N and N+1. Investigation shows step N crashed at 30% completion but step N+1 ran on the partial restart files.

**Root cause.** Submit pattern uses `--dependency=afterany:$JOBID` because the author wanted "robustness against weird upstream exit codes." The upstream job hit a recoverable error, exited non-zero, but had written incomplete restart files. Downstream proceeded anyway.

**Mitigation.**
- Default to `afterok` unless you have an explicit reason to use `afterany`.
- If `afterany` is genuinely needed (e.g., recovery / cleanup pattern), the downstream job's first action must be an explicit validation of upstream output (file size, header checksum, expected step count, etc.) and an early-exit if invalid.

**Generalization.** Dependency semantics are load-bearing. The default should be the conservative one (`afterok`); other types require an explicit design rationale.

---

## Section 3: Pattern recommendations (NOT prescriptions)

Three submission patterns for self-propagating SLURM workflows, with honest tradeoffs. The agent reasons about which fits the specific job; this page does not pick a winner.

### 3.1 In-script resubmit

```bash
#!/bin/bash
#SBATCH --time=12:00:00
ITER=$(cat .iter 2>/dev/null || echo 0)
if [ "$ITER" -ge 15 ]; then exit 0; fi
echo $((ITER + 1)) > .iter
$EXE production.namd
[ $? -eq 0 ] || { echo "halt: nonzero exit"; exit 1; }
sleep 30
sbatch --dependency=afterok:$SLURM_JOB_ID slurm.sh
```

**Pros.** Simple, single script, easy to read. State is local to the workflow directory. Easy to debug from a single log.

**Cons.** Fragile at the walltime cliff — `sbatch` may not run if SIGKILL arrives first. Brittle without the four guardrails. Notification volume scales with iteration count.

**When acceptable.** Short jobs (well under walltime), with bounded counter, rate ceiling (`sleep` before resubmit), failure ceiling (consecutive non-zero check), and notification cap (no `--mail-type` on chain links, or only on the explicit terminal job).

### 3.2 Pre-chained submission

```bash
PREV=$(sbatch --parsable step1.sh)
for i in $(seq 2 15); do
    PREV=$(sbatch --parsable --dependency=afterok:$PREV step${i}.sh)
done
```

**Pros.** Structurally robust against walltime cliff — no post-work code is load-bearing. Entire chain visible in `squeue`. Easy to cancel (`scancel <jobids>`) or inspect. No in-script resubmit means no fast-fail loop possible.

**Cons.** Consumes queue slots upfront. Hits `MaxSubmitJobsPerUser` if N is large. Less flexible if upstream completion conditions evolve mid-chain.

**When best.** Long-running multi-day chains, ensemble runs of known length, scientific pipelines with well-defined stage count.

### 3.3 Signal trap with `--signal=B:USR1@<seconds>`

```bash
#!/bin/bash
#SBATCH --time=12:00:00
#SBATCH --signal=B:USR1@120

resubmit_handler() {
    sbatch --dependency=afterok:$SLURM_JOB_ID slurm.sh
    exit 0
}
trap resubmit_handler USR1

$EXE production.namd &
wait $!
# normal-completion path also resubmits
sbatch --dependency=afterok:$SLURM_JOB_ID slurm.sh
```

**Pros.** Graceful pre-walltime cleanup. Combines in-script flexibility with walltime-cliff resilience.

**Cons.** Signal timing reliability varies across clusters (some honor `@<seconds>` precisely, some are jittery). Requires backgrounding the main job with `&` and `wait`, which changes how exit codes propagate. Easy to get wrong.

**When best.** Belt-and-suspenders combined with a pre-chained submission — if either fires, the chain advances. Useful when the agent doesn't fully trust either mechanism alone.

**Honest acknowledgement.** No single pattern is universally correct. Long campaigns on a stable cluster lean toward pre-chained. Exploratory or short-iteration work leans toward in-script. Defensive setups use signal traps. The agent should reason about which fits.

---

## Section 4: SLURM-specific reasoning questions

A list to prompt reasoning, not check pass/fail. Different submissions yield different answers; that's correct.

1. Does this script contain any `sbatch` calls? For each: is it bounded, rate-limited, failure-ceilinged, and notification-capped?
2. If the underlying job fast-fails (< 60 seconds), how many submissions does the pattern produce in the next hour?
3. If walltime expires mid-run, will any post-work bash actually execute?
4. Is there a signal trap installed? If so, what cluster behavior is it relying on?
5. Are restart files written frequently enough that walltime SIGKILL costs less than 1 hour of redo?
6. What dependency type is used? Is it `afterany` where `afterok` would be safer?
7. Could two chain links become eligible simultaneously? (In-script resubmit + pre-chain is the classic trigger.)
8. What's the `MaxSubmitJobsPerUser` for the target partition / QoS? How does the planned pre-chain depth compare?
9. What's the `MaxJobsPerUser` (running)? Could the pattern starve other work in the same allocation?
10. How many emails fire on a clean-completion run? On a fast-fail run? Are the chain links muted?
11. Is `--mail-type` set on every chain link, or only on the terminal job?
12. Does the script check `$?` after every `sbatch` call, capturing stderr so silent rejections are caught?
13. What's the cluster's SIGTERM-to-SIGKILL grace period? Have you tested it for this submission?
14. Could fairshare cost from this campaign meaningfully delay the next one?
15. Are restart-file writes atomic (write-to-temp, fsync, rename), so a partial write can't poison the next link?
16. Is `--requeue` set? What's the cluster default? Would automatic requeue interact badly with the resubmit pattern?
17. If the user runs `scancel <jobid>`, does the chain stop cleanly, or does the in-script resubmit immediately restart it?
18. Is there a documented halt procedure — a single command that kills the entire chain and prevents auto-relaunch?
19. Does the workflow distinguish "infrastructure error" (worth retrying) from "config error" (must halt)?
20. If a human notices something wrong at 3 AM, how do they stop the workflow without taking down adjacent work?

---

## Section 5: Reference commands for diagnosis

SLURM commands an agent uses when monitoring an active chain or doing root-cause analysis after an incident.

### Queue and history

```bash
squeue -u <user>                          # current queued/running jobs
squeue -u <user> -t PENDING --start       # estimated start times
squeue -u <user> -h | wc -l               # count active jobs
sacct -u <user> -S now-1hour -X           # recent submissions
sacct -u <user> -S now-24hour -X \
    --format=JobID,JobName,Partition,State,Elapsed,ExitCode
sacct -j <jobid> --format=JobID,JobName,State,Elapsed,ExitCode,ReqTRES,AllocTRES
sacct -j <jobid> -o JobID,Reason%50       # detailed reason field for failures
```

### Cluster topology and limits

```bash
scontrol show partition <name>            # walltime, GPU, node caps
sacctmgr show qos <qos_name> format=Name,MaxSubmitJobsPerUser,MaxJobsPerUser,MaxWall
sacctmgr show association user=<user> format=Account,QOS,GrpTRES,MaxSubmit
sshare -u <user>                          # fairshare state
sinfo -p <partition> -o "%P %g %D %T %N"  # node state in partition
```

### Anti-pattern detection

Fast-fail count (jobs that completed in under 2 minutes within the last 15 minutes — strong signal for runaway resubmit loops):

```bash
sacct -u <user> -S now-15min -X --format=Elapsed -P --noheader \
    | awk -F: '{if ($1=="00" && $2 < 2) c++} END {print c+0}'
```

Submission-rate check (count of new jobs per hour in the last 4 hours):

```bash
sacct -u <user> -S now-4hour -X --format=JobID,Submit -P --noheader \
    | awk -F'|' '{print substr($2, 1, 13)}' | sort | uniq -c
```

Identify jobs with mail enabled (requires inspecting submit scripts; sacct doesn't expose this):

```bash
grep -lE '^\s*#SBATCH\s+--mail-type' submit_scripts/*.sh
```

### Halting a runaway

```bash
scancel -u <user>                          # cancel everything (heavy hammer)
scancel -u <user> --state=PENDING          # cancel only pending (safer; lets running jobs finish)
scancel --name=<jobname>                   # cancel by name
scontrol hold <jobid>                      # hold a specific job without killing
scontrol release <jobid>                   # release after fixing
```

When in doubt during an incident: `scancel -u <user>` first, debug second. A wrongly-cancelled job is recoverable; another hour of mail flood may not be.

---

## Section 6: Cross-references

- `compute-validation/workflows/orchestration-safety.md` — parent four-phase workflow that uses this page
- `compute-validation/tools/namd.md` — sister tool page, physics-focused (energy / pressure / box dynamics) rather than orchestration-focused
- `compute-validation/templates/ORCHESTRATION_CHECK.template.md` — output artifact the parent workflow produces
- `compute-strategy/backends/alpine.md` — Alpine cluster specifics (partitions, QoS, real-world submit caps); referenced rather than duplicated here
- `campaign-orchestration/SKILL.md` — runtime monitoring during long campaigns (this page is the static-analysis sibling)
- SLURM dependency man page: <https://slurm.schedmd.com/sbatch.html#OPT_dependency>
- SLURM signal man page: <https://slurm.schedmd.com/sbatch.html#OPT_signal>
- SLURM `sacct` reference: <https://slurm.schedmd.com/sacct.html>
