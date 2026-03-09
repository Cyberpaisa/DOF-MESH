"""
Tests for core.agent_output — AgentOutput data model.

Verifies:
- OutputType enum values
- AgentOutput creation and schema validation
- Z3 constraint generation for each output type
"""

import unittest

import z3

from core.agent_output import AgentOutput, OutputType


class TestOutputType(unittest.TestCase):
    """Test OutputType enum."""

    def test_all_types_exist(self):
        expected = {"trust_score", "promotion", "demotion",
                    "threat_class", "mitigation", "pattern_match"}
        actual = {t.value for t in OutputType}
        self.assertEqual(actual, expected)


class TestAgentOutputValidation(unittest.TestCase):
    """Test schema validation."""

    def test_valid_output(self):
        o = AgentOutput(
            output_type=OutputType.TRUST_SCORE_ASSIGNMENT,
            agent_id="agent1",
            proposed_value=0.85,
            evidence={"source": "benchmark"},
            confidence=0.9,
        )
        self.assertTrue(o.validate_schema())

    def test_empty_agent_id_invalid(self):
        o = AgentOutput(
            output_type=OutputType.TRUST_SCORE_ASSIGNMENT,
            agent_id="",
            proposed_value=0.5,
            evidence={},
        )
        self.assertFalse(o.validate_schema())

    def test_none_value_invalid(self):
        o = AgentOutput(
            output_type=OutputType.TRUST_SCORE_ASSIGNMENT,
            agent_id="agent1",
            proposed_value=None,
            evidence={},
        )
        self.assertFalse(o.validate_schema())

    def test_negative_confidence_invalid(self):
        o = AgentOutput(
            output_type=OutputType.TRUST_SCORE_ASSIGNMENT,
            agent_id="agent1",
            proposed_value=0.5,
            evidence={},
            confidence=-0.1,
        )
        self.assertFalse(o.validate_schema())

    def test_confidence_above_one_invalid(self):
        o = AgentOutput(
            output_type=OutputType.TRUST_SCORE_ASSIGNMENT,
            agent_id="agent1",
            proposed_value=0.5,
            evidence={},
            confidence=1.5,
        )
        self.assertFalse(o.validate_schema())


class TestAgentOutputZ3Constraints(unittest.TestCase):
    """Test Z3 constraint generation."""

    def test_trust_score_constraints(self):
        o = AgentOutput(
            output_type=OutputType.TRUST_SCORE_ASSIGNMENT,
            agent_id="a1",
            proposed_value=0.5,
            evidence={},
        )
        constraints = o.as_z3_constraints()
        self.assertGreater(len(constraints), 0)

    def test_promotion_constraints(self):
        o = AgentOutput(
            output_type=OutputType.AGENT_PROMOTION,
            agent_id="a1",
            proposed_value=2,
            evidence={"current_level": 1},
        )
        constraints = o.as_z3_constraints()
        self.assertGreater(len(constraints), 0)

    def test_pattern_match_constraints(self):
        o = AgentOutput(
            output_type=OutputType.PATTERN_MATCH_ASSERTION,
            agent_id="a1",
            proposed_value=5,
            evidence={},
        )
        constraints = o.as_z3_constraints()
        # Pattern ID in [0, 11]
        solver = z3.Solver()
        for c in constraints:
            solver.add(c)
        self.assertEqual(solver.check(), z3.sat)

    def test_pattern_match_out_of_range(self):
        """Pattern ID 15 should be accepted by constraint (it's just IntVal)."""
        o = AgentOutput(
            output_type=OutputType.PATTERN_MATCH_ASSERTION,
            agent_id="a1",
            proposed_value=15,
            evidence={},
        )
        constraints = o.as_z3_constraints()
        solver = z3.Solver()
        for c in constraints:
            solver.add(c)
        # IntVal(15) <= 11 is False, so constraints are unsat
        self.assertEqual(solver.check(), z3.unsat)


if __name__ == "__main__":
    unittest.main()
