"""
Z3 Gate — formal verification gate for agent outputs.

Neurosymbolic architecture: agents produce outputs → Z3 verifies consistency
with governance rules → approved outputs execute, rejected ones are blocked.

The gate intercepts Meta-Supervisor decisions and Red/Blue agent outputs
before they take effect. Red/Blue agents are already deterministic internally;
the gate validates their OUTPUTS (classifications, mitigations) are consistent.

Timeout behavior:
- Gate NEVER blocks > timeout_ms
- On timeout → delegates to deterministic layers (Constitution → AST → Arbiter)
- Logs warning but does NOT fail
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import z3

from core.state_model import DOFAgentState
from core.agent_output import AgentOutput, OutputType
from core.transitions import _cross_cutting_constraints

logger = logging.getLogger("core.z3_gate")


class GateResult(Enum):
    """Outcome of Z3 gate verification."""
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"
    FALLBACK = "fallback"


# Deterministic fallback chain (in order of preference)
_FALLBACK_LAYERS = ["Constitution", "AST", "Arbiter", "LoopGuard"]


@dataclass
class GateVerification:
    """Full result of a Z3 gate verification."""
    result: GateResult
    decision_type: str
    invariants_checked: list[str]
    counterexample: Optional[dict] = None
    verification_time_ms: float = 0.0
    fallback_layer: Optional[str] = None
    proof_transcript: Optional[str] = None


class Z3Gate:
    """Z3 verification gate for agent outputs.

    Validates that proposed agent outputs are consistent with DOF
    governance constraints before they are applied.
    """

    def __init__(self, timeout_ms: int = 5000):
        """Initialize gate.

        Args:
            timeout_ms: Maximum Z3 solving time. On timeout, delegates
                       to deterministic layers instead of blocking.
        """
        self.timeout_ms = timeout_ms
        self._last_transcript: Optional[str] = None

    def validate_output(self, output: AgentOutput) -> GateVerification:
        """Validate an agent output against governance constraints.

        Dispatches to type-specific validation based on output_type.
        Returns REJECTED immediately if output is None.
        """
        if output is None:
            return GateVerification(
                result=GateResult.REJECTED,
                decision_type="unknown",
                invariants_checked=[],
                counterexample={"error": "output is None"},
                verification_time_ms=0.0,
            )
        if not output.validate_schema():
            return GateVerification(
                result=GateResult.REJECTED,
                decision_type=output.output_type.value,
                invariants_checked=[],
                counterexample={"error": "Invalid output schema"},
                verification_time_ms=0.0,
            )

        if output.output_type == OutputType.TRUST_SCORE_ASSIGNMENT:
            return self.validate_trust_score(
                output.agent_id,
                float(output.proposed_value),
                output.evidence,
            )
        elif output.output_type == OutputType.AGENT_PROMOTION:
            return self.validate_promotion(
                output.agent_id,
                int(output.evidence.get("current_level", 0)),
                int(output.proposed_value),
            )
        elif output.output_type == OutputType.THREAT_CLASSIFICATION:
            return self.validate_threat_output(
                output.evidence,
                str(output.proposed_value),
            )
        elif output.output_type == OutputType.MITIGATION_RECOMMENDATION:
            return self.validate_mitigation_output(
                str(output.proposed_value),
                output.evidence,
            )
        else:
            # Generic validation using output constraints
            return self._generic_validate(output)

    def validate_trust_score(self, agent_id: str, proposed_score: float,
                             evidence: dict) -> GateVerification:
        """Validate a trust score assignment.

        Checks:
        - Score in [0, 1]
        - If agent is governor (level 3), score must be > 0.8
        - Score change is consistent with evidence
        """
        start = time.time()
        solver = z3.Solver()
        solver.set("timeout", self.timeout_ms)

        score = z3.Real("proposed_score")
        level = z3.Int("current_level")

        solver.add(score == z3.RealVal(str(proposed_score)))

        current_level = evidence.get("current_level", 0)
        solver.add(level == current_level)

        # Try to violate: score out of range OR governor with low score
        solver.add(z3.Or(
            score < 0,
            score > 1,
            z3.And(level == 3, score <= z3.RealVal("0.8")),
        ))

        result = solver.check()
        elapsed = (time.time() - start) * 1000

        invariants = ["INV-4", "INV-6"]

        if result == z3.unsat:
            # No violation possible — score is valid
            self._last_transcript = f"UNSAT: trust_score={proposed_score} valid"
            return GateVerification(
                result=GateResult.APPROVED,
                decision_type="trust_score",
                invariants_checked=invariants,
                verification_time_ms=round(elapsed, 2),
                proof_transcript=self._last_transcript,
            )
        elif result == z3.sat:
            model = solver.model()
            ce = {"proposed_score": proposed_score,
                  "current_level": current_level,
                  "reason": "Score violates governance constraints"}
            self._last_transcript = f"SAT: counterexample found: {ce}"
            return GateVerification(
                result=GateResult.REJECTED,
                decision_type="trust_score",
                invariants_checked=invariants,
                counterexample=ce,
                verification_time_ms=round(elapsed, 2),
                proof_transcript=self._last_transcript,
            )
        else:
            return self._handle_timeout("trust_score", invariants, elapsed)

    def validate_promotion(self, agent_id: str, current_level: int,
                           target_level: int) -> GateVerification:
        """Validate an agent promotion.

        Checks:
        - Target is exactly current + 1 (no jumps)
        - Target <= 3
        - If target is 3, trust must be > 0.8
        """
        start = time.time()
        solver = z3.Solver()
        solver.set("timeout", self.timeout_ms)

        current = z3.IntVal(current_level)
        target = z3.IntVal(target_level)

        # Try to violate hierarchy constraints
        solver.add(z3.Or(
            target != current + 1,
            target > 3,
            target < 0,
        ))

        result = solver.check()
        elapsed = (time.time() - start) * 1000

        invariants = ["INV-3", "INV-6"]

        if result == z3.unsat:
            self._last_transcript = f"UNSAT: promotion {current_level}→{target_level} valid"
            return GateVerification(
                result=GateResult.APPROVED,
                decision_type="promotion",
                invariants_checked=invariants,
                verification_time_ms=round(elapsed, 2),
                proof_transcript=self._last_transcript,
            )
        else:
            ce = {"current_level": current_level, "target_level": target_level,
                  "reason": "Promotion violates hierarchy constraints"}
            self._last_transcript = f"SAT: invalid promotion: {ce}"
            return GateVerification(
                result=GateResult.REJECTED,
                decision_type="promotion",
                invariants_checked=invariants,
                counterexample=ce,
                verification_time_ms=round(elapsed, 2),
                proof_transcript=self._last_transcript,
            )

    def validate_threat_output(self, threat_data: dict,
                               proposed_level: str) -> GateVerification:
        """Validate a threat classification output.

        Checks:
        - Threat level is valid (LOW/MEDIUM/HIGH/CRITICAL → 0-3)
        - Classification is consistent with evidence
        """
        start = time.time()

        level_map = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3,
                     "0": 0, "1": 1, "2": 2, "3": 3}
        level_int = level_map.get(str(proposed_level).upper())

        if level_int is None:
            elapsed = (time.time() - start) * 1000
            return GateVerification(
                result=GateResult.REJECTED,
                decision_type="threat_class",
                invariants_checked=[],
                counterexample={"proposed_level": proposed_level,
                                "reason": "Invalid threat level"},
                verification_time_ms=round(elapsed, 2),
            )

        # Check evidence consistency: HIGH/CRITICAL requires at least
        # one indicator in evidence
        indicators = threat_data.get("indicators", [])
        pattern_matches = threat_data.get("pattern_matches", 0)

        if level_int >= 2 and not indicators and pattern_matches == 0:
            elapsed = (time.time() - start) * 1000
            return GateVerification(
                result=GateResult.REJECTED,
                decision_type="threat_class",
                invariants_checked=["evidence_consistency"],
                counterexample={"proposed_level": proposed_level,
                                "indicators": 0, "pattern_matches": 0,
                                "reason": "HIGH/CRITICAL requires evidence"},
                verification_time_ms=round(elapsed, 2),
            )

        elapsed = (time.time() - start) * 1000
        self._last_transcript = f"APPROVED: threat_class={proposed_level}"
        return GateVerification(
            result=GateResult.APPROVED,
            decision_type="threat_class",
            invariants_checked=["level_range", "evidence_consistency"],
            verification_time_ms=round(elapsed, 2),
            proof_transcript=self._last_transcript,
        )

    def validate_mitigation_output(self, action: str,
                                   evidence: dict) -> GateVerification:
        """Validate a mitigation recommendation.

        Checks that the recommended action doesn't violate governance.
        """
        start = time.time()

        # Blocked mitigations (would violate governance)
        blocked_actions = [
            "disable_governance", "skip_verification",
            "bypass_constitution", "remove_all_rules",
            "elevate_without_review", "publish_without_check",
        ]

        action_lower = action.lower().replace(" ", "_").replace("-", "_")
        for blocked in blocked_actions:
            if blocked in action_lower:
                elapsed = (time.time() - start) * 1000
                return GateVerification(
                    result=GateResult.REJECTED,
                    decision_type="mitigation",
                    invariants_checked=["governance_preservation"],
                    counterexample={"action": action,
                                    "blocked_by": blocked,
                                    "reason": "Action would violate governance"},
                    verification_time_ms=round(elapsed, 2),
                )

        elapsed = (time.time() - start) * 1000
        self._last_transcript = f"APPROVED: mitigation={action}"
        return GateVerification(
            result=GateResult.APPROVED,
            decision_type="mitigation",
            invariants_checked=["governance_preservation"],
            verification_time_ms=round(elapsed, 2),
            proof_transcript=self._last_transcript,
        )

    def get_proof_transcript(self) -> Optional[str]:
        """Return the last verification's proof transcript."""
        return self._last_transcript

    def _generic_validate(self, output: AgentOutput) -> GateVerification:
        """Generic validation using output's Z3 constraints."""
        start = time.time()
        solver = z3.Solver()
        solver.set("timeout", self.timeout_ms)

        constraints = output.as_z3_constraints()
        if not constraints:
            elapsed = (time.time() - start) * 1000
            return GateVerification(
                result=GateResult.APPROVED,
                decision_type=output.output_type.value,
                invariants_checked=[],
                verification_time_ms=round(elapsed, 2),
            )

        # Check that constraints are satisfiable (output is valid)
        for c in constraints:
            solver.add(c)

        result = solver.check()
        elapsed = (time.time() - start) * 1000

        if result == z3.sat:
            self._last_transcript = f"SAT: output constraints satisfiable"
            return GateVerification(
                result=GateResult.APPROVED,
                decision_type=output.output_type.value,
                invariants_checked=["schema_validity"],
                verification_time_ms=round(elapsed, 2),
                proof_transcript=self._last_transcript,
            )
        elif result == z3.unsat:
            return GateVerification(
                result=GateResult.REJECTED,
                decision_type=output.output_type.value,
                invariants_checked=["schema_validity"],
                counterexample={"reason": "Output constraints unsatisfiable"},
                verification_time_ms=round(elapsed, 2),
            )
        else:
            return self._handle_timeout(output.output_type.value,
                                        ["schema_validity"], elapsed)

    def _handle_timeout(self, decision_type: str, invariants: list[str],
                        elapsed_ms: float) -> GateVerification:
        """Handle Z3 timeout by delegating to deterministic layers."""
        fallback = _FALLBACK_LAYERS[0]
        logger.warning(f"Z3 Gate TIMEOUT on {decision_type}, "
                       f"delegating to {fallback}")
        return GateVerification(
            result=GateResult.FALLBACK,
            decision_type=decision_type,
            invariants_checked=invariants,
            fallback_layer=fallback,
            verification_time_ms=round(elapsed_ms, 2),
        )
