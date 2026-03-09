"""
DOF Agent State Model — Z3 symbolic state for formal verification.

Defines the complete state of a DOF agent as Z3 symbolic variables.
Each variable maps to an aspect of agent lifecycle that must preserve
safety invariants across all transitions.

Used by TransitionVerifier (core.transitions) and HierarchyZ3
(core.hierarchy_z3) to prove governance inviolability.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import z3

logger = logging.getLogger("core.state_model")


@dataclass
class DOFAgentState:
    """Symbolic agent state for Z3 verification.

    Variables:
        trust_score: Real in [0.0, 1.0]
        hierarchy_level: Int in {0=user, 1=agent, 2=supervisor, 3=governor}
        threat_detected: Bool
        publish_allowed: Bool
        attestation_count: Int >= 0
        cooldown_active: Bool
        governance_violation: Bool
        safety_score: Real in [0.0, 1.0]  — SS(f) = 1 − f³
        failure_rate: Real in [0.0, 1.0]  — provider failure rate f
    """

    trust_score: z3.ArithRef = field(default=None)
    hierarchy_level: z3.ArithRef = field(default=None)
    threat_detected: z3.BoolRef = field(default=None)
    publish_allowed: z3.BoolRef = field(default=None)
    attestation_count: z3.ArithRef = field(default=None)
    cooldown_active: z3.BoolRef = field(default=None)
    governance_violation: z3.BoolRef = field(default=None)
    safety_score: z3.ArithRef = field(default=None)
    failure_rate: z3.ArithRef = field(default=None)

    _prefix: str = field(default="", repr=False)

    def __init__(self, prefix: str = ""):
        """Create Z3 symbolic variables with optional prefix.

        Args:
            prefix: String prefix for variable names (e.g. "pre_", "post_")
                    to avoid collisions between pre/post states in the same solver.
        """
        self._prefix = prefix
        p = prefix

        self.trust_score = z3.Real(f"{p}trust_score")
        self.hierarchy_level = z3.Int(f"{p}hierarchy_level")
        self.threat_detected = z3.Bool(f"{p}threat_detected")
        self.publish_allowed = z3.Bool(f"{p}publish_allowed")
        self.attestation_count = z3.Int(f"{p}attestation_count")
        self.cooldown_active = z3.Bool(f"{p}cooldown_active")
        self.governance_violation = z3.Bool(f"{p}governance_violation")
        self.safety_score = z3.Real(f"{p}safety_score")
        self.failure_rate = z3.Real(f"{p}failure_rate")

    def as_dict(self) -> dict[str, z3.ExprRef]:
        """Return mapping of variable names to Z3 expressions."""
        return {
            "trust_score": self.trust_score,
            "hierarchy_level": self.hierarchy_level,
            "threat_detected": self.threat_detected,
            "publish_allowed": self.publish_allowed,
            "attestation_count": self.attestation_count,
            "cooldown_active": self.cooldown_active,
            "governance_violation": self.governance_violation,
            "safety_score": self.safety_score,
            "failure_rate": self.failure_rate,
        }

    def constraints(self) -> list[z3.BoolRef]:
        """Return base range constraints (valid value domains).

        These must hold in ANY valid agent state:
        - trust_score ∈ [0, 1]
        - hierarchy_level ∈ {0, 1, 2, 3}
        - attestation_count >= 0
        - safety_score ∈ [0, 1]
        - failure_rate ∈ [0, 1]
        """
        return [
            self.trust_score >= 0, self.trust_score <= 1,
            self.hierarchy_level >= 0, self.hierarchy_level <= 3,
            self.attestation_count >= 0,
            self.safety_score >= 0, self.safety_score <= 1,
            self.failure_rate >= 0, self.failure_rate <= 1,
        ]

    @staticmethod
    def from_concrete(
        trust_score: float = 0.9,
        hierarchy_level: int = 1,
        threat_detected: bool = False,
        publish_allowed: bool = True,
        attestation_count: int = 0,
        cooldown_active: bool = False,
        governance_violation: bool = False,
        safety_score: float = 1.0,
        failure_rate: float = 0.0,
    ) -> list[z3.BoolRef]:
        """Return Z3 constraints that fix a concrete state.

        Useful for testing specific scenarios against invariants.
        Creates a fresh state with empty prefix and adds equality constraints.
        """
        s = DOFAgentState(prefix="concrete_")
        return [
            s.trust_score == z3.RealVal(str(trust_score)),
            s.hierarchy_level == hierarchy_level,
            s.threat_detected == threat_detected,
            s.publish_allowed == publish_allowed,
            s.attestation_count == attestation_count,
            s.cooldown_active == cooldown_active,
            s.governance_violation == governance_violation,
            s.safety_score == z3.RealVal(str(safety_score)),
            s.failure_rate == z3.RealVal(str(failure_rate)),
        ], s
