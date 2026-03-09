"""
Tests for core.z3_gate — Z3 Gate formal verification for agent outputs.

Verifies:
- Trust score validation (range, governor constraint)
- Promotion validation (hierarchy jumps)
- Threat classification (level range, evidence consistency)
- Mitigation validation (governance preservation)
- Timeout/fallback behavior
- Generic validation
"""

import unittest

from core.z3_gate import Z3Gate, GateResult, GateVerification
from core.agent_output import AgentOutput, OutputType


class TestZ3GateTrustScore(unittest.TestCase):
    """Test trust score validation."""

    def setUp(self):
        self.gate = Z3Gate(timeout_ms=3000)

    def test_valid_trust_score_approved(self):
        result = self.gate.validate_trust_score("agent1", 0.85, {})
        self.assertEqual(result.result, GateResult.APPROVED)

    def test_trust_score_zero_approved(self):
        result = self.gate.validate_trust_score("agent1", 0.0, {})
        self.assertEqual(result.result, GateResult.APPROVED)

    def test_trust_score_one_approved(self):
        result = self.gate.validate_trust_score("agent1", 1.0, {})
        self.assertEqual(result.result, GateResult.APPROVED)

    def test_trust_score_negative_rejected(self):
        result = self.gate.validate_trust_score("agent1", -0.1, {})
        self.assertEqual(result.result, GateResult.REJECTED)

    def test_trust_score_above_one_rejected(self):
        result = self.gate.validate_trust_score("agent1", 1.5, {})
        self.assertEqual(result.result, GateResult.REJECTED)

    def test_governor_low_trust_rejected(self):
        """Governor (level 3) with trust <= 0.8 should be rejected."""
        result = self.gate.validate_trust_score(
            "agent1", 0.5, {"current_level": 3}
        )
        self.assertEqual(result.result, GateResult.REJECTED)

    def test_governor_high_trust_approved(self):
        result = self.gate.validate_trust_score(
            "agent1", 0.9, {"current_level": 3}
        )
        self.assertEqual(result.result, GateResult.APPROVED)

    def test_trust_score_has_invariants(self):
        result = self.gate.validate_trust_score("agent1", 0.5, {})
        self.assertIn("INV-4", result.invariants_checked)


class TestZ3GatePromotion(unittest.TestCase):
    """Test promotion validation."""

    def setUp(self):
        self.gate = Z3Gate(timeout_ms=3000)

    def test_valid_promotion_approved(self):
        result = self.gate.validate_promotion("agent1", 1, 2)
        self.assertEqual(result.result, GateResult.APPROVED)

    def test_promotion_jump_rejected(self):
        """Can't skip levels: 0 → 2 is invalid."""
        result = self.gate.validate_promotion("agent1", 0, 2)
        self.assertEqual(result.result, GateResult.REJECTED)

    def test_promotion_above_max_rejected(self):
        """Can't promote above level 3."""
        result = self.gate.validate_promotion("agent1", 3, 4)
        self.assertEqual(result.result, GateResult.REJECTED)

    def test_promotion_to_governor_approved(self):
        result = self.gate.validate_promotion("agent1", 2, 3)
        self.assertEqual(result.result, GateResult.APPROVED)


class TestZ3GateThreatClassification(unittest.TestCase):
    """Test threat output validation."""

    def setUp(self):
        self.gate = Z3Gate(timeout_ms=3000)

    def test_low_threat_approved(self):
        result = self.gate.validate_threat_output({}, "LOW")
        self.assertEqual(result.result, GateResult.APPROVED)

    def test_high_threat_with_evidence_approved(self):
        evidence = {"indicators": ["sql_injection"], "pattern_matches": 1}
        result = self.gate.validate_threat_output(evidence, "HIGH")
        self.assertEqual(result.result, GateResult.APPROVED)

    def test_high_threat_no_evidence_rejected(self):
        """HIGH threat requires evidence."""
        result = self.gate.validate_threat_output({}, "HIGH")
        self.assertEqual(result.result, GateResult.REJECTED)

    def test_critical_no_evidence_rejected(self):
        result = self.gate.validate_threat_output({}, "CRITICAL")
        self.assertEqual(result.result, GateResult.REJECTED)

    def test_invalid_level_rejected(self):
        result = self.gate.validate_threat_output({}, "INVALID")
        self.assertEqual(result.result, GateResult.REJECTED)

    def test_medium_no_evidence_approved(self):
        """MEDIUM doesn't require evidence."""
        result = self.gate.validate_threat_output({}, "MEDIUM")
        self.assertEqual(result.result, GateResult.APPROVED)


class TestZ3GateMitigation(unittest.TestCase):
    """Test mitigation validation."""

    def setUp(self):
        self.gate = Z3Gate(timeout_ms=3000)

    def test_valid_mitigation_approved(self):
        result = self.gate.validate_mitigation_output("block_ip", {})
        self.assertEqual(result.result, GateResult.APPROVED)

    def test_disable_governance_rejected(self):
        result = self.gate.validate_mitigation_output("disable_governance", {})
        self.assertEqual(result.result, GateResult.REJECTED)

    def test_bypass_constitution_rejected(self):
        result = self.gate.validate_mitigation_output("bypass constitution", {})
        self.assertEqual(result.result, GateResult.REJECTED)

    def test_skip_verification_rejected(self):
        result = self.gate.validate_mitigation_output("skip-verification", {})
        self.assertEqual(result.result, GateResult.REJECTED)


class TestZ3GateOutputDispatch(unittest.TestCase):
    """Test validate_output dispatching."""

    def setUp(self):
        self.gate = Z3Gate(timeout_ms=3000)

    def test_dispatch_trust_score(self):
        output = AgentOutput(
            output_type=OutputType.TRUST_SCORE_ASSIGNMENT,
            agent_id="agent1",
            proposed_value=0.85,
            evidence={},
            source_agent="supervisor",
            confidence=0.9,
        )
        result = self.gate.validate_output(output)
        self.assertEqual(result.result, GateResult.APPROVED)

    def test_dispatch_invalid_schema_rejected(self):
        output = AgentOutput(
            output_type=OutputType.TRUST_SCORE_ASSIGNMENT,
            agent_id="",  # invalid
            proposed_value=0.5,
            evidence={},
        )
        result = self.gate.validate_output(output)
        self.assertEqual(result.result, GateResult.REJECTED)

    def test_proof_transcript_available(self):
        self.gate.validate_trust_score("agent1", 0.5, {})
        transcript = self.gate.get_proof_transcript()
        self.assertIsNotNone(transcript)


class TestGateVerificationDataclass(unittest.TestCase):
    """Test GateVerification structure."""

    def test_approved_result(self):
        v = GateVerification(
            result=GateResult.APPROVED,
            decision_type="trust_score",
            invariants_checked=["INV-4"],
        )
        self.assertEqual(v.result, GateResult.APPROVED)
        self.assertIsNone(v.counterexample)
        self.assertIsNone(v.fallback_layer)

    def test_fallback_result(self):
        v = GateVerification(
            result=GateResult.FALLBACK,
            decision_type="trust_score",
            invariants_checked=["INV-4"],
            fallback_layer="Constitution",
        )
        self.assertEqual(v.fallback_layer, "Constitution")


if __name__ == "__main__":
    unittest.main()
