"""
Tests for core.boundary — Z3-powered boundary value generation.

Verifies:
- find_boundary_values returns valid float values
- find_minimal_violation finds counterexamples
- enumerate_edge_cases generates correct combinations
- Edge cases respect governance rules
"""

import unittest

import z3

from core.boundary import BoundaryEngine
from core.state_model import DOFAgentState


class TestBoundaryValues(unittest.TestCase):
    """Test find_boundary_values."""

    def setUp(self):
        self.engine = BoundaryEngine()

    def test_simple_threshold(self):
        """Find boundary values around x > 0.4."""
        x = z3.Real("x")
        values = self.engine.find_boundary_values(x > z3.RealVal("0.4"), x)
        self.assertIsInstance(values, list)
        self.assertGreater(len(values), 0)

    def test_all_values_in_range(self):
        """All returned values must be in [0, 1]."""
        x = z3.Real("x")
        values = self.engine.find_boundary_values(x > z3.RealVal("0.8"), x)
        for v in values:
            self.assertGreaterEqual(v, 0.0)
            self.assertLessEqual(v, 1.0)

    def test_values_are_sorted(self):
        """Returned values must be sorted ascending."""
        x = z3.Real("x")
        values = self.engine.find_boundary_values(x > z3.RealVal("0.5"), x)
        self.assertEqual(values, sorted(values))

    def test_unsatisfiable_constraint(self):
        """Unsatisfiable constraint returns empty list."""
        x = z3.Real("x")
        # x > 1 AND x in [0,1] → unsatisfiable
        values = self.engine.find_boundary_values(
            z3.And(x > 1, x < 0), x
        )
        self.assertEqual(values, [])

    def test_always_true_constraint(self):
        """Always-true constraint returns single value."""
        x = z3.Real("x")
        # x >= 0 is always satisfiable in [0,1], and NOT(x >= 0) is unsat in [0,1]
        values = self.engine.find_boundary_values(x >= 0, x)
        # Should return at least 1 value (sat_val) since negation is unsat in [0,1]
        self.assertGreaterEqual(len(values), 1)

    def test_n_parameter_limits_output(self):
        """n parameter limits the number of values."""
        x = z3.Real("x")
        values = self.engine.find_boundary_values(x > z3.RealVal("0.5"), x, n=3)
        self.assertLessEqual(len(values), 3)

    def test_values_are_floats(self):
        """All returned values must be floats."""
        x = z3.Real("x")
        values = self.engine.find_boundary_values(x > z3.RealVal("0.4"), x)
        for v in values:
            self.assertIsInstance(v, float)

    def test_boundary_includes_zero(self):
        """Boundary values should include 0.0."""
        x = z3.Real("x")
        values = self.engine.find_boundary_values(x > z3.RealVal("0.5"), x, n=10)
        if len(values) >= 3:
            self.assertIn(0.0, values)


class TestMinimalViolation(unittest.TestCase):
    """Test find_minimal_violation."""

    def setUp(self):
        self.engine = BoundaryEngine()

    def test_satisfiable_negation(self):
        """Find a violation when constraint can be negated."""
        x = z3.Real("x")
        result = self.engine.find_minimal_violation([x > z3.RealVal("0.5")])
        self.assertIsNotNone(result)
        self.assertIsInstance(result, dict)

    def test_tautology_no_violation(self):
        """Tautology has no violation."""
        x = z3.Real("x")
        result = self.engine.find_minimal_violation([z3.Or(x > 0, x <= 0)])
        self.assertIsNone(result)

    def test_multiple_constraints(self):
        """Multiple constraints can still be violated."""
        x = z3.Real("x")
        result = self.engine.find_minimal_violation([
            x > z3.RealVal("0.3"),
            x < z3.RealVal("0.7"),
        ])
        # NOT(x > 0.3 AND x < 0.7) is satisfiable
        self.assertIsNotNone(result)

    def test_result_contains_variable_names(self):
        """Result dict should contain variable names as keys."""
        x = z3.Real("my_var")
        result = self.engine.find_minimal_violation([x > z3.RealVal("0.5")])
        if result:
            self.assertTrue(any("my_var" in k for k in result.keys()))


class TestEnumerateEdgeCases(unittest.TestCase):
    """Test enumerate_edge_cases."""

    def setUp(self):
        self.engine = BoundaryEngine()
        self.state = DOFAgentState()

    def test_returns_list(self):
        cases = self.engine.enumerate_edge_cases(self.state)
        self.assertIsInstance(cases, list)

    def test_non_empty(self):
        cases = self.engine.enumerate_edge_cases(self.state)
        self.assertGreater(len(cases), 0)

    def test_each_case_is_dict(self):
        cases = self.engine.enumerate_edge_cases(self.state)
        for case in cases:
            self.assertIsInstance(case, dict)

    def test_expected_count(self):
        """8 trust × 4 levels × 2 threat × 2 cooldown = 128."""
        cases = self.engine.enumerate_edge_cases(self.state)
        self.assertEqual(len(cases), 128)

    def test_trust_score_range(self):
        """All trust scores must be in [0, 1]."""
        cases = self.engine.enumerate_edge_cases(self.state)
        for case in cases:
            self.assertGreaterEqual(case["trust_score"], 0.0)
            self.assertLessEqual(case["trust_score"], 1.0)

    def test_hierarchy_range(self):
        """Hierarchy levels must be in {0, 1, 2, 3}."""
        cases = self.engine.enumerate_edge_cases(self.state)
        for case in cases:
            self.assertIn(case["hierarchy_level"], [0, 1, 2, 3])

    def test_publish_blocked_when_threat(self):
        """If threat_detected, publish_allowed must be False."""
        cases = self.engine.enumerate_edge_cases(self.state)
        for case in cases:
            if case["threat_detected"]:
                self.assertFalse(case["publish_allowed"],
                                 f"Publish allowed with threat: {case}")

    def test_publish_blocked_when_cooldown(self):
        """If cooldown_active, publish_allowed must be False."""
        cases = self.engine.enumerate_edge_cases(self.state)
        for case in cases:
            if case["cooldown_active"]:
                self.assertFalse(case["publish_allowed"],
                                 f"Publish allowed during cooldown: {case}")

    def test_no_attestations_when_low_trust(self):
        """If trust < 0.4, attestation_count must be 0."""
        cases = self.engine.enumerate_edge_cases(self.state)
        for case in cases:
            if case["trust_score"] < 0.4:
                self.assertEqual(case["attestation_count"], 0)

    def test_all_required_keys(self):
        """Each case must have all required keys."""
        required = {"trust_score", "hierarchy_level", "threat_detected",
                     "cooldown_active", "publish_allowed", "attestation_count",
                     "governance_violation", "failure_rate", "safety_score"}
        cases = self.engine.enumerate_edge_cases(self.state)
        for case in cases:
            self.assertEqual(set(case.keys()), required)


class TestBoundaryEngineInit(unittest.TestCase):
    """Test BoundaryEngine construction."""

    def test_default_timeout(self):
        engine = BoundaryEngine()
        self.assertEqual(engine.timeout_ms, 5000)

    def test_custom_timeout(self):
        engine = BoundaryEngine(timeout_ms=1000)
        self.assertEqual(engine.timeout_ms, 1000)


if __name__ == "__main__":
    unittest.main()
