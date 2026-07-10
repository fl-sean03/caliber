#!/usr/bin/env python3
"""
Unit tests for scripts/lint_sim_input.py (EV-A5, rebase-2026-07-02).

The QE empty-input case reproduces the historical 2026-01-17 CRASH signature:
an empty `input_tmp.in` fed to pw.x, which aborted with
'read_namelists [...] could not find namelist &control' (see repo-root CRASH
debris and docs/rebase/CRASH_POSTMORTEM_20260117.md).

Run: python -m pytest tests/test_lint_sim_input.py  (or python tests/test_lint_sim_input.py)
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from lint_sim_input import lint_qe, lint_lammps  # noqa: E402

VALID_QE = """\
&control
    calculation = 'scf'
    prefix = 'si'
    pseudo_dir = './'
/
&system
    ibrav = 2, celldm(1) = 10.2, nat = 2, ntyp = 1,
    ecutwfc = 40
/
&electrons
    conv_thr = 1.0d-8
/
ATOMIC_SPECIES
 Si 28.086 Si.pbe-n-rrkjus_psl.1.0.0.UPF
ATOMIC_POSITIONS alat
 Si 0.00 0.00 0.00
 Si 0.25 0.25 0.25
K_POINTS automatic
 4 4 4 0 0 0
"""

VALID_LAMMPS = """\
units       lj
atom_style  atomic
lattice     fcc 0.8442
region      box block 0 5 0 5 0 5
create_box  1 box
create_atoms 1 box
mass        1 1.0
pair_style  lj/cut 2.5
pair_coeff  1 1 1.0 1.0 2.5
fix         1 all nve
run         100
"""


class TestQELint(unittest.TestCase):
    def test_empty_input_blocked_crash_class(self):
        """The exact 2026-01-17 CRASH reproduction: empty input must be blocked."""
        problems = lint_qe("")
        self.assertTrue(problems, "empty QE input must be blocked")
        self.assertIn("&control", problems[0])

    def test_whitespace_only_blocked(self):
        self.assertTrue(lint_qe("   \n\t\n"))

    def test_control_not_first_blocked(self):
        bad = VALID_QE.replace("&control", "&kontrol", 1)
        problems = lint_qe(bad)
        self.assertTrue(any("&control" in p for p in problems))

    def test_valid_input_passes(self):
        self.assertEqual(lint_qe(VALID_QE), [])


class TestLAMMPSLint(unittest.TestCase):
    def test_empty_blocked(self):
        self.assertTrue(lint_lammps(""))

    def test_pair_style_without_units_blocked(self):
        self.assertTrue(lint_lammps("pair_style eam/alloy\nrun 100\n"))

    def test_units_pair_mismatch_blocked(self):
        problems = lint_lammps("units real\npair_style eam/alloy\nrun 100\n")
        self.assertTrue(any("eam/alloy" in p for p in problems))

    def test_valid_input_passes(self):
        self.assertEqual(lint_lammps(VALID_LAMMPS), [])


if __name__ == "__main__":
    unittest.main()
