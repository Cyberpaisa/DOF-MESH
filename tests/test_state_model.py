"""
Tests for core.state_model — DOFAgentState Z3 symbolic state model.

Verifies:
- State creation with/without prefix
- Variable types (Real, Int, Bool)
- Base constraints (valid ranges)
- from_concrete for concrete scenarios
- as_dict serialization
- Prefix collision avoidance
"""

import unittest

import z3

from core.state_model import DOFAgentState


class TestDOFAgentStateCreation(unittest.TestCase):
    """Test state variable creation."""

    def test_create_default_prefix(self):
        """State with empty prefix has unprefixed variable names."""
        state = DOFAgentState()
        self.assertEqual(str(state.trust_score), "trust_score")
        self.assertEqual(str(state.hierarchy_level), "hierarchy_level")

    def test_create_with_prefix(self):
        """State with prefix has prefixed variable names."""
        state = DOFAgentState(prefix="pre_")
        self.assertEqual(str(state.trust_score), "pre_trust_score")
        self.assertEqual(str(state.hierarchy_level), "pre_hierarchy_level")
        self.assertEqual(str(state.threat_detected), "pre_threat_detected")

    def test_two_states_no_collision(self):
        """Pre and post states have different variable names."""
        pre = DOFAgentState(prefix="pre_")
        post = DOFAgentState(prefix="post_")
        self.assertNotEqual(str(pre.trust_score), str(post.trust_score))
        self.assertNotEqual(str(pre.hierarchy_level), str(post.hierarchy_level))

    def test_all_nine_variables_exist(self):
        """State has exactly 9 symbolic variables."""
        state = DOFAgentState()
        d = state.as_dict()
        self.assertEqual(len(d), 9)
        expected_keys = {
            "trust_score", "hierarchy_level", "threat_detected",
            "publish_allowed", "attestation_count", "cooldown_active",
            "governance_violation", "safety_score", "failure_rate",
        }
        self.assertEqual(set(d.keys()), expected_keys)


class TestDOFAgentStateTypes(unittest.TestCase):
    """Test Z3 variable types."""

    def test_trust_score_is_real(self):
        state = DOFAgentState()
        self.assertTrue(z3.is_real(state.trust_score))

    def test_hierarchy_level_is_int(self):
        state = DOFAgentState()
        self.assertTrue(z3.is_int(state.hierarchy_level))

    def test_threat_detected_is_bool(self):
        state = DOFAgentState()
        self.assertTrue(z3.is_bool(state.threat_detected))

    def test_publish_allowed_is_bool(self):
        state = DOFAgentState()
        self.assertTrue(z3.is_bool(state.publish_allowed))

    def test_attestation_count_is_int(self):
        state = DOFAgentState()
        self.assertTrue(z3.is_int(state.attestation_count))

    def test_cooldown_active_is_bool(self):
        state = DOFAgentState()
        self.assertTrue(z3.is_bool(state.cooldown_active))

    def test_governance_violation_is_bool(self):
        state = DOFAgentState()
        self.assertTrue(z3.is_bool(state.governance_violation))

    def test_safety_score_is_real(self):
        state = DOFAgentState()
        self.assertTrue(z3.is_real(state.safety_score))

    def test_failure_rate_is_real(self):
        state = DOFAgentState()
        self.assertTrue(z3.is_real(state.failure_rate))


class TestDOFAgentStateConstraints(unittest.TestCase):
    """Test base constraints."""

    def test_constraints_non_empty(self):
        state = DOFAgentState()
        constraints = state.constraints()
        self.assertGreater(len(constraints), 0)

    def test_constraints_are_satisfiable(self):
        """Base constraints alone should be satisfiable (valid states exist)."""
        state = DOFAgentState()
        solver = z3.Solver()
        for c in state.constraints():
            solver.add(c)
        self.assertEqual(solver.check(), z3.sat)

    def test_trust_below_zero_unsatisfiable(self):
        """trust_score < 0 violates base constraints."""
        state = DOFAgentState()
        solver = z3.Solver()
        for c in state.constraints():
            solver.add(c)
        solver.add(state.trust_score < 0)
        self.assertEqual(solver.check(), z3.unsat)

    def test_trust_above_one_unsatisfiable(self):
        """trust_score > 1 violates base constraints."""
        state = DOFAgentState()
        solver = z3.Solver()
        for c in state.constraints():
            solver.add(c)
        solver.add(state.trust_score > 1)
        self.assertEqual(solver.check(), z3.unsat)

    def test_hierarchy_below_zero_unsatisfiable(self):
        state = DOFAgentState()
        solver = z3.Solver()
        for c in state.constraints():
            solver.add(c)
        solver.add(state.hierarchy_level < 0)
        self.assertEqual(solver.check(), z3.unsat)

    def test_hierarchy_above_three_unsatisfiable(self):
        state = DOFAgentState()
        solver = z3.Solver()
        for c in state.constraints():
            solver.add(c)
        solver.add(state.hierarchy_level > 3)
        self.assertEqual(solver.check(), z3.unsat)

    def test_negative_attestation_count_unsatisfiable(self):
        state = DOFAgentState()
        solver = z3.Solver()
        for c in state.constraints():
            solver.add(c)
        solver.add(state.attestation_count < 0)
        self.assertEqual(solver.check(), z3.unsat)

    def test_safety_score_in_range(self):
        """safety_score must be in [0, 1]."""
        state = DOFAgentState()
        solver = z3.Solver()
        for c in state.constraints():
            solver.add(c)
        solver.add(state.safety_score > 1)
        self.assertEqual(solver.check(), z3.unsat)

    def test_failure_rate_in_range(self):
        state = DOFAgentState()
        solver = z3.Solver()
        for c in state.constraints():
            solver.add(c)
        solver.add(state.failure_rate < 0)
        self.assertEqual(solver.check(), z3.unsat)


class TestDOFAgentStateFromConcrete(unittest.TestCase):
    """Test from_concrete factory."""

    def test_from_concrete_default_values(self):
        """Default concrete state is satisfiable."""
        constraints, state = DOFAgentState.from_concrete()
        solver = z3.Solver()
        for c in state.constraints():
            solver.add(c)
        for c in constraints:
            solver.add(c)
        self.assertEqual(solver.check(), z3.sat)

    def test_from_concrete_custom_values(self):
        """Custom concrete state with valid values is satisfiable."""
        constraints, state = DOFAgentState.from_concrete(
            trust_score=0.5, hierarchy_level=2, threat_detected=True,
            publish_allowed=False, attestation_count=3,
        )
        solver = z3.Solver()
        for c in state.constraints():
            solver.add(c)
        for c in constraints:
            solver.add(c)
        self.assertEqual(solver.check(), z3.sat)

    def test_from_concrete_invalid_trust_unsatisfiable(self):
        """trust_score=1.5 violates base constraints."""
        constraints, state = DOFAgentState.from_concrete(trust_score=1.5)
        solver = z3.Solver()
        for c in state.constraints():
            solver.add(c)
        for c in constraints:
            solver.add(c)
        self.assertEqual(solver.check(), z3.unsat)

    def test_from_concrete_invalid_hierarchy_unsatisfiable(self):
        """hierarchy_level=5 violates base constraints."""
        constraints, state = DOFAgentState.from_concrete(hierarchy_level=5)
        solver = z3.Solver()
        for c in state.constraints():
            solver.add(c)
        for c in constraints:
            solver.add(c)
        self.assertEqual(solver.check(), z3.unsat)


class TestDOFAgentStateAsDict(unittest.TestCase):
    """Test as_dict serialization."""

    def test_as_dict_returns_dict(self):
        state = DOFAgentState()
        d = state.as_dict()
        self.assertIsInstance(d, dict)

    def test_as_dict_values_are_z3(self):
        state = DOFAgentState()
        for k, v in state.as_dict().items():
            self.assertIsInstance(v, z3.ExprRef)

    def test_as_dict_with_prefix_has_prefix_in_str(self):
        state = DOFAgentState(prefix="test_")
        for v in state.as_dict().values():
            self.assertTrue(str(v).startswith("test_"))


if __name__ == "__main__":
    unittest.main()
