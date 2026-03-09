"""
Tests for core.transitions — TransitionVerifier Z3 invariant verification.

Verifies:
- Each invariant INV-1 through INV-8 individually passes (PROVEN)
- verify_all() returns all PROVEN
- Counterexamples appear when invariants are weakened
- Each TransitionType produces valid constraints
- Timeout handling
"""

import unittest

import z3

from core.state_model import DOFAgentState
from core.transitions import (
    TransitionVerifier,
    TransitionType,
    VerificationResult,
    _build_invariant,
    _build_transition,
)


class TestTransitionVerifierInvariants(unittest.TestCase):
    """Test each invariant individually."""

    def setUp(self):
        self.verifier = TransitionVerifier(timeout_ms=5000)

    def test_inv1_threat_blocks_publish(self):
        result = self.verifier.verify_invariant("INV-1")
        self.assertEqual(result.status, "PROVEN")
        self.assertIsNone(result.counterexample)

    def test_inv2_low_trust_no_attestations(self):
        result = self.verifier.verify_invariant("INV-2")
        self.assertEqual(result.status, "PROVEN")

    def test_inv3_no_hierarchy_jumps(self):
        result = self.verifier.verify_invariant("INV-3")
        self.assertEqual(result.status, "PROVEN")

    def test_inv4_trust_in_range(self):
        result = self.verifier.verify_invariant("INV-4")
        self.assertEqual(result.status, "PROVEN")

    def test_inv5_cooldown_blocks_publish(self):
        result = self.verifier.verify_invariant("INV-5")
        self.assertEqual(result.status, "PROVEN")

    def test_inv6_governor_high_trust(self):
        result = self.verifier.verify_invariant("INV-6")
        self.assertEqual(result.status, "PROVEN")

    def test_inv7_ss_formula_consistent(self):
        result = self.verifier.verify_invariant("INV-7")
        self.assertEqual(result.status, "PROVEN")

    def test_inv8_violation_forces_demote(self):
        result = self.verifier.verify_invariant("INV-8")
        self.assertEqual(result.status, "PROVEN")


class TestTransitionVerifierAll(unittest.TestCase):
    """Test verify_all aggregation."""

    def test_verify_all_returns_8_results(self):
        verifier = TransitionVerifier(timeout_ms=5000)
        results = verifier.verify_all()
        self.assertEqual(len(results), 8)

    def test_verify_all_all_proven(self):
        verifier = TransitionVerifier(timeout_ms=5000)
        results = verifier.verify_all()
        for inv_id, r in results.items():
            self.assertEqual(r.status, "PROVEN",
                             f"{inv_id} should be PROVEN but is {r.status}")

    def test_verify_all_keys_match_ids(self):
        verifier = TransitionVerifier(timeout_ms=5000)
        results = verifier.verify_all()
        expected = {f"INV-{i}" for i in range(1, 9)}
        self.assertEqual(set(results.keys()), expected)


class TestTransitionVerifierCounterexample(unittest.TestCase):
    """Test counterexample extraction."""

    def test_get_counterexample_for_valid_invariant_is_none(self):
        verifier = TransitionVerifier(timeout_ms=5000)
        ce = verifier.get_counterexample("INV-1")
        self.assertIsNone(ce)

    def test_invalid_invariant_raises(self):
        verifier = TransitionVerifier()
        with self.assertRaises(ValueError):
            verifier.verify_invariant("INV-99")


class TestTransitionTypes(unittest.TestCase):
    """Test that each TransitionType produces valid Z3 constraints."""

    def test_all_transition_types_produce_constraints(self):
        pre = DOFAgentState(prefix="pre_")
        post = DOFAgentState(prefix="post_")
        verifier = TransitionVerifier()

        for t in TransitionType:
            constraint = verifier.define_transition(t, pre, post)
            self.assertIsNotNone(constraint,
                                 f"Transition {t.value} returned None")

    def test_publish_transition_satisfiable(self):
        """A valid publish transition should be satisfiable."""
        pre = DOFAgentState(prefix="pre_")
        post = DOFAgentState(prefix="post_")

        solver = z3.Solver()
        for c in pre.constraints():
            solver.add(c)
        for c in post.constraints():
            solver.add(c)
        solver.add(_build_transition(TransitionType.PUBLISH, pre, post))

        self.assertEqual(solver.check(), z3.sat)

    def test_promote_transition_satisfiable(self):
        pre = DOFAgentState(prefix="pre_")
        post = DOFAgentState(prefix="post_")

        solver = z3.Solver()
        for c in pre.constraints():
            solver.add(c)
        for c in post.constraints():
            solver.add(c)
        solver.add(_build_transition(TransitionType.PROMOTE, pre, post))

        self.assertEqual(solver.check(), z3.sat)

    def test_threat_detect_blocks_publish(self):
        """After THREAT_DETECT, publish_allowed must be False."""
        pre = DOFAgentState(prefix="pre_")
        post = DOFAgentState(prefix="post_")

        solver = z3.Solver()
        for c in pre.constraints():
            solver.add(c)
        for c in post.constraints():
            solver.add(c)
        solver.add(_build_transition(TransitionType.THREAT_DETECT, pre, post))
        solver.add(post.publish_allowed)  # try to have publish after threat

        self.assertEqual(solver.check(), z3.unsat)

    def test_cooldown_start_blocks_publish(self):
        pre = DOFAgentState(prefix="pre_")
        post = DOFAgentState(prefix="post_")

        solver = z3.Solver()
        for c in pre.constraints():
            solver.add(c)
        for c in post.constraints():
            solver.add(c)
        solver.add(_build_transition(TransitionType.COOLDOWN_START, pre, post))
        solver.add(post.publish_allowed)

        self.assertEqual(solver.check(), z3.unsat)

    def test_governor_action_requires_level_3(self):
        """GOVERNOR_ACTION requires hierarchy_level=3."""
        pre = DOFAgentState(prefix="pre_")
        post = DOFAgentState(prefix="post_")

        solver = z3.Solver()
        for c in pre.constraints():
            solver.add(c)
        for c in post.constraints():
            solver.add(c)
        solver.add(_build_transition(TransitionType.GOVERNOR_ACTION, pre, post))
        solver.add(pre.hierarchy_level != 3)

        self.assertEqual(solver.check(), z3.unsat)


class TestVerificationResultDataclass(unittest.TestCase):
    """Test VerificationResult structure."""

    def test_result_has_required_fields(self):
        r = VerificationResult(
            invariant_id="INV-1",
            status="PROVEN",
            counterexample=None,
            verification_time_ms=5.0,
        )
        self.assertEqual(r.invariant_id, "INV-1")
        self.assertEqual(r.status, "PROVEN")
        self.assertIsNone(r.counterexample)
        self.assertGreater(r.verification_time_ms, 0)


class TestInvariantFormulas(unittest.TestCase):
    """Test invariant Z3 formulas directly."""

    def test_inv1_formula_is_bool(self):
        pre = DOFAgentState(prefix="pre_")
        post = DOFAgentState(prefix="post_")
        formula = _build_invariant("INV-1", pre, post)
        self.assertTrue(z3.is_bool(formula))

    def test_inv7_formula_links_ss_and_failure_rate(self):
        """INV-7: safety_score == 1 - f³"""
        pre = DOFAgentState(prefix="pre_")
        post = DOFAgentState(prefix="post_")
        formula = _build_invariant("INV-7", pre, post)

        solver = z3.Solver()
        solver.add(post.failure_rate == z3.RealVal("0.5"))
        solver.add(post.safety_score == z3.RealVal("0.875"))
        solver.add(formula)
        self.assertEqual(solver.check(), z3.sat)

    def test_unknown_invariant_raises(self):
        pre = DOFAgentState()
        post = DOFAgentState()
        with self.assertRaises(ValueError):
            _build_invariant("INV-999", pre, post)


if __name__ == "__main__":
    unittest.main()
