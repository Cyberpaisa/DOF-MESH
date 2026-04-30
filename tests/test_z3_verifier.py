"""
Tests for core/z3_verifier.py — Z3 formal verification of DOF invariants.
"""

import os
import sys
import json
import tempfile
import unittest
from unittest.mock import patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from core.z3_verifier import Z3Verifier, PROOFS_FILE


class TestGCRInvariant(unittest.TestCase):
    """GCR(f) = 1.0 must be formally verified as invariant."""

    def test_gcr_invariant_verified(self):
        verifier = Z3Verifier()
        result = verifier.prove_gcr_invariant()
        self.assertEqual(result.result, "VERIFIED")
        self.assertEqual(result.theorem_name, "GCR_INVARIANT")
        self.assertGreater(result.proof_time_ms, 0)
        self.assertIn("independent", result.description.lower())


class TestSSFormula(unittest.TestCase):
    """SS(f) = 1 - f^3 must be formally verified."""

    def test_ss_formula_verified(self):
        verifier = Z3Verifier()
        result = verifier.prove_ss_formula()
        self.assertEqual(result.result, "VERIFIED")
        self.assertEqual(result.theorem_name, "SS_FORMULA")

    def test_ss_monotonicity_verified(self):
        verifier = Z3Verifier()
        result = verifier.prove_ss_monotonicity()
        self.assertEqual(result.result, "VERIFIED")
        self.assertEqual(result.theorem_name, "SS_MONOTONICITY")

    def test_ss_boundaries_verified(self):
        verifier = Z3Verifier()
        result = verifier.prove_ss_boundaries()
        self.assertEqual(result.result, "VERIFIED")
        self.assertEqual(result.theorem_name, "SS_BOUNDARIES")


class TestBrokenInvariant(unittest.TestCase):
    """Intentionally broken invariant must produce COUNTEREXAMPLE_FOUND."""

    def test_broken_invariant_caught(self):
        verifier = Z3Verifier()
        result = verifier.prove_broken_invariant()
        self.assertEqual(result.result, "COUNTEREXAMPLE_FOUND")
        self.assertEqual(result.theorem_name, "BROKEN_INVARIANT_SS_F2")
        self.assertIn("counterexample", result.details.lower())


class TestVerifyAll(unittest.TestCase):
    """verify_all() runs all proofs and saves results."""

    def test_verify_all_returns_4_results(self):
        verifier = Z3Verifier()
        results = verifier.verify_all()
        self.assertEqual(len(results), 4)
        verified = [r for r in results if r.result == "VERIFIED"]
        self.assertEqual(len(verified), 4)

    def test_verify_all_saves_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_proofs_file = os.path.join(tmpdir, "z3_proofs.json")
            with patch("core.z3_verifier.PROOFS_FILE", temp_proofs_file):
                verifier = Z3Verifier()
                verifier.verify_all()
                self.assertTrue(os.path.exists(temp_proofs_file))

                with open(temp_proofs_file) as f:
                    data = json.load(f)

        self.assertIn("proofs", data)
        self.assertIn("summary", data)
        self.assertIn("z3_version", data)
        self.assertEqual(data["summary"]["total"], 4)
        self.assertEqual(data["summary"]["verified"], 4)


class TestProofResultSchema(unittest.TestCase):
    """Verify ProofResult has all required fields."""

    def test_proof_result_fields(self):
        verifier = Z3Verifier()
        result = verifier.prove_gcr_invariant()

        self.assertIsInstance(result.theorem_name, str)
        self.assertIn(result.result, ("VERIFIED", "COUNTEREXAMPLE_FOUND"))
        self.assertIsInstance(result.proof_time_ms, float)
        self.assertIsInstance(result.z3_version, str)
        self.assertIsInstance(result.description, str)
        self.assertTrue(len(result.z3_version) > 0)


class TestUnknownRateMonitor(unittest.TestCase):
    """Z3 unknown rate monitor must detect silent failures and enter degraded mode."""

    def test_handle_sat_returns_pass(self):
        import z3
        verifier = Z3Verifier()
        result = verifier._handle_z3_result(z3.sat)
        self.assertEqual(result, "PASS")

    def test_handle_unsat_returns_fail(self):
        import z3
        verifier = Z3Verifier()
        result = verifier._handle_z3_result(z3.unsat)
        self.assertEqual(result, "FAIL")

    def test_handle_unknown_returns_fail_not_pass(self):
        """z3.unknown must NEVER be treated as PASS — forced to FAIL."""
        import z3
        verifier = Z3Verifier()
        result = verifier._handle_z3_result(z3.unknown)
        self.assertEqual(result, "FAIL")

    def test_unknown_rate_zero_on_fresh_verifier(self):
        verifier = Z3Verifier()
        self.assertEqual(verifier.unknown_rate(), 0.0)

    def test_unknown_rate_increases_with_unknowns(self):
        import z3
        verifier = Z3Verifier()
        verifier._handle_z3_result(z3.sat)
        verifier._handle_z3_result(z3.sat)
        verifier._handle_z3_result(z3.unknown)
        # 1 unknown out of 3 = 33%
        self.assertAlmostEqual(verifier.unknown_rate(), 1/3, places=5)

    def test_no_degraded_mode_below_threshold(self):
        import z3
        verifier = Z3Verifier()
        # Feed 99 sat + 0 unknown → rate = 0%
        for _ in range(99):
            verifier._handle_z3_result(z3.sat)
        self.assertFalse(verifier.is_degraded())

    def test_degraded_mode_triggered_above_threshold(self):
        import z3
        verifier = Z3Verifier()
        # Feed 2 unknowns + 1 sat → rate = 2/3 > 1%
        verifier._handle_z3_result(z3.unknown)
        verifier._handle_z3_result(z3.unknown)
        verifier._handle_z3_result(z3.sat)
        self.assertTrue(verifier.is_degraded())

    def test_verify_all_skips_when_degraded(self):
        import z3
        verifier = Z3Verifier()
        # Force degraded mode
        verifier._handle_z3_result(z3.unknown)
        verifier._handle_z3_result(z3.unknown)
        verifier._handle_z3_result(z3.sat)
        self.assertTrue(verifier.is_degraded())
        results = verifier.verify_all()
        # Should return empty (skipped proofs)
        self.assertEqual(len(results), 0)


if __name__ == "__main__":
    unittest.main()
