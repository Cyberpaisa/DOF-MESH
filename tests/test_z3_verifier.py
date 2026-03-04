"""
Tests for core/z3_verifier.py — Z3 formal verification of DOF invariants.
"""

import os
import sys
import json
import unittest

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
        verifier = Z3Verifier()
        verifier.verify_all()
        self.assertTrue(os.path.exists(PROOFS_FILE))

        with open(PROOFS_FILE) as f:
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


if __name__ == "__main__":
    unittest.main()
