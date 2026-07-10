# Layer A — Verification (deep reasoning before any compute)

You're here because the agent in `compute-validation/SKILL.md` has been asked to verify a campaign before any compute is spent. This document is the workflow. The parent skill explains *why* and *where this fits*; this document explains *how to actually do it*.

> One-line restatement: **try to break the campaign on paper.** If you can find a failure here, you've saved hours of compute. If you can't, you've earned the right to spend a few minutes on a smoke run with much higher confidence.

Read the parent `compute-validation/SKILL.md` first. The 3-layer model and termination criteria live there. This document zooms into Layer A only.

---

## Mindset — falsify, don't validate

This is the single most important thing in this document, so it goes first.

**The goal is not to convince yourself the campaign will work.** The goal is to find the way it will fail. Assume there is a bug. Your job is to locate it before compute is spent.

Concretely, that means:

- For every parameter you read, ask "what would go wrong if this were tuned 10x in either direction? what regime is this assuming?"
- For every config inheritance ("we're reusing the NPT box from the last campaign"), ask "what was different about that campaign? has the system characteristics shifted enough that the inherited assumption no longer holds?"
- For every "this is just like the last one," ask "what's the *one thing* that's actually different, and is that one thing safe?"
- When you find yourself writing "this looks fine," stop. Replace it with "I checked X, Y, Z and could not find a failure mode under those checks." The first version invites confirmation bias; the second version is honest.
- If you have nothing flagged after 15 minutes of reading, you're not looking hard enough. Real campaigns almost always have at least one yellow item.

The agent's failure mode here is being too agreeable. Senior engineers reviewing junior engineers' campaign configs find issues 80% of the time on first read. If your verification is finding nothing, the prior should be that you're missing something, not that the campaign is unusually clean.

---

## The 8 categories

Walk these in order. Each one is a separate investigation; don't blur them together.

| # | Category | What you're looking for | How to investigate |
|---|---|---|---|
| 1 | Config integrity | Files exist; syntax parses; references resolve; values are *self-consistently* sensible | Read each config end-to-end; resolve every path/reference; cross-check values |
| 2 | Domain sanity | The protocol is well-posed for this system (physics for MD, statistics for ML, chemistry for QM) | Apply domain heuristics — see per-tool pages in `tools/<software>.md` |
| 3 | Computational sanity | Walltime, memory, throughput estimates match what's requested | Estimate from first principles; compare to request; flag mismatches |
| 4 | Pattern matching | Known-bad patterns in `priors.yaml` that this system matches | Load priors; for each pattern, evaluate match against current characteristics |
| 5 | Precedent comparison | What's different from the last successful campaign in this project? Why? Is that difference safe? | Find latest passing config; diff; rationalize each delta |
| 6 | Risk assessment | Top-3 ways this campaign could fail | Enumerate; for each, describe smoke-vs-production signature; map mitigation |
| 7 | External research | Unfamiliar regime, unusual protocol, novel parameter | WebSearch / WebFetch / forum reads; 30-minute hard cap unless extended |
| 8 | Output | The verification report itself | Write `VERIFICATION.md` with green/yellow/red items + rationales + mitigations |

The rest of this document is one section per category, with concrete heuristics.

---

### 1. Config integrity

The dumb checks first. Most "integrity" bugs are caught by syntax linters, but the *semantic* integrity bugs are the ones that bite.

**Mechanical checks:**

- Every file referenced in the deploy script exists at the expected path
- Every path in the config (PDB, PSF, parameter files, restart files, force-field files) resolves
- Syntax parses (run the tool's `--check` or `--dry-run` flag if it has one)
- All required environment variables are set in the submit script
- Submit script directives (walltime, memory, GPU count) are syntactically valid for the target scheduler

**Semantic checks (these are the ones that matter):**

- Does the timestep make sense for the integrator and constraints? E.g. NAMD with rigidBonds + 4 fs only valid if hydrogen mass repartitioning is *also* on; otherwise 2 fs.
- Do thermostat / barostat coupling constants make sense for the system size? Too tight → unphysical oscillations; too loose → no equilibration.
- Are output frequencies sane relative to total steps? If `dcdfreq=1000` and `numsteps=2000`, you'll only get 2 frames in your trajectory.
- Does `numsteps` match the intended physical duration? Quick check: numsteps × timestep × 1e-6 = duration in ns. Sanity-check against what the campaign's purpose is.
- Does the box size match the system contents? An empty box around 200 NEC molecules in a 75 Å z-extent will have density ≪ liquid density — does the protocol expect that?
- For chained pipelines: do the input files of stage N match the output files of stage N-1? Don't just assume the deploy script gets this right; read the pipeline.

**Heuristic:** if a parameter is set to a value you can't immediately rationalize from the system, dig in. "It was inherited from the template" is not a rationale. Either the value was deliberately chosen for this system (find the rationale) or it was carried over and may be wrong (find the carry-over and audit it).

---

### 2. Domain sanity

This is where domain expertise shows. The per-tool pages in `tools/<software>.md` give specific heuristics; this section is the framework.

**For MD:**

- Density at start: realistic? (For organic liquids, ρ ≈ 0.9–1.1 g/cm³. For Pt slabs, slab Pt fraction × Pt bulk density × layer count comparison.)
- Temperature: thermostat target physically meaningful? (Don't run NEC at 1000 K if you mean the bulk to be liquid; do run Pt at 1000 K if you mean to decorrelate but Pt must be fixed or it melts.)
- Pressure: NPT target compatible with the box geometry? (For slabs, full NPT will collapse the vacuum gap — need `useConstantArea yes` or a slab-aware barostat.)
- Force field: parameters cover all atom types in the system? Missing parameters are silent NaN factories.
- Initial velocity: assigned at correct temperature? Or relying on minimization + heating?
- Periodic boundary conditions: cell large enough to avoid self-image artifacts? For slabs: enough vacuum gap?

**For ML training:**

- Learning rate compatible with batch size? (Linear scaling rule, warmup applied?)
- Loss function expectations: known bounds, sane initial value
- Dataset shape matches model input
- Validation split present, drawn from same distribution
- Mixed precision settings consistent with target hardware

**For DFT:**

- k-point density appropriate for cell type (metallic vs insulator, slab z-direction)
- Plane-wave cutoff matches pseudopotential recommendations (≥1.5x suggested)
- Smearing scheme appropriate for system (Marzari-Vanderbilt for metals, Gaussian for insulators)
- Spin polarization on iff system requires it

If you don't know the domain, this is when external research (category 7) starts paying off.

---

### 3. Computational sanity

Estimate independently of what the submit script asks for, then compare.

**Walltime:**

```
walltime ≈ (atoms × steps) / throughput
```

Throughput numbers should live in the relevant `tools/<tool>.md`. For NAMD on A100: ~50–200 ns/day for 10–50k-atom systems with PME and rigid bonds. So a 50 ns production on 12k atoms ≈ 0.5–1 day. Compare against the requested walltime + restart frequency.

**GPU memory:**

```
mem_GB ≈ atoms_per_GPU × bytes_per_atom × overhead_factor
```

For NAMD: ~40–80 KB/atom in GPU memory (PME grids dominate for large boxes). So 12k atoms ≈ 0.5–1 GB before PME, well within an A100. For a 500k-atom system, you're at 20–40 GB and an A100 (40 GB) is borderline.

For ML training: model_params × bytes (4 for fp32, 2 for bf16) × 4–6x (gradients + optimizer states + activations).

**Throughput cross-check:**

- Look at recent NAMD log files in this project. What's actual ns/day? Multiply by walltime, see if `numsteps × dt` fits.
- For a fresh system, run with the most-similar prior throughput. If actual <50% of expected, you're misallocating.

**Heuristic:** if your independent estimate disagrees with the request by >2x, something is wrong. Either the estimate is wrong (you missed an overhead) or the request is wrong (over- or under-asking). Reconcile before submitting.

---

### 4. Pattern matching against priors

Every project should have a `priors.yaml` (template at `templates/priors.template.yaml`). It's a catalog of known failure patterns specific to this project's typical work.

**How priors.yaml is structured:**

```yaml
patterns:
  - id: namd-velocity-limit-on-flexible-water
    description: NAMD throws "atom velocity > limit" when flexible water + minimal minimization
    matches:
      - has_flexible_water: true
      - minimize_steps_below: 5000
    severity: high
    mitigation: "Increase minimize from 1000 to 10000 steps"
    references:
      - "campaigns/2026-04-12-cubic-npt/SMOKE_ANALYSIS_002.md"
  - id: slab-patch-grid-collapse
    description: NAMD GPU patch grid degenerates when slab z-thickness < 2x patch margin
    matches:
      - geometry: slab
      - z_extent_below: 25
    severity: high
    mitigation: "Increase vacuum padding so z >= 2 * margin + slab thickness"
```

**How to use it:**

1. Read every pattern in `priors.yaml`
2. For each pattern, evaluate its `matches` rules against the current campaign
3. For matched patterns, surface them in the report — even low-severity matches deserve mention
4. For high-severity matches, applying the mitigation is required, not optional. If the mitigation conflicts with another constraint, escalate.

**If the project doesn't have priors.yaml yet:** check the project's `AGENTS.md`, `HPC_PLAYBOOK.md`, or any "common failure modes" section for equivalent informal knowledge. Treat that as the priors for this verification, and consider creating a `priors.yaml` skeleton as part of the output.

**The point of priors.yaml is the bidirectional learning loop in the parent SKILL.md.** Every smoke that surfaces a new bug should append to priors. So a verification that doesn't load priors is throwing away the project's accumulated knowledge.

---

### 5. Precedent comparison

The most reliable way to find subtle bugs is to compare the current campaign to the last one that *worked*.

**Procedure:**

1. Find the most recent successful campaign in the same project / system family. Look at `simulations/<latest_passing>/`, the project's STATUS.md, the campaign-orchestration WORKFLOW.md files.
2. Diff the configs:
   ```
   diff simulations/last_passing/inputs/config.namd simulations/current/inputs/config.namd
   diff simulations/last_passing/deploy_hpc.sh simulations/current/deploy_hpc.sh
   ```
3. For *every* difference, ask:
   - Why is this different? (What changed about the science / hardware / protocol?)
   - Is the difference safe? (Does it preserve the invariants the last run depended on?)
   - Is there evidence the difference works? (Has it been smoked elsewhere? Or is this the first time?)

4. Any difference you can't rationalize is a red flag until you find the rationale. *Don't* accept differences as "must be intentional, the user changed it for a reason." That's confirmation bias. Find the reason.

**Common precedent-diff red flags:**

- A timestep changed without a comment
- A thermostat constant changed (often someone's edit got carried into a template)
- An output frequency that no longer matches what downstream analysis expects
- A new force-field parameter file added without provenance
- A walltime increased without explanation (often signals "the last run barely fit, this one will hit the wall")

If there's no precedent (this is the first campaign of its kind), say so explicitly in the verification report and lean harder on categories 2, 3, 4, 7.

---

### 6. Risk assessment

Enumerate the top-3 ways this campaign could fail. Be specific.

For each failure mode, fill out:

```
Risk: <name>
  Mechanism: <what physically happens>
  Smoke signature: <what would the smoke output show?>
  Production signature: <what would production output show?>
  Mitigation: <what's done in the config to prevent this?>
  Detection: <how would Layer B catch it?>
```

**Why this matters:** the next layer (Layer B smoke) is a measurement instrument. To use it well, you need to know in advance what you'd measure to detect each risk. If risk X has no clean smoke signature, the smoke can't catch it — you may need a more deliberate measurement protocol or a longer smoke.

**Heuristic:** if you can't think of 3 risks, you're not trying. Every MD campaign has at least: density drift, throughput collapse, restart-write failure. Every ML training has at least: gradient explosion, OOM in late epoch, learning rate collapse. Use the per-tool pages for tool-specific top-3 templates.

---

### 7. External research as needed

Most campaigns don't need this. Do it when:

- You're in a parameter regime nobody on the team has used before
- You're using an unfamiliar tool or unfamiliar feature of a familiar tool (e.g., NAMD-3 GPU-resident vs NAMD-2 CPU-with-GPU-offload)
- The system has unusual characteristics (very anisotropic box, unusual atom types, exotic force-field combination)
- You found something in priors / precedent diff that you don't understand and can't internally rationalize

**How:**

- Tool documentation (`pmewald` flag in NAMD docs, `useConstantArea` interaction with PME...)
- Project's WIKI / forums / mailing list archives
- Recent papers using the tool in this regime (how do they parameterize?)
- WebSearch for "<tool> <feature> slab" or "<tool> <bug>"

**When to stop:** 30-minute hard cap by default. If you spend more, you're either pulling on the wrong thread or this is a high-stakes campaign where the human should weigh in. For high-stakes, ask the user "should I extend research budget?" rather than silently spending an hour.

**What to record:** any external source you consult, with the specific finding that affected your conclusion. The verification report should cite these. Future verifications can short-circuit by reading that report.

---

### 8. Output — VERIFICATION.md

The output is a markdown file in the campaign directory. Format:

```markdown
# VERIFICATION — <campaign-name>

**Date:** YYYY-MM-DD
**Agent:** <model + identifier>
**Campaign config:** <path to primary config>
**Precedent compared against:** <path to last passing campaign>

## Summary

Overall: GREEN | YELLOW | RED

One paragraph stating the gist. Mention the highest-severity finding.

## Findings

### Category 1 — Config integrity
Status: GREEN/YELLOW/RED
- Findings (bulleted; cite line numbers and file paths)

### Category 2 — Domain sanity
Status: GREEN/YELLOW/RED
- Findings

### ... (one section per category)

## Risk register

| # | Risk | Mechanism | Smoke signature | Mitigation | Detection in Layer B |
|---|------|-----------|-----------------|------------|----------------------|
| 1 | ... | ... | ... | ... | ... |

## Mitigations applied to config

- Edit 1: <file:line> changed <X> from <A> to <B>. Rationale: <Y>.
- ...

## Open questions for human

(If any. Often empty for routine variants; non-empty for first-of-kind work.)

## Verdict

- [ ] All red items resolved
- [ ] Yellow items resolved or accepted with rationale
- [ ] Cleared to proceed to Layer B (smoke)

## References

- priors.yaml entries triggered: <ids>
- External sources consulted: <urls>
- Precedent campaign: <path>
```

This file gets read by humans, by future agents, and by the smoke-analysis layer (which compares its measurements to the predictions here). Write it with all three audiences in mind.

---

## How to use priors.yaml

The schema is in `templates/priors.template.yaml`. Each entry has:

- `id` — short slug, unique per project
- `description` — one sentence what the failure looks like
- `matches` — predicates for "does this campaign trigger this prior"
- `severity` — `low` | `medium` | `high`
- `mitigation` — concrete action that prevents it
- `references` — links to past VERIFICATION.md or SMOKE_ANALYSIS_NNN.md where this surfaced

**Loading priors:**

1. Read `<project>/.priors.yaml` (or wherever the project keeps it; check AGENTS.md)
2. Extract characteristics of the current campaign (geometry, system size, tool, parameters)
3. For each pattern, evaluate `matches` predicates against extracted characteristics
4. For matches, surface in VERIFICATION.md and apply mitigation

**Updating priors:**

If during verification you discover a new pattern (one that should have been catchable but wasn't because no prior existed), draft an addition to `priors.yaml` and surface it in the report. The next agent benefits.

---

## Pluralistic verification for high-stakes campaigns

For routine campaigns, one verification pass is enough. For high-stakes ones — long walltimes, paid backends, unique opportunity windows, or anything where failure would set back the project significantly — dispatch a second independent verification.

**When to dispatch a second verifier:**

- Walltime > 24 hr per job
- Paid backend with cap > $50
- Novel parameter regime (never run before in this project)
- Required for a deadline (failure means the deadline is missed)
- Anything the human flags as high-stakes

**How:**

1. Original agent produces `VERIFICATION.md`
2. Dispatch a fresh subagent with the same campaign + same priors but *no access* to the first VERIFICATION.md
3. Second agent produces `VERIFICATION_independent.md`
4. Compare the two:
   - Findings both surfaced → high-confidence findings, fix them
   - Findings only one surfaced → either a real catch the other missed, or a false alarm; reconcile by reading the rationale
   - Verdict mismatch (one says GREEN, other says YELLOW) → escalate to human

**Reconciling differences:**

Don't just take the union of findings. Read the rationale on each and decide whether each side's finding stands up to scrutiny. The goal is two perspectives → richer picture, not two checklists merged.

---

## Investigation discipline — when to dig deeper vs accept

The single biggest failure mode of this layer is *shallow investigation* — agent reads a config, sees no obvious red flag, declares green. Use these heuristics to decide when to keep digging:

**Dig deeper when:**

- A parameter value is unusual for the regime (high or low compared to typical) — find the rationale, even if it takes 10 minutes
- A precedent diff has differences you can't rationalize — treat as red flag until rationale found
- Something in priors triggered, even at low severity — investigate the match
- The system characteristics put it in a regime nobody on the team has used before — this is when external research pays
- You feel reluctant to flag something as YELLOW because "the user obviously knew what they were doing" — that's confirmation bias, dig in

**Accept and move on when:**

- You investigated, found a clear rationale (in code comments, in AGENTS.md, in a previous VERIFICATION.md, or by computation), and the rationale survives scrutiny
- The campaign is byte-identical to a precedent that passed both Layer A and Layer B; no diff to rationalize
- Domain expert (the human) explicitly stated the choice in a recent message

**Default verdict for first-time work:** YELLOW. Not GREEN. Even if you can't find a specific failure mode, the absence of evidence is not evidence of absence. Mark first-of-kind work as YELLOW and require human confirmation to advance.

**Default verdict for routine variants:** GREEN if all 8 categories passed cleanly; YELLOW if any one category had a finding that's resolvable but not yet resolved; RED if any high-severity finding remains.

**Chain reasoning:** when investigating, follow `claim → evidence → conclusion`. If you write "this is fine," your reasoning trail must be `claim: X is fine` → `evidence: <link to data, cite line, or reference>` → `conclusion: therefore X is fine`. If the evidence link is missing, the claim is unsupported.

---

## A worked example — the patch-grid scenario

To make this concrete, here's how Layer A would have caught a real bug that surfaced 2026-05-06 in the hydrogenation surfaces project. The bug: NAMD GPU production on a Pt slab failed with "Patch grid is too small in z" after ~10 ps because the box z-extent had compressed during NPT below the threshold where NAMD can decompose the patch grid for GPU offload.

What Layer A would have surfaced:

```markdown
### Category 2 — Domain sanity
Status: YELLOW

- Box z-extent at start of production: 48.3 Å (NPT-equilibrated value).
  - Slab thickness ~12 Å (5 Pt layers + small adsorbed NEC layer).
  - Vacuum gap ~36 Å.
- NAMD GPU patch margin (default `pairlistDist + 2`): ~14 Å.
- Patches in z ≈ floor(48.3 / 14) = 3.
- Concern: with only 3 patches in z, NAMD may not have enough granularity for GPU
  decomposition, especially if the vacuum gap allows imbalanced atom distribution.
- **Action:** verify patch grid sizing in smoke output (look for "PATCH GRID" line in
  log, expected: 4×4×3 or larger).

### Category 4 — Pattern matching
Status: GREEN (no priors.yaml entry for this pattern yet — DRAFT one below for
future runs)

- Suggested addition to priors.yaml:
  ```yaml
  - id: namd-slab-patch-grid-z-too-small
    description: NAMD GPU rejects patch grid when slab box z < ~14 Å × 4
    matches:
      - geometry: slab
      - z_extent_below: 56  # = 4 patches × 14 Å margin
      - tool: namd-3
      - gpu_resident: true
    severity: high
    mitigation: "Either increase vacuum padding to push z above 56 Å, or use
                 NAMD-2 CPU+GPU offload mode (no patch-grid constraint)"
  ```

### Category 5 — Precedent comparison
Status: YELLOW

- Last successful campaign: cubic NP NPT (simulations/npt-equilibration/cubic/).
  - That run had box z ≈ 110 Å — patch grid never an issue.
- Current slab campaign has z ≈ 48 Å — 2.3x smaller in z.
- This is a *qualitatively new regime* for NAMD GPU offload in this project. Flag.

### Risk register

| # | Risk | Mechanism | Smoke signature | Mitigation | Detection in Layer B |
|---|------|-----------|-----------------|------------|----------------------|
| 1 | Patch grid too small | NAMD GPU requires z/margin ≥ 4 | "PATCH GRID" line in log shows nz=3 or 2 | Increase vacuum padding | grep "PATCH GRID" smoke log |
| 2 | Density drift on slab | Vacuum gap collapses if NPT not constrained to z | Density rises >1.2 g/cm³ over smoke | useConstantArea yes (verify in config) | extract density vs time |
| 3 | Pt melting at 1000 K | Pt atoms not fixed during decorrelation | Pt atoms displace > 1 Å from lattice | All Pt B=1.0 in PDB (verify) | RMSD of Pt sublattice |
```

That's the kind of explicit, granular reasoning Layer A produces. The patch-grid risk is *predictable from the config* (z-extent + tool + GPU mode → patch grid math), but only if the agent does the math. The smoke would then either confirm the worry (NAMD log shows tight patch grid → fix the config before production) or refute it (patch grid is fine → advance).

The cost of this analysis is ~30 minutes. The cost of not doing it was ~10 hours of compute that crashed at the 10 ps mark.

---

## Common verification failure modes

These are the ways verification itself goes wrong. Watch for them in your own work.

**Investigates too shallowly.** Reads the config top-to-bottom, sees nothing obviously wrong, declares green. Symptom: VERIFICATION.md is short, has only "all checks passed" with no specifics. Fix: every section needs at least one specific finding, even if it's "checked X by computing Y, value is in expected range." Empty bullet lists are a smell.

**Confirms instead of falsifies.** Reads the config looking for reasons it'll work, not reasons it'll fail. Symptom: every parameter explained as "as expected." Fix: re-read with the explicit prompt "if I were to construct a counterexample where this fails, what parameter would I tune?"

**Doesn't load priors.yaml.** Either forgets, or the project doesn't have one and the agent doesn't check the alternative ("common failure modes" sections, AGENTS.md, recent VERIFICATION.md files). Fix: priors are mandatory input. If `priors.yaml` doesn't exist, you must check at least one alternative source and note it.

**Skips precedent comparison.** Hard to find the latest passing campaign, so the agent skips it. Symptom: VERIFICATION.md has no precedent diff section. Fix: precedent comparison is mandatory. If genuinely no precedent exists (first-of-kind), say so explicitly. Do not silently skip.

**Overclaims green.** Has YELLOW-worthy findings but talks itself into GREEN because "the campaign should work." Fix: default to YELLOW when in doubt. The cost of a YELLOW that should have been GREEN is "user spends 30s reading the rationale and approves." The cost of a GREEN that should have been YELLOW can be 10 hours of failed compute.

**Underclaims red.** Sees a clear failure mode and writes "GREEN with caveat." Fix: severity is determined by impact and detectability, not by hopefulness. If a finding would crash production, it's RED.

**Bundles findings.** Lumps multiple distinct findings into one. Symptom: a single bullet point with 3 unrelated issues. Fix: one finding = one bullet. The audit trail is more useful when each finding is separately addressable.

---

## When this layer is sufficient vs when smoke is essential

Layer A catches **predictable** failures — anything you can deduce from reading the config + applying domain knowledge + matching priors. That's a lot of failures, often >50% of the ones that would otherwise crash a production run.

Layer A does **not** catch **empirical** failures — bugs that only surface when the system actually runs. Examples:

- Slow density drift that's invisible in 100 steps but obvious over 10 ns
- A throughput collapse that only happens after the GPU's caches warm up in a particular pattern
- Energy drift from accumulated floating-point error
- Race conditions in multi-GPU runs that show up under specific load patterns
- Convergence failures in iterative solvers that depend on the initial state

That's why Layer B (smoke + analysis) exists. It runs cheaply enough to be a measurement, and it catches the empirical class.

**Don't try to catch empirical bugs in Layer A.** It's not what reasoning is good for. Note them in the risk register, predict their smoke signature, and let Layer B do the catching.

**Don't skip Layer B because Layer A was clean.** A clean Layer A means you're not aware of any predictable bugs — but the empirical class is still out there. Layer B is the only filter for it.

**Don't skip Layer A' (orchestration safety) because Layer A was clean.** Layer A reasons about *physics correctness*. Layer A' is the parallel sibling that reasons about *script + submission + chain safety* — the class of failure that lives in interactions between scheduler behavior, automation, and notification. A bulletproof physics config with a runaway resubmit loop is still a disaster. Both A and A' must pass before Layer B.

---

## Cross-references

- Parent skill: `compute-validation/SKILL.md`
- Sibling layer (orchestration safety): `workflows/orchestration-safety.md`
- Smoke layer: `workflows/smoke-analysis.md`
- Iteration discipline: `workflows/iteration-discipline.md`
- Per-tool signal extraction: `tools/<tool>.md`
- VERIFICATION.md template: `templates/VERIFICATION.template.md`
- ORCHESTRATION_CHECK.md template: `templates/ORCHESTRATION_CHECK.template.md`
- Priors schema: `templates/priors.template.yaml`
- Composing skill (where to run): `compute-strategy/SKILL.md`
- Composing skill (long-running state + runtime monitoring): `campaign-orchestration/SKILL.md`
