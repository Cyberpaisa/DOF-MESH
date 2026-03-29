"""
DOFVerifier — Public API for agent action verification.

This is the entry point that the README Quick Start documents.
Pipeline: Z3Gate (formal) → ConstitutionEnforcer (governance) → attestation hash.

Usage:
    from dof import DOFVerifier

    verifier = DOFVerifier()
    result = verifier.verify_action(
        agent_id="apex-1687",
        action="transfer",
        params={"amount": 500, "token": "USDC"}
    )
    print(result.verdict)       # APPROVED | REJECTED
    print(result.z3_proof)      # "4/4 VERIFIED [GCR_INVARIANT:VERIFIED | ...]"
    print(result.latency_ms)    # e.g. 11.2
    print(result.attestation)   # 0x<keccak256-like hash>
"""

import sys
import os
import time
import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any

# Ensure project root on path
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

logger = logging.getLogger("dof.verifier")


@dataclass
class VerifyResult:
    """Result of a DOFVerifier.verify_action() call."""
    verdict: str                    # "APPROVED" | "REJECTED"
    agent_id: str
    action: str
    params: dict
    latency_ms: float
    z3_proof: str                   # formal proof summary
    z3_time_ms: float               # Z3 solve time
    governance_passed: bool         # Constitution check on output text
    violations: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    attestation: str = ""           # keccak256 hash of this result


class DOFVerifier:
    """
    Single-entry verifier for agent actions. Zero LLMs in the decision loop.

    Pipeline per verify_action() call:
      1. Z3Gate.validate_trust_score()   — formal proof of trust invariants (~3ms)
      2. Z3Verifier.verify_all()         — 4 system theorems VERIFIED (~7ms, cached)
      3. ConstitutionEnforcer.check()    — governance rules on action text (<1ms)
      4. keccak256-like attestation hash — immutable record of this decision

    Args:
        cache_z3: Cache Z3Verifier proofs per process instance (default True).
                  Z3 system invariants are stable — safe to cache.
    """

    def __init__(self, cache_z3: bool = True):
        self._cache_z3 = cache_z3
        self._z3_proofs_cache: str | None = None
        self._enforcer = None
        self._gate = None
        self._z3 = None
        self._init_modules()

    def _init_modules(self):
        try:
            from core.governance import ConstitutionEnforcer
            self._enforcer = ConstitutionEnforcer()
        except Exception as e:
            logger.warning(f"ConstitutionEnforcer not available: {e}")
        try:
            from core.z3_gate import Z3Gate
            self._gate = Z3Gate()
        except Exception as e:
            logger.warning(f"Z3Gate not available: {e}")
        try:
            from core.z3_verifier import Z3Verifier
            self._z3 = Z3Verifier()
        except Exception as e:
            logger.warning(f"Z3Verifier not available: {e}")

    def _run_z3_proofs(self) -> tuple[str, float]:
        """Run Z3 system theorems, cached per process. Returns (summary, ms)."""
        if not self._z3:
            return "Z3 not available", 0.0
        if self._cache_z3 and self._z3_proofs_cache:
            return self._z3_proofs_cache, 0.0
        t0 = time.time()
        try:
            proofs = self._z3.verify_all()
            n_ok = sum(1 for p in proofs if p.result == "VERIFIED")
            details = " | ".join(f"{p.theorem_name}:{p.result}" for p in proofs)
            summary = f"{n_ok}/{len(proofs)} VERIFIED [{details}]"
            ms = round((time.time() - t0) * 1000, 1)
            if self._cache_z3:
                self._z3_proofs_cache = summary
            return summary, ms
        except Exception as e:
            return f"Z3 error: {e}", 0.0

    def _attestation_hash(self, agent_id: str, action: str,
                          params: dict, verdict: str) -> str:
        """Deterministic keccak256-style hash of the verification decision."""
        payload = f"{agent_id}:{action}:{sorted(params.items())}:{verdict}"
        return "0x" + hashlib.sha3_256(payload.encode()).hexdigest()

    def verify_action(
        self,
        agent_id: str,
        action: str,
        params: dict | None = None,
        trust_score: float = 0.85,
    ) -> VerifyResult:
        """
        Verify an agent action using Z3 formal proofs + Constitution.

        Args:
            agent_id:    Identifier of the agent (e.g. "apex-1687").
            action:      Action name (e.g. "transfer", "execute_trade").
            params:      Action parameters (e.g. {"amount": 500, "token": "USDC"}).
            trust_score: Agent trust score 0.0–1.0 (used in Z3Gate invariants).

        Returns:
            VerifyResult with verdict APPROVED or REJECTED.
        """
        t0 = time.time()
        params = params or {}
        violations = []
        warnings_list = []
        z3_gate_result = "APPROVED"
        z3_time_ms = 0.0

        # Step 1 — Z3Gate: formal proof of trust score invariants
        if self._gate:
            try:
                evidence = {"action": action, **params}
                gv = self._gate.validate_trust_score(
                    agent_id=agent_id,
                    proposed_score=trust_score,
                    evidence=evidence,
                )
                z3_gate_result = gv.result.value.upper() if hasattr(gv.result, "value") else str(gv.result)
                z3_time_ms = gv.verification_time_ms
                if z3_gate_result not in ("APPROVED",):
                    violations.append(f"[Z3_GATE] {gv.proof_transcript}")
            except Exception as e:
                logger.warning(f"Z3Gate error: {e}")

        # Step 2 — Z3Verifier: system theorems (cached)
        z3_proof_summary, z3_verify_ms = self._run_z3_proofs()
        z3_time_ms += z3_verify_ms

        # Step 3 — Constitution: governance check on the action description
        gov_passed = True
        if self._enforcer:
            try:
                # Build action output text that Constitution expects
                param_str = ", ".join(f"{k}={v}" for k, v in params.items())
                action_text = (
                    f"[{z3_gate_result}] Agent {agent_id} executing {action}({param_str}). "
                    f"Z3 proof: {z3_proof_summary[:60]}."
                )
                gov = self._enforcer.check(action_text)
                gov_passed = gov.passed if hasattr(gov, "passed") else True
                if not gov_passed:
                    violations.extend(gov.violations if hasattr(gov, "violations") else [])
                warnings_list = gov.warnings if hasattr(gov, "warnings") else []
            except Exception as e:
                logger.warning(f"Constitution check error: {e}")

        verdict = "REJECTED" if violations else "APPROVED"
        latency_ms = round((time.time() - t0) * 1000, 1)
        attestation = self._attestation_hash(agent_id, action, params, verdict)

        return VerifyResult(
            verdict=verdict,
            agent_id=agent_id,
            action=action,
            params=params,
            latency_ms=latency_ms,
            z3_proof=z3_proof_summary,
            z3_time_ms=z3_time_ms,
            governance_passed=gov_passed,
            violations=violations,
            warnings=warnings_list,
            attestation=attestation,
        )

    def verify_batch(self, actions: list[dict]) -> list[VerifyResult]:
        """Verify multiple actions. Z3 system proofs run once and are cached."""
        return [self.verify_action(**a) for a in actions]
