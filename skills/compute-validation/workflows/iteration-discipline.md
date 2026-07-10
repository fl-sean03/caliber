# Iteration Discipline — when the smoke loop terminates

You're here because you're inside the Layer B loop in `compute-validation/SKILL.md` and the next decision is *advance, iterate, or escalate*. The parent skill explains *why* the loop exists. Layer A (`workflows/verification.md`) explains *what to predict before compute*. This document is about *when to stop iterating*.

> One-line restatement: **stop when the loop has earned the right to advance, not when you're tired of iterating.** Both early and late termination are real costs.

Read `compute-validation/SKILL.md` first if you haven't. It carries the 3-layer model that this document presupposes.

---

## The fundamental tension

Two failure modes compete:

- **Stop too early** → a bug that smoke could have surfaced makes it into production. You burn 10 hours of compute on a doomed run. Worst case: silent corruption that's only visible in the analysis phase, weeks later.
- **Stop too late** → the loop iterates indefinitely. Cheap smoke isn't free; iteration burns engineering time, queue position, and (on paid backends) real money. Worst case: 8 smokes in, the agent is debugging the smoke harness rather than the campaign.

The discipline below is about resolving that tension *explicitly* rather than implicitly. Every loop termination should be defensible: either the criteria below were met, or escalation was triggered, with the reason recorded.

The cost of an unjustified "advance" is a crashed production. The cost of an unjustified "iterate" is a few hours of cheap compute. Bias toward iteration when the criteria are ambiguous, but not toward indefinite iteration — that's what the budget is for.

---

## Termination criteria — advance to production

Advance to production only when **all** of the following hold. Missing any one of these → keep iterating, don't advance.

1. **All Layer A red items are resolved.** A red item is not resolved by being downgraded; it's resolved by being either fixed in the config or empirically demonstrated to be a non-issue (with the smoke evidence cited in VERIFICATION.md).
2. **All yellow items are either resolved OR explicitly accepted with rationale.** "Accepted" means a sentence in VERIFICATION.md saying *what* was accepted and *why* — not silence. Future agents reading the file should understand the choice.
3. **Smoke measurements are consistent with verification predictions, within tolerance.** Tolerance is per-signal — see per-tool pages. As a default: throughput within ±20% of predicted, drift signals within the right *order of magnitude* and *direction*, threshold crossings either absent or explained.
4. **2 consecutive smokes with no config changes show identical behavior, within noise.** This is the reproducibility check (see below for what "identical" means operationally).
5. **Extrapolation does not predict any failure threshold crossing within the production timescale.** If a signal trends toward a known failure mode at a rate that would cross the threshold before production ends, that's a no-go even if the smoke itself looked fine.
6. **Iteration budget is not exceeded.** Default budget: 5 smokes. See below.
7. **Reproducibility check has been explicitly done.** Not "the smoke looked stable, probably reproducible" — actually run two consecutive smokes with frozen config and compare.

If any of (1)–(7) is missing, the answer is **iterate** or **escalate**, not **advance**.

---

## Iteration budget — default 5 smokes per campaign

Why 5?

- Empirically, most fixes resolve in 1–2 iterations. The first smoke surfaces a problem; the next smoke (after a config edit) confirms the fix.
- Persistent failures past 3 iterations indicate **design issues, not config tweaks**. If you're on iteration 4 still chasing the same symptom, the system is telling you the campaign needs rethinking, not retuning.
- A budget of 5 leaves room for: 1 baseline smoke + 1 reproducibility re-smoke at the end + up to 3 fix-and-retry iterations in between. That's enough to recover from typical issues without enabling indefinite iteration.

The budget is **per campaign**, not per error class. Hitting 5 smokes total → escalate, even if each smoke surfaced a different issue. That pattern means the campaign has more unknowns than verification anticipated, and the human should weigh in before more compute is spent.

The budget tightens for **workarounds** — see "Fix vs workaround" below.

---

## Escalation triggers — halt the loop

Any one of the following triggers escalation. The agent sets `escalation_required: true` in the campaign's WORKFLOW.md (per `campaign-orchestration` schema), records the reason, and stops iterating. Continuing past any of these is *not* the agent's call.

- **Iteration budget exceeded** without satisfaction of all termination criteria.
- **Same red flag persists after a fix attempt** — the fix didn't resolve it. (After two fix attempts on the same issue: escalate, period.)
- **Two consecutive fix attempts produce divergent (not converging) behavior.** Iteration N showed symptom X; you applied a fix; iteration N+1 shows a *different* symptom Y. That's not progress, that's the system telling you the model of what's happening is wrong.
- **Novel signal not in priors AND agent confidence in interpretation is low.** Don't bluff your way through unfamiliar signals. If you can't explain what you're seeing within ~30 minutes of investigation, the human should look.
- **Extrapolated production walltime exceeds requested + buffer.** If the smoke says production will take longer than the queue allows, you can't fix it by iterating smokes.
- **Cost cap would be exceeded** (paid backends only). The current iteration plus realistic buffer for one more must fit under the cap.
- **Anything destructive proposed.** Deleting data, changing force-field params, modifying inputs in ways that invalidate prior runs — escalate, never auto-execute.

Escalation isn't failure; it's the right call. Most campaigns terminate cleanly inside the budget. The ones that don't are exactly the ones that benefit most from human input before more compute is spent.

---

## Fix vs workaround

Not every config change earns the same trust. Distinguish:

- **Fix** — addresses the root cause. The agent can articulate why this change makes the symptom go away (the mechanism). Expected to make smoke and production behavior match the verification prediction. Counts toward the iteration budget at 1× weight.
- **Workaround** — bypasses a symptom without understanding the cause. May still be the right thing to do (deadlines exist), but it's flagged. Counts toward the iteration budget at **2× weight** — so the workaround budget is effectively 2.5 instead of 5.

Examples:

- *Fix*: smoke crashed at 1 ns with "atom velocity too large." Diagnosis: minimization was too short, system never relaxed. Increased minimize 1000 → 10000 steps. Expected mechanism: longer minimization removes high-energy clashes. (Smoke after fix runs cleanly, prediction held. Fix.)
- *Workaround*: same crash. Reduced timestep 2 fs → 1 fs. Symptom goes away (smaller steps tolerate higher initial velocities). But you didn't understand why velocities were high. (Smoke runs cleanly, but you've also doubled production walltime and you don't know if there's a lurking issue with the initial state.)

Workarounds are allowed when the fix is genuinely unclear and a deadline forces a decision. They must be flagged in `SMOKE_ANALYSIS_NNN.md` and in the eventual VALIDATION_SUMMARY. If a campaign accumulates more than one workaround, escalate even if the budget allows another iteration — the system is telling you something that warrants human attention.

---

## Reproducibility check — operationally

The 2-consecutive-smokes-identical criterion needs an operational definition, otherwise the agent will hand-wave it.

A reproducibility check is satisfied when:

- Two consecutive smokes ran with **byte-identical configs and inputs**. (A reproducibility check after a config edit is not a reproducibility check.)
- Throughput numbers across the two runs are within **±5%** of each other (tighter than the verification-prediction tolerance, because here we're comparing two real measurements).
- Energy / loss / drift curves overlay to visual inspection — no flagged divergences. For MD: total energy traces with comparable slope and noise band. For ML training: loss curves with comparable trajectory at matched step counts.
- No new red or yellow flags surfaced on the second run that weren't present in the first.

Why required: a campaign that's not deterministic at smoke timescale is not ready for production. Either there's a stochastic source you don't understand (which production will magnify), or there's nondeterminism in the pipeline itself (config not actually frozen). Both are problems.

Cheap variant: if the tool supports it, use a fixed RNG seed for both smokes — drives expected reproducibility tighter. If two smokes with the *same* seed disagree by more than ±5%, you have a real problem before you even ask about determinism across seeds.

---

## Updating priors during iteration

The bidirectional learning loop in the parent SKILL.md operates *during* iteration, not just at the end. Two cases:

1. **A fix resolves a previously-red flag.** Append to project `priors.yaml` as a discovered pattern. Include:
   - Pattern slug, system characteristics that triggered it, the symptom, the fix that worked.
   - Reference to this campaign's SMOKE_ANALYSIS_NNN.md so future agents can read the trail.
   - Severity classification — usually `medium` if discovered via smoke (smoke caught it before production), `high` if it would clearly have crashed production.

2. **A smoke surfaces something verification missed.** This is a verification-layer learning, not just a pattern. In addition to appending to priors, update the verification workflow's "external research" or "common verification failure modes" sections so the next verification doesn't miss it the same way.

Don't defer these updates to a later cleanup pass. Append as the iteration happens — by the time the loop terminates, priors should already reflect what was learned. Future verifications will then start sharper.

---

## Bidirectional learning rule

Every divergence between Layer A prediction and Layer B measurement is *information*. There are exactly two cases:

- **(a) The prior was wrong or incomplete.** Verification predicted X, smoke measured Y, and on investigation it's clear the prior reasoning was flawed (maybe an estimate used the wrong constants, maybe an analogy didn't transfer). → Update priors with the corrected reasoning. The smoke just made future verifications more accurate.
- **(b) The pattern is genuinely novel.** Verification didn't predict it because no prior described it. → Document it in priors as a new pattern. The smoke just expanded the catalog.

Either way, **record the rationale**. The temptation is to write "smoke disagreed with verification, retried with new config, all good." That throws away the learning. The right framing is "smoke measured Y instead of predicted X because of <reason>; updating priors with the corrected reasoning."

If the agent can't articulate which of (a) or (b) applies — that's a sign the divergence isn't fully understood, and confidence should drop until it is.

---

## Edge cases

The criteria above cover the common flow. Edge cases:

**Smoke crashes deterministically at a specific step.**
That's not a smoke pass — it's a Layer A miss. Loop back to verification, treat the crash as a previously-unidentified red item, address it there before re-smoking. Don't keep re-running the smoke hoping something changes.

**Smoke runs successfully but extrapolation predicts production failure.**
This is exactly what smoke is for. The smoke succeeded as a measurement instrument. Propose the fix that prevents the predicted failure (e.g., shorter run length, larger box, different timestep), edit the config, re-smoke. Do not advance just because the smoke itself didn't crash — the criterion is "extrapolation does not predict failure threshold crossing," not "smoke didn't crash."

**Smoke and verification disagree on a parameter — which to trust?**
Default: trust the measurement. The smoke is real data; the verification was a model. Then *investigate why the prediction was off* — see "Bidirectional learning rule." The verification model may have an error worth fixing for future campaigns. But don't override a measurement with a prediction.

**Smoke runs but is insufficient duration to extrapolate confidently.**
Run a longer canary smoke — 2–4× the original duration. This counts toward the iteration budget. If even the longer smoke doesn't give enough signal for extrapolation, escalate — the system is hard to predict at smoke timescales, which means production has unknowable risk.

**The reproducibility re-smoke surfaces a new red flag the first didn't.**
Treat the new flag as the next iteration's problem (don't advance). The fact that two "identical" smokes diverged is itself diagnostic — see the Bidirectional learning rule.

**The campaign is byte-identical to a recently-passing precedent.**
Reproducibility is implicit (the precedent is the prior reproducibility evidence). One smoke is enough to confirm; you don't need a fresh 2-consecutive check unless something about the environment changed.

---

## Documentation requirement

Every iteration produces a `SMOKE_ANALYSIS_NNN.md` (template at `templates/SMOKE_ANALYSIS.template.md`), with N = 001, 002, ... by iteration. The file records what was measured, what was predicted, what diverged, what was fixed, and the verdict for that iteration.

When the loop terminates, the campaign produces either:

- A one-paragraph summary appended to VERIFICATION.md under a `## Validation summary` section, OR
- A separate `VALIDATION_SUMMARY.md` if VERIFICATION.md has grown unwieldy.

Either form must include: how many iterations were run, what was learned across them, what was fixed, the final go/no-go decision, and a pointer to which SMOKE_ANALYSIS_NNN.md is the basis for the decision. Future agents and humans reading the campaign trail should be able to reconstruct the loop's reasoning without re-reading every iteration file.

---

## What a "satisfied" decision looks like in writing

Concrete example of the kind of paragraph that documents a successful loop termination — write something like this in VERIFICATION.md or VALIDATION_SUMMARY.md when you advance to production:

> **Validation summary.** Layer B smoke loop ran 3 iterations. Iteration 001 surfaced a density drift trending toward 1.18 g/cm³ over the smoke window, extrapolating to ~1.4 g/cm³ at production end — flagged red, would have invalidated the result. Diagnosis: NPT was running on a slab without `useConstantArea yes`, so the vacuum gap was being compressed. Fix applied: set `useConstantArea yes` in `production.namd`, line 47. Iteration 002 (after fix) showed density stable at 1.05 ± 0.01 g/cm³ across the smoke window — within the prior expectation for liquid NEC at 333 K. Iteration 003 (reproducibility re-smoke, byte-identical config) showed throughput 168 vs 171 ns/day (+1.8%), density traces overlay within noise, no new flags. All Layer A red items resolved; one yellow (patch grid sizing) explicitly accepted with rationale (smoke confirmed 4×4×3 grid stable across both reproducibility runs). Extrapolated production walltime: 18 hours, well under requested 24-hour walltime. Iteration budget: 3 of 5 used. Advancing to production. Priors updated: appended `slab-npt-needs-useConstantArea` pattern to `simulations/.priors.yaml` based on this loop's findings.

Note the structure: what was measured, what diverged from predictions, what was fixed (with file:line), the reproducibility evidence, the budget accounting, and the priors update. A future agent reading this can reconstruct the decision without re-running anything.

---

## Cross-references

- Parent skill: `compute-validation/SKILL.md`
- Layer A (verification): `workflows/verification.md`
- Layer B (smoke analysis): `workflows/smoke-analysis.md`
- VERIFICATION.md template: `templates/VERIFICATION.template.md`
- SMOKE_ANALYSIS.md template: `templates/SMOKE_ANALYSIS.template.md`
- priors.yaml schema: `templates/priors.template.yaml`
- Composing skill (orchestration of long runs, escalation propagation): `campaign-orchestration/SKILL.md`
