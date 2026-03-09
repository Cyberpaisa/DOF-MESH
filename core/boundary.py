"""
Boundary Engine — Z3-powered edge case and boundary value generation.

Finds values at the boundaries of governance constraints using Z3's
model enumeration. Used by Z3TestGenerator to create targeted tests.
"""

from __future__ import annotations

import logging
from typing import Optional

import z3

from core.state_model import DOFAgentState

logger = logging.getLogger("core.boundary")


class BoundaryEngine:
    """Generate boundary values and edge cases using Z3."""

    def __init__(self, timeout_ms: int = 5000):
        self.timeout_ms = timeout_ms

    def find_boundary_values(self, constraint: z3.BoolRef,
                             variable: z3.ArithRef,
                             n: int = 10) -> list[float]:
        """Find values near the boundary of a constraint.

        Uses Z3 to find the threshold, then generates values around it.

        Args:
            constraint: Z3 boolean formula involving variable.
            variable: Z3 arithmetic variable to find boundary for.
            n: Number of boundary values to generate.

        Returns:
            List of float values near the constraint boundary.
        """
        # Find the boundary by binary search via Z3
        solver = z3.Solver()
        solver.set("timeout", self.timeout_ms)

        # Find a satisfying value
        solver.add(constraint)
        solver.add(variable >= 0, variable <= 1)
        if solver.check() != z3.sat:
            return []

        sat_val = self._extract_real(solver.model(), variable)

        # Find an unsatisfying value
        solver2 = z3.Solver()
        solver2.set("timeout", self.timeout_ms)
        solver2.add(z3.Not(constraint))
        solver2.add(variable >= 0, variable <= 1)
        if solver2.check() != z3.sat:
            return [sat_val]

        unsat_val = self._extract_real(solver2.model(), variable)

        # Generate boundary values around the midpoint
        boundary = (sat_val + unsat_val) / 2
        step = abs(sat_val - unsat_val) / (n + 1) if n > 0 else 0.01

        values = set()
        values.add(round(boundary, 6))
        values.add(round(boundary - step, 6))
        values.add(round(boundary + step, 6))
        values.add(0.0)
        values.add(1.0)

        # Generate n values centered around boundary
        for i in range(1, n // 2 + 1):
            values.add(round(boundary - i * step, 6))
            values.add(round(boundary + i * step, 6))

        # Filter to valid range
        return sorted(v for v in values if 0.0 <= v <= 1.0)[:n]

    def find_minimal_violation(
        self, constraints: list[z3.BoolRef]
    ) -> Optional[dict]:
        """Find the smallest input that violates the constraints.

        Returns dict of variable assignments if a violation exists.
        """
        solver = z3.Solver()
        solver.set("timeout", self.timeout_ms)

        # Negate constraints — find a satisfying assignment to the negation
        solver.add(z3.Not(z3.And(constraints)))

        if solver.check() == z3.sat:
            model = solver.model()
            return {str(d): self._model_val(model, d) for d in model.decls()}
        return None

    def enumerate_edge_cases(self, state: DOFAgentState) -> list[dict]:
        """Generate edge case state assignments for all variables.

        Produces combinations of extreme values for each state variable.
        """
        edge_cases = []

        # Trust score edges
        for trust in [0.0, 0.39, 0.4, 0.41, 0.79, 0.8, 0.81, 1.0]:
            for level in [0, 1, 2, 3]:
                for threat in [True, False]:
                    for cooldown in [True, False]:
                        edge_cases.append({
                            "trust_score": trust,
                            "hierarchy_level": level,
                            "threat_detected": threat,
                            "cooldown_active": cooldown,
                            "publish_allowed": not (threat or cooldown),
                            "attestation_count": 0 if trust < 0.4 else 1,
                            "governance_violation": False,
                            "failure_rate": 0.0,
                            "safety_score": 1.0,
                        })

        return edge_cases

    @staticmethod
    def _extract_real(model: z3.ModelRef, var: z3.ArithRef) -> float:
        """Extract a float from a Z3 model."""
        val = model.eval(var, model_completion=True)
        try:
            return float(val.as_fraction())
        except Exception:
            return 0.5

    @staticmethod
    def _model_val(model: z3.ModelRef, decl) -> str:
        """Extract string representation of a model value."""
        val = model[decl]
        return str(val)
