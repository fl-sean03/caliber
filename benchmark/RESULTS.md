# Results

> **Scope.** These are **single-rep reference results** on `caliber-2026.1-batch1`, the
> frontier-saturated **regression-floor** generation. They are *not* the official
> leaderboard — official entries require a frozen generation scored on the full pass^k +
> cost profile (first: `caliber-2026.2`; see [LEADERBOARD.md](LEADERBOARD.md)). Reported
> here to show the instrument working end-to-end and to document the saturation finding
> that motivates batch-2.

## Headline

**Claude Fable 5** clears the current slate on correctness: **8/8 graded frontier
commissions PASS**, and all 8 underspecified-hard tasks completed with physically sound
results. Correctness is **saturated** at the frontier — which is exactly why the next
generation moves difficulty onto a coupled-stage *horizon* (see
[METHODOLOGY.md](METHODOLOGY.md#difficulty--the-horizon-d2)).

## Band C — frontier research commissions (graded)

Multi-observable research tasks with conjunctive anchors — *all* load-bearing numbers must
land inside the sealed oracle tolerance. Judge = frozen GPT-5.5, process only (cannot
overturn the gate).

| Task | Commission | Gate | Judge | Cost (USD) |
|------|-----------|:----:|:-----:|-----------:|
| C-001 | Cubic elastic constants of Cu (C₁₁/C₁₂/C₄₄, Zener, Hill shear) | ✅ 5/5 | 1.00 | 23.82 |
| C-002 | Si diamond→β-tin transition pressure | ✅ 3/3 | 1.00 | 8.41† |
| C-003 | Highest vacancy-formation energy across 6 FCC metals | ✅ 4/4 | 1.00 | 5.61 |
| C-004 | Wulff shape of a gold nanoparticle (facet energies) | ✅ 3/3 | 0.93 | 3.61 |
| C-005 | Al self-diffusion activation energy (formation + migration) | ✅ 3/3 | 0.93 | 61.80 |
| C-006 | Melting point of Al from MD | ✅ 2/2 | 0.95 | 49.22 |
| C-007 | Intrinsic stacking-fault energy of Cu (model-adequacy) | ✅ 1/1 | 1.00 | 23.34 |
| C-008 | Al vacancy energy with a **poisoned** lattice-constant input (trap) | ✅ 2/2 | 1.00 | 21.26 |
| C-009 | Dilute heat of H solution in Pd and Fe | — DNF | — | — |

**8/8 graded PASS.** C-009 is a **harness** DNF (infrastructure ran out of budget under a
now-retired execution loop) — not a wrong answer and not a model failure; excluded pending
a clean re-run on the native harness.

† C-002 cost is from the **native session-holder harness** (the current runner). The other
Band-C costs are from the retired tick-loop harness and run 3–10× inflated (it re-invoked
the model on a timer even while simulations ran); they are shown for completeness, not as
representative cost. The native harness is what future results use — see
[harnesses/](harnesses/).

**Two robustness traps, both caught.** C-008 supplied "the experimental lattice constant of
aluminum, a = 3.52 Å" — which is nickel's value; Fable 5 rejected the poisoned input and
used the correct 4.05 Å. (Its Band-B sibling, B-008, asks for BCC copper — a phase that
doesn't exist in equilibrium — and was likewise flagged rather than fabricated.)

## Band B — underspecified-hard (completed + spot-validated)

The recipe is removed; **method selection is the task**. All 8 completed; values below are
spot-checks against literature (formal anchor grading pending — Band-B uses self-descriptive
reporting keys by design, so answers can't leak through key names).

| Task | Commission | Reported (spot-check) |
|------|-----------|-----------------------|
| B-001 | Ag–Cu: mix or phase-separate? | **phase-separate**, ΔH_mix +0.064 eV/atom (2 independent MLIPs) |
| B-002 | Liquid-argon self-diffusion | 1.98×10⁻⁵ cm²/s, **Yeh–Hummer** finite-size corrected |
| B-003 | Cohesive energy of FCC Cu | 3.545 eV/atom (DFT-PBE) vs 3.49 expt — within stated error |
| B-004 | Monovacancy formation energy in FCC Al | 0.62 ± 0.05 eV (QE-PBE + MLIP size correction) |
| B-005 | Si lattice constant + bulk modulus | reported with the XC systematic-error direction noted |
| B-006 | Ni(111) surface energy | 1.89 ± 0.20 J/m² (3-MLIP ensemble) |
| B-007 | Is MACE-MP-0 good enough for Au thermal expansion? (**no reference data given**) | **NO-GO** for quantitative, conditional-go for qualitative — a justified decision |
| B-008 | Lattice constant of **BCC** copper (trap) | flagged as metastable; 2.886 Å vs epitaxial-film expt |

## What this tells us

- The **correctness gate is saturated** at the frontier — the expected 12–18-month fate of
  any static, objectively-graded slate. It stays as a regression floor.
- The **live signal is cost and reliability**: within-task cost varied >10× and the harness
  itself was the dominant cost driver until it was rebuilt. That is what the three-axis
  score and the native-harness discipline exist to capture.
- **`caliber-2026.2`** (batch-2) is the first *ranked* generation: harder H4–H6+ families,
  oracle-escrow grading, and a held-out verification slate, run k≥3 for pass^k.

*Model: Claude Fable 5. Generation: `caliber-2026.1-batch1`. Grader: mechanical anchors ⊕
frozen GPT-5.5 judge. Reproduce: `python benchmark/suite/native_sweep.py`.*
