"""
DOF Agent Output Protocol — structured outputs that pass through Z3 Gate.

Defines the data model for agent outputs (Meta-Supervisor decisions,
Red/Blue classifications) that must be formally verified before execution.

The Z3 Gate validates these outputs against governance constraints.
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import z3

logger = logging.getLogger("core.agent_output")


class OutputType(Enum):
    """Types of agent outputs that require Z3 validation."""
    TRUST_SCORE_ASSIGNMENT = "trust_score"
    AGENT_PROMOTION = "promotion"
    AGENT_DEMOTION = "demotion"
    THREAT_CLASSIFICATION = "threat_class"
    MITIGATION_RECOMMENDATION = "mitigation"
    PATTERN_MATCH_ASSERTION = "pattern_match"


@dataclass
class AgentOutput:
    """Structured output from a DOF agent.

    Every output that affects trust scores, hierarchy, or threat state
    must pass through the Z3 Gate for formal verification.
    """
    output_type: OutputType
    agent_id: str
    proposed_value: Any
    evidence: dict
    timestamp: float = field(default_factory=time.time)
    source_agent: str = ""
    confidence: float = 0.0

    def as_z3_constraints(self) -> list[z3.BoolRef]:
        """Translate the output to Z3 constraints for gate verification.

        Returns constraints that must hold for this output to be valid.
        """
        constraints = []

        if self.output_type == OutputType.TRUST_SCORE_ASSIGNMENT:
            score = z3.RealVal(str(self.proposed_value))
            # Trust score must be in [0, 1]
            constraints.append(score >= 0)
            constraints.append(score <= 1)

        elif self.output_type == OutputType.AGENT_PROMOTION:
            target = z3.IntVal(int(self.proposed_value))
            current = z3.IntVal(int(self.evidence.get("current_level", 0)))
            # Can only promote by 1 level
            constraints.append(target == current + 1)
            # Max level 3
            constraints.append(target <= 3)

        elif self.output_type == OutputType.AGENT_DEMOTION:
            target = z3.IntVal(int(self.proposed_value))
            current = z3.IntVal(int(self.evidence.get("current_level", 0)))
            # Can only demote by 1 level
            constraints.append(target == current - 1)
            # Min level 0
            constraints.append(target >= 0)

        elif self.output_type == OutputType.THREAT_CLASSIFICATION:
            # Threat level must be one of: LOW=0, MEDIUM=1, HIGH=2, CRITICAL=3
            level = z3.IntVal(int(self.proposed_value))
            constraints.append(level >= 0)
            constraints.append(level <= 3)

        elif self.output_type == OutputType.PATTERN_MATCH_ASSERTION:
            # Pattern ID must be in range [0, 11] (12 DOFThreatPatterns categories)
            pattern_id = z3.IntVal(int(self.proposed_value))
            constraints.append(pattern_id >= 0)
            constraints.append(pattern_id <= 11)

        return constraints

    def validate_schema(self) -> bool:
        """Validate that the output has all required fields."""
        if not self.agent_id:
            return False
        if self.proposed_value is None:
            return False
        if not isinstance(self.evidence, dict):
            return False
        if self.confidence < 0 or self.confidence > 1:
            return False
        return True
