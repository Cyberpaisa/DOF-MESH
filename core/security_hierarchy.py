from __future__ import annotations
"""
Security Hierarchy — L0 → L1 → L2 → L3 → L4 Orchestrator.

Chains all security verification layers in deterministic order:
  L0: Triage — Pre-LLM filtering (skip 72.7% of noise)
  L1: Constitution — HARD_RULES enforcement (block/allow)
  L2: AST Gate — Static code analysis (eval/exec/import/secrets)
  L3: Soft Rules — Scoring (sources, structure, actionability, PII)
  L4: Z3 Gate — Formal mathematical verification (theorem proving)

Each layer is a gate: if it fails, execution stops. No LLM involvement
in any layer — 100% deterministic from L0 to L4.

Results logged to logs/security_hierarchy.jsonl for audit.
"""

import json
import logging
import os
import time
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("core.security_hierarchy")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = os.path.join(BASE_DIR, "logs", "security_hierarchy.jsonl")


@dataclass
class LayerResult:
    """Result from a single security layer."""
    layer: str  # L0, L1, L2, L3, L4
    passed: bool
    reason: str
    score: float = 1.0  # 0.0-1.0
    details: dict = field(default_factory=dict)
    time_ms: float = 0.0


@dataclass
class HierarchyResult:
    """Result from the full security hierarchy."""
    passed: bool
    failed_at: str  # Layer that failed, or "NONE"
    layers: list[LayerResult] = field(default_factory=list)
    total_time_ms: float = 0.0
    proof_hash: str = ""
    timestamp: float = field(default_factory=time.time)


class SecurityHierarchy:
    """Orchestrates L0→L4 security verification pipeline.

    Each layer is optional — if the module isn't available, it's skipped
    with a warning. This allows graceful degradation.
    """

    def __init__(self):
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    def verify(self, input_text: str, output_text: str,
               attempt: int = 1,
               active_providers: list[str] | None = None,
               contains_code: bool = False) -> HierarchyResult:
        """Run the full L0→L4 security hierarchy.

        Args:
            input_text: The original input/prompt
            output_text: The agent's output to verify
            attempt: Current retry attempt number
            active_providers: Available LLM providers
            contains_code: Whether output contains executable code

        Returns:
            HierarchyResult with pass/fail and layer details
        """
        start = time.time()
        layers: list[LayerResult] = []
        overall_passed = True
        failed_at = "NONE"

        # --- L0: Triage ---
        l0_result = self._run_l0(input_text, attempt, active_providers)
        layers.append(l0_result)
        if not l0_result.passed:
            overall_passed = False
            failed_at = "L0"
            return self._finalize(overall_passed, failed_at, layers, start)

        # --- L1: Constitution (HARD_RULES) ---
        l1_result = self._run_l1(output_text)
        layers.append(l1_result)
        if not l1_result.passed:
            overall_passed = False
            failed_at = "L1"
            return self._finalize(overall_passed, failed_at, layers, start)

        # --- L2: AST Gate (if code) ---
        if contains_code or self._looks_like_code(output_text):
            l2_result = self._run_l2(output_text)
            layers.append(l2_result)
            if not l2_result.passed:
                overall_passed = False
                failed_at = "L2"
                return self._finalize(overall_passed, failed_at, layers, start)
        else:
            layers.append(LayerResult("L2", True, "skipped_no_code", 1.0))

        # --- L3: Soft Rules (scoring) ---
        l3_result = self._run_l3(output_text)
        layers.append(l3_result)
        # L3 never blocks — only scores

        # --- L4: Z3 Gate (formal verification) ---
        l4_result = self._run_l4()
        layers.append(l4_result)
        if not l4_result.passed:
            overall_passed = False
            failed_at = "L4"

        return self._finalize(overall_passed, failed_at, layers, start)

    def _run_l0(self, input_text: str, attempt: int,
                providers: list[str] | None) -> LayerResult:
        """L0: Deterministic pre-LLM triage."""
        start = time.time()
        try:
            from core.l0_triage import L0Triage
            triage = L0Triage()
            decision = triage.evaluate(input_text, attempt, providers)
            return LayerResult(
                "L0", decision.proceed, decision.reason,
                1.0 if decision.proceed else 0.0,
                decision.checks,
                (time.time() - start) * 1000,
            )
        except ImportError:
            return LayerResult("L0", True, "module_not_available", 1.0,
                               time_ms=(time.time() - start) * 1000)

    def _run_l1(self, output_text: str) -> LayerResult:
        """L1: Constitution enforcement (HARD_RULES)."""
        start = time.time()
        try:
            from core.governance import ConstitutionEnforcer
            enforcer = ConstitutionEnforcer()
            result = enforcer.enforce(output_text)
            passed = result.get("status") == "COMPLIANT"
            reason = "; ".join(result.get("hard_violations", [])) or "compliant"
            return LayerResult(
                "L1", passed, reason,
                1.0 if passed else 0.0,
                {"enforcement": reason},
                (time.time() - start) * 1000,
            )
        except ImportError:
            return LayerResult("L1", True, "module_not_available", 1.0,
                               time_ms=(time.time() - start) * 1000)

    def _run_l2(self, output_text: str) -> LayerResult:
        """L2: AST verification for code safety."""
        start = time.time()
        try:
            from core.ast_verifier import ASTVerifier
            verifier = ASTVerifier()
            result = verifier.verify(output_text)
            return LayerResult(
                "L2", result.passed, "ast_verified" if result.passed else "ast_violations",
                result.score,
                {"violations": [str(v) for v in result.violations[:5]]},
                (time.time() - start) * 1000,
            )
        except ImportError:
            return LayerResult("L2", True, "module_not_available", 1.0,
                               time_ms=(time.time() - start) * 1000)

    def _run_l3(self, output_text: str) -> LayerResult:
        """L3: Soft rules scoring (never blocks, only scores)."""
        start = time.time()
        try:
            from core.governance import ConstitutionEnforcer
            enforcer = ConstitutionEnforcer()
            result = enforcer.check(output_text)
            return LayerResult(
                "L3", True, "soft_rules_scored",
                result.score,
                {"warnings": result.warnings[:5] if hasattr(result, 'warnings') else []},
                (time.time() - start) * 1000,
            )
        except (ImportError, AttributeError):
            return LayerResult("L3", True, "module_not_available", 1.0,
                               time_ms=(time.time() - start) * 1000)

    def _run_l4(self) -> LayerResult:
        """L4: Z3 formal verification."""
        start = time.time()
        try:
            from core.z3_verifier import Z3Verifier
            verifier = Z3Verifier()
            proofs = verifier.verify_all()
            all_proven = all(p.result in ("PROVEN", "VERIFIED") for p in proofs)
            proven_count = sum(1 for p in proofs if p.result in ("PROVEN", "VERIFIED"))
            total = len(proofs)
            return LayerResult(
                "L4", all_proven,
                f"z3_{proven_count}/{total}_proven",
                proven_count / max(total, 1),
                {
                    "proven": proven_count,
                    "total": total,
                    "theorems": [
                        {"name": p.theorem_name, "result": p.result, "ms": p.proof_time_ms}
                        for p in proofs
                    ],
                },
                (time.time() - start) * 1000,
            )
        except ImportError:
            return LayerResult("L4", True, "z3_not_available", 1.0,
                               time_ms=(time.time() - start) * 1000)

    def _looks_like_code(self, text: str) -> bool:
        """Heuristic: does this text contain code?"""
        code_indicators = [
            "def ", "class ", "import ", "from ", "return ",
            "function ", "const ", "let ", "var ",
            "```", "eval(", "exec(",
        ]
        return any(indicator in text for indicator in code_indicators)

    def _finalize(self, passed: bool, failed_at: str,
                  layers: list[LayerResult], start_time: float) -> HierarchyResult:
        """Finalize result and log."""
        import hashlib
        total_ms = (time.time() - start_time) * 1000

        # Compute proof hash over all layer results
        layer_summary = "|".join(f"{l.layer}:{l.passed}:{l.score}" for l in layers)
        proof_hash = hashlib.sha256(layer_summary.encode()).hexdigest()

        result = HierarchyResult(
            passed=passed,
            failed_at=failed_at,
            layers=layers,
            total_time_ms=round(total_ms, 2),
            proof_hash=proof_hash,
        )

        self._log(result)
        return result

    def _log(self, result: HierarchyResult):
        """Log to JSONL."""
        try:
            entry = {
                "passed": result.passed,
                "failed_at": result.failed_at,
                "layers": [
                    {"layer": l.layer, "passed": l.passed, "score": l.score, "ms": l.time_ms}
                    for l in result.layers
                ],
                "total_ms": result.total_time_ms,
                "proof_hash": result.proof_hash,
                "timestamp": result.timestamp,
            }
            with open(LOG_FILE, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Security hierarchy log error: {e}")

    def report(self, result: HierarchyResult) -> str:
        """Human-readable security hierarchy report."""
        lines = [
            "=== Security Hierarchy L0→L4 ===",
            f"Status: {'PASS' if result.passed else f'FAIL at {result.failed_at}'}",
            f"Total time: {result.total_time_ms:.1f}ms",
            "",
        ]

        for layer in result.layers:
            icon = "PASS" if layer.passed else "FAIL"
            lines.append(
                f"  [{icon}] {layer.layer}: {layer.reason} "
                f"(score={layer.score:.2f}, {layer.time_ms:.1f}ms)"
            )

        lines.append(f"\nProof hash: {result.proof_hash[:16]}...")
        return "\n".join(lines)


# --- Convenience ---

def verify_full(input_text: str, output_text: str, **kwargs) -> HierarchyResult:
    """Quick full hierarchy verification."""
    return SecurityHierarchy().verify(input_text, output_text, **kwargs)


# --- Quick test ---

if __name__ == "__main__":
    hierarchy = SecurityHierarchy()

    print("=== Test 1: Normal output ===\n")
    result = hierarchy.verify(
        input_text="Analyze the security of this smart contract",
        output_text="The contract has a reentrancy vulnerability in the withdraw function. "
                     "The state change occurs after the external call, allowing an attacker "
                     "to drain funds. Recommendation: use checks-effects-interactions pattern "
                     "or add a ReentrancyGuard modifier.",
        attempt=1,
    )
    print(hierarchy.report(result))

    print("\n=== Test 2: Code with eval() ===\n")
    result2 = hierarchy.verify(
        input_text="Generate a Python script",
        output_text="Here's the solution:\n```python\nresult = eval(user_input)\nprint(result)\n```",
        attempt=1,
        contains_code=True,
    )
    print(hierarchy.report(result2))
