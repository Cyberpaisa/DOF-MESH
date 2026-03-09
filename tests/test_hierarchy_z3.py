"""
Tests for core.hierarchy_z3 — Z3 verification of enforce_hierarchy patterns.

Verifies:
- Pattern loading from core.governance
- Individual pattern → Z3 conversion
- all_patterns_z3 AND formula
- verify_hierarchy_inviolable returns PROVEN
- find_weakest_pattern consistency
- Category counts match governance.py
"""

import unittest

import z3

from core.state_model import DOFAgentState
from core.hierarchy_z3 import HierarchyZ3, HierarchyVerificationResult
from core.governance import (
    _SYSTEM_OVERRIDE_PATTERNS,
    _RESPONSE_VIOLATION_PATTERNS,
)


class TestHierarchyZ3PatternLoading(unittest.TestCase):
    """Test that patterns are loaded correctly from governance."""

    def test_override_patterns_loaded(self):
        h = HierarchyZ3()
        self.assertEqual(len(h.override_patterns), len(_SYSTEM_OVERRIDE_PATTERNS))

    def test_violation_patterns_loaded(self):
        h = HierarchyZ3()
        self.assertEqual(len(h.violation_patterns), len(_RESPONSE_VIOLATION_PATTERNS))

    def test_total_patterns_sum(self):
        h = HierarchyZ3()
        expected = len(_SYSTEM_OVERRIDE_PATTERNS) + len(_RESPONSE_VIOLATION_PATTERNS)
        self.assertEqual(h.total_patterns, expected)

    def test_all_patterns_concatenated(self):
        h = HierarchyZ3()
        self.assertEqual(len(h.all_patterns), h.total_patterns)

    def test_two_categories(self):
        """enforce_hierarchy has exactly 2 pattern categories."""
        h = HierarchyZ3()
        self.assertGreater(len(h.override_patterns), 0)
        self.assertGreater(len(h.violation_patterns), 0)


class TestHierarchyZ3PatternConversion(unittest.TestCase):
    """Test individual pattern → Z3 conversion."""

    def test_first_override_pattern_to_z3(self):
        h = HierarchyZ3()
        state = DOFAgentState()
        formula = h.pattern_to_z3(0, state)
        self.assertTrue(z3.is_bool(formula))

    def test_first_violation_pattern_to_z3(self):
        h = HierarchyZ3()
        state = DOFAgentState()
        idx = len(h.override_patterns)  # first violation pattern
        formula = h.pattern_to_z3(idx, state)
        self.assertTrue(z3.is_bool(formula))

    def test_last_pattern_to_z3(self):
        h = HierarchyZ3()
        state = DOFAgentState()
        formula = h.pattern_to_z3(h.total_patterns - 1, state)
        self.assertTrue(z3.is_bool(formula))

    def test_invalid_pattern_id_raises(self):
        h = HierarchyZ3()
        state = DOFAgentState()
        with self.assertRaises(ValueError):
            h.pattern_to_z3(-1, state)
        with self.assertRaises(ValueError):
            h.pattern_to_z3(h.total_patterns, state)

    def test_pattern_implies_no_publish(self):
        """If a pattern fires, publish must be blocked."""
        h = HierarchyZ3()
        state = DOFAgentState()

        for i in range(h.total_patterns):
            solver = z3.Solver()
            for c in state.constraints():
                solver.add(c)
            # Pattern fires
            solver.add(h._all_vars[i])
            # Pattern constraint holds
            solver.add(h.pattern_to_z3(i, state))
            # Try to publish anyway
            solver.add(state.publish_allowed)

            self.assertEqual(solver.check(), z3.unsat,
                             f"Pattern {i} ({h.all_patterns[i]}) allows publish")


class TestHierarchyZ3AllPatterns(unittest.TestCase):
    """Test all_patterns_z3 combined formula."""

    def test_all_patterns_z3_is_bool(self):
        h = HierarchyZ3()
        state = DOFAgentState()
        formula = h.all_patterns_z3(state)
        self.assertTrue(z3.is_bool(formula))

    def test_all_patterns_satisfiable_when_no_patterns_fire(self):
        """If no pattern fires, all_patterns_z3 is trivially satisfied."""
        h = HierarchyZ3()
        state = DOFAgentState()

        solver = z3.Solver()
        for c in state.constraints():
            solver.add(c)
        solver.add(h.all_patterns_z3(state))
        # No pattern vars set to True
        for v in h._all_vars:
            solver.add(z3.Not(v))

        self.assertEqual(solver.check(), z3.sat)


class TestHierarchyZ3Verification(unittest.TestCase):
    """Test verify_hierarchy_inviolable."""

    def test_hierarchy_is_proven(self):
        h = HierarchyZ3()
        result = h.verify_hierarchy_inviolable()
        self.assertEqual(result.status, "PROVEN")

    def test_result_has_pattern_count(self):
        h = HierarchyZ3()
        result = h.verify_hierarchy_inviolable()
        self.assertEqual(result.patterns_checked, h.total_patterns)

    def test_result_has_category_count(self):
        h = HierarchyZ3()
        result = h.verify_hierarchy_inviolable()
        self.assertEqual(result.categories_checked, 2)

    def test_result_no_counterexample(self):
        h = HierarchyZ3()
        result = h.verify_hierarchy_inviolable()
        self.assertIsNone(result.counterexample)

    def test_result_has_time(self):
        h = HierarchyZ3()
        result = h.verify_hierarchy_inviolable()
        self.assertGreater(result.verification_time_ms, 0)


class TestHierarchyZ3WeakestPattern(unittest.TestCase):
    """Test find_weakest_pattern."""

    def test_no_weak_patterns(self):
        """All patterns should be individually strong."""
        h = HierarchyZ3()
        result = h.find_weakest_pattern()
        self.assertIsNone(result)


class TestHierarchyVerificationResultDataclass(unittest.TestCase):
    """Test HierarchyVerificationResult structure."""

    def test_dataclass_fields(self):
        r = HierarchyVerificationResult(
            status="PROVEN",
            patterns_checked=42,
            categories_checked=2,
            counterexample=None,
            verification_time_ms=10.0,
        )
        self.assertEqual(r.status, "PROVEN")
        self.assertEqual(r.patterns_checked, 42)
        self.assertEqual(r.categories_checked, 2)
        self.assertIsNone(r.counterexample)
        self.assertIsNone(r.weakest_pattern_id)


if __name__ == "__main__":
    unittest.main()
