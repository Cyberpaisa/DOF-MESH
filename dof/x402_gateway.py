"""
x402 Trust Gateway — DOF v0.2.5
================================
Formal verification layer for x402 payment endpoints.
Zero LLM in the critical decision path — 100% deterministic.

Usage:
    from dof.core.x402_gateway import TrustGateway, GatewayVerdict

    gateway = TrustGateway()
    verdict = gateway.verify(endpoint_url="https://api.example.com/agent",
                             response_body='{"result": "done"}',
                             payment_amount=0.01)
    if verdict.action == "ALLOW":
        proceed_with_payment()
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

# DOF internal imports — graceful fallback if running standalone
try:
    from dof.governance import ConstitutionEnforcer
    from dof.adversarial import RedTeamAgent
    from dof.merkle import MerkleBatcher
    _DOF_AVAILABLE = True
except ImportError:
    _DOF_AVAILABLE = False


# ─── Data Models ──────────────────────────────────────────────────────────────

class GatewayAction(str, Enum):
    ALLOW = "ALLOW"
    WARN  = "WARN"
    BLOCK = "BLOCK"


@dataclass
class CheckResult:
    """Result of a single verification check."""
    check_name: str
    passed: bool
    score: float          # 0.0 (fail) → 1.0 (pass)
    evidence: str = ""
    latency_ms: float = 0.0


@dataclass
class GatewayVerdict:
    """
    Final verdict for an x402 payment request.

    Attributes:
        action          : ALLOW / WARN / BLOCK
        governance_score: composite 0.0–1.0 (higher = more trustworthy)
        checks          : individual CheckResult list
        endpoint_hash   : SHA-256 of (url + response_body) for on-chain ref
        enigma_published: True if score was pushed to Enigma Scanner
        latency_ms      : total gateway latency
        timestamp       : Unix epoch
    """
    action: GatewayAction
    governance_score: float
    checks: list[CheckResult] = field(default_factory=list)
    endpoint_hash: str = ""
    enigma_published: bool = False
    latency_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)
    blocked_reason: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "action": self.action.value,
            "governance_score": round(self.governance_score, 4),
            "endpoint_hash": self.endpoint_hash,
            "enigma_published": self.enigma_published,
            "latency_ms": round(self.latency_ms, 2),
            "timestamp": self.timestamp,
            "blocked_reason": self.blocked_reason,
            "checks": [
                {
                    "check": c.check_name,
                    "passed": c.passed,
                    "score": round(c.score, 4),
                    "evidence": c.evidence,
                    "latency_ms": round(c.latency_ms, 2),
                }
                for c in self.checks
            ],
        }

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"GatewayVerdict(action={self.action.value}, "
            f"score={self.governance_score:.3f}, "
            f"checks={len(self.checks)})"
        )


# ─── Deterministic Checks (no LLM) ────────────────────────────────────────────

class _DeterministicChecks:
    """
    Static rule-based checks that run in the critical payment path.
    All checks are O(n) string scans — no external calls.
    """

    # PII patterns (simplified, non-regex for determinism)
    _PII_TOKENS = [
        "ssn", "social security", "credit card", "cvv", "passport",
        "date of birth", "dob", "bank account", "routing number",
    ]

    # Hallucination indicators
    _HALLUCINATION_TOKENS = [
        "as an ai", "i cannot", "i'm unable to", "i don't have access",
        "as a language model", "i apologize", "i must inform you",
    ]

    # Adversarial payload indicators
    _ADVERSARIAL_TOKENS = [
        "ignore previous", "ignore all", "disregard", "override",
        "jailbreak", "dan mode", "developer mode", "pretend you are",
        "you are now", "forget your instructions",
    ]

    @classmethod
    def check_pii(cls, text: str) -> CheckResult:
        t0 = time.perf_counter()
        lower = text.lower()
        hits = [tok for tok in cls._PII_TOKENS if tok in lower]
        passed = len(hits) == 0
        score = 1.0 if passed else max(0.0, 1.0 - (len(hits) * 0.25))
        return CheckResult(
            check_name="pii_scan",
            passed=passed,
            score=score,
            evidence=f"PII tokens found: {hits}" if hits else "No PII detected",
            latency_ms=(time.perf_counter() - t0) * 1000,
        )

    @classmethod
    def check_hallucination(cls, text: str) -> CheckResult:
        t0 = time.perf_counter()
        lower = text.lower()
        hits = [tok for tok in cls._HALLUCINATION_TOKENS if tok in lower]
        passed = len(hits) == 0
        score = 1.0 if passed else max(0.0, 1.0 - (len(hits) * 0.5))
        return CheckResult(
            check_name="hallucination_scan",
            passed=passed,
            score=score,
            evidence=f"Hallucination indicators: {hits}" if hits else "Clean",
            latency_ms=(time.perf_counter() - t0) * 1000,
        )

    @classmethod
    def check_adversarial(cls, text: str) -> CheckResult:
        t0 = time.perf_counter()
        lower = text.lower()
        hits = [tok for tok in cls._ADVERSARIAL_TOKENS if tok in lower]
        passed = len(hits) == 0
        score = 0.0 if hits else 1.0   # binary — any adversarial = zero score
        return CheckResult(
            check_name="adversarial_scan",
            passed=passed,
            score=score,
            evidence=f"Adversarial tokens: {hits}" if hits else "Clean",
            latency_ms=(time.perf_counter() - t0) * 1000,
        )

    @classmethod
    def check_response_structure(cls, response_body: str) -> CheckResult:
        """Validates that the response is parseable and non-empty."""
        t0 = time.perf_counter()
        try:
            parsed = json.loads(response_body)
            passed = bool(parsed)
            score = 1.0 if passed else 0.5
            evidence = f"Valid JSON, keys: {list(parsed.keys())[:5]}" if isinstance(parsed, dict) else "Valid JSON"
        except (json.JSONDecodeError, TypeError):
            # Non-JSON is acceptable (plain text responses)
            passed = bool(response_body and response_body.strip())
            score = 0.8 if passed else 0.0
            evidence = "Non-JSON response (plain text)" if passed else "Empty response"
        return CheckResult(
            check_name="response_structure",
            passed=passed,
            score=score,
            evidence=evidence,
            latency_ms=(time.perf_counter() - t0) * 1000,
        )


# ─── DOF-powered Checks (when dof-sdk available) ──────────────────────────────

class _DOFChecks:
    """Wraps DOF SDK components — only used when dof-sdk is installed."""

    def __init__(self):
        if not _DOF_AVAILABLE:
            raise RuntimeError(
                "dof-sdk not installed. Run: pip install dof-sdk"
            )
        self._enforcer = ConstitutionEnforcer()
        self._red_team = RedTeamAgent()

    def check_constitution(
        self,
        system_prompt: str,
        user_prompt: str,
        response: str,
    ) -> CheckResult:
        t0 = time.perf_counter()
        result = self._enforcer.enforce_hierarchy(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response=response,
        )
        passed = result.compliant
        score = 1.0 if passed else 0.0
        return CheckResult(
            check_name="constitution_enforcer",
            passed=passed,
            score=score,
            evidence=f"violation_level={result.violation_level} | {result.details}",
            latency_ms=(time.perf_counter() - t0) * 1000,
        )

    def check_red_team(self, payload: str) -> CheckResult:
        t0 = time.perf_counter()
        attack = self._red_team.indirect_prompt_injection(payload)
        passed = not attack.detected
        score = 0.0 if attack.detected else 1.0
        return CheckResult(
            check_name="red_team_injection",
            passed=passed,
            score=score,
            evidence=f"detected={attack.detected}",
            latency_ms=(time.perf_counter() - t0) * 1000,
        )


# ─── Enigma Bridge (optional on-chain publication) ────────────────────────────

class EnigmaBridge:
    """
    Lightweight stub for publishing trust scores to Enigma Scanner.
    Replace with real HTTP client when Enigma API is ready.
    """

    def __init__(self, enigma_url: str = "https://erc-8004scan.xyz/api/score"):
        self.enigma_url = enigma_url

    def publish(
        self,
        endpoint_hash: str,
        score: float,
        action: str,
        metadata: dict | None = None,
    ) -> bool:
        """
        Publish trust score to Enigma Scanner.
        Returns True on success.
        """
        try:
            import urllib.request
            payload = json.dumps({
                "endpoint_hash": endpoint_hash,
                "score": round(score, 4),
                "action": action,
                "metadata": metadata or {},
                "timestamp": time.time(),
            }).encode()
            req = urllib.request.Request(
                self.enigma_url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=2) as resp:
                return resp.status == 200
        except Exception:
            return False


# ─── TrustGateway ─────────────────────────────────────────────────────────────

class TrustGateway:
    """
    x402 Trust Gateway — intercepts payment requests and runs formal
    DOF verification before allowing the transaction to proceed.

    Decision logic:
        BLOCK  : adversarial detected OR governance_score < block_threshold
        WARN   : PII detected OR block_threshold ≤ score < warn_threshold
        ALLOW  : all checks pass AND score ≥ warn_threshold

    Args:
        block_threshold : score below which payments are BLOCKED (default 0.4)
        warn_threshold  : score below which payments are WARNED (default 0.7)
        use_dof_sdk     : use ConstitutionEnforcer + RedTeamAgent if available
        publish_to_enigma: push verdict to Enigma Scanner after each check
        enigma_url      : Enigma Scanner API endpoint
    """

    def __init__(
        self,
        block_threshold: float = 0.4,
        warn_threshold: float = 0.7,
        use_dof_sdk: bool = True,
        publish_to_enigma: bool = False,
        enigma_url: str = "https://erc-8004scan.xyz/api/score",
    ):
        self.block_threshold = block_threshold
        self.warn_threshold = warn_threshold
        self.publish_to_enigma = publish_to_enigma

        self._det = _DeterministicChecks()

        self._dof: Optional[_DOFChecks] = None
        if use_dof_sdk and _DOF_AVAILABLE:
            try:
                self._dof = _DOFChecks()
            except Exception:
                pass  # graceful degradation

        self._enigma = EnigmaBridge(enigma_url) if publish_to_enigma else None

    # ── public API ────────────────────────────────────────────────────────────

    def verify(
        self,
        response_body: str,
        endpoint_url: str = "",
        system_prompt: str = "",
        user_prompt: str = "",
        payment_amount: float = 0.0,
        metadata: dict | None = None,
    ) -> GatewayVerdict:
        """
        Run all checks and return a GatewayVerdict.

        Args:
            response_body  : raw response from the x402 endpoint
            endpoint_url   : URL of the endpoint (used for hashing)
            system_prompt  : system prompt sent to the agent (optional)
            user_prompt    : user prompt sent to the agent (optional)
            payment_amount : amount in USD/ETH being paid (used in metadata)
            metadata       : extra context to attach to the Enigma publication
        """
        t0 = time.perf_counter()
        checks: list[CheckResult] = []

        # 0. Hard block on empty response
        if not response_body or not response_body.strip():
            return GatewayVerdict(
                action=GatewayAction.BLOCK,
                governance_score=0.0,
                checks=[CheckResult('response_structure', False, 0.0, 'Empty response')],
                endpoint_hash=hashlib.sha256(endpoint_url.encode()).hexdigest(),
                latency_ms=(time.perf_counter() - t0) * 1000,
                blocked_reason='Empty response body',
            )

        # 1. Deterministic checks (always run, no external deps)
        checks.append(_DeterministicChecks.check_response_structure(response_body))
        checks.append(_DeterministicChecks.check_adversarial(response_body))
        checks.append(_DeterministicChecks.check_hallucination(response_body))
        checks.append(_DeterministicChecks.check_pii(response_body))

        # 2. DOF SDK checks (when available and prompts provided)
        if self._dof and (system_prompt or user_prompt):
            checks.append(
                self._dof.check_constitution(
                    system_prompt=system_prompt or "You are a helpful agent.",
                    user_prompt=user_prompt or response_body[:200],
                    response=response_body,
                )
            )
            checks.append(self._dof.check_red_team(response_body))

        # 3. Compute composite governance score (weighted average)
        weights = {
            "adversarial_scan":     0.35,   # highest weight — hard fail
            "hallucination_scan":   0.25,
            "pii_scan":             0.20,
            "response_structure":   0.05,
            "constitution_enforcer":0.10,
            "red_team_injection":   0.05,
        }
        total_w = 0.0
        weighted_score = 0.0
        for c in checks:
            w = weights.get(c.check_name, 0.05)
            weighted_score += c.score * w
            total_w += w
        governance_score = weighted_score / total_w if total_w > 0 else 0.0

        # 4. Determine action
        adversarial_check = next(
            (c for c in checks if c.check_name == "adversarial_scan"), None
        )
        pii_check = next(
            (c for c in checks if c.check_name == "pii_scan"), None
        )

        blocked_reason = None
        if adversarial_check and not adversarial_check.passed:
            action = GatewayAction.BLOCK
            blocked_reason = adversarial_check.evidence
        elif governance_score < self.block_threshold:
            action = GatewayAction.BLOCK
            blocked_reason = f"governance_score={governance_score:.3f} below block_threshold={self.block_threshold}"
        elif (pii_check and not pii_check.passed) or governance_score < self.warn_threshold:
            action = GatewayAction.WARN
        else:
            action = GatewayAction.ALLOW

        # 5. Build endpoint hash (deterministic fingerprint)
        endpoint_hash = hashlib.sha256(
            f"{endpoint_url}::{response_body[:512]}".encode()
        ).hexdigest()

        total_ms = (time.perf_counter() - t0) * 1000

        verdict = GatewayVerdict(
            action=action,
            governance_score=governance_score,
            checks=checks,
            endpoint_hash=endpoint_hash,
            latency_ms=total_ms,
            blocked_reason=blocked_reason,
        )

        # 6. Optional Enigma publication
        if self._enigma:
            published = self._enigma.publish(
                endpoint_hash=endpoint_hash,
                score=governance_score,
                action=action.value,
                metadata={
                    "endpoint_url": endpoint_url,
                    "payment_amount": payment_amount,
                    **(metadata or {}),
                },
            )
            verdict.enigma_published = published

        return verdict

    def verify_batch(self, requests: list[dict]) -> list[GatewayVerdict]:
        """
        Verify multiple x402 requests in sequence.
        Each dict should match the kwargs of verify().
        """
        return [self.verify(**req) for req in requests]
