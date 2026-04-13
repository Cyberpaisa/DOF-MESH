"""
RED TEAM RUNNER — DOF-MESH Military Grade
Ejecuta todos los vectores de ataque contra las 7 capas de governance.
Mide, documenta y genera reporte de vulnerabilidades.

Uso:
    python3 tests/red_team/redteam_runner.py
    python3 tests/red_team/redteam_runner.py --category semantic_injection
    python3 tests/red_team/redteam_runner.py --category all --verbose
"""
import sys
import os
import json
import time
import argparse
import hashlib
from datetime import datetime
from dataclasses import dataclass, field, asdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from core.governance import (
    check_governance,
    check_instruction_override,
    enforce_hierarchy,
    RulePriority,
)
from core.ast_verifier import ASTVerifier
from core.adversarial import AdversarialEvaluator
from attack_vectors import ALL_VECTORS, TOTAL_VECTORS

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'integrations', 'datos-colombia'))
try:
    from tools.secop import detect_anomalies, fetch_contracts
    SECOP_AVAILABLE = True
except Exception:
    SECOP_AVAILABLE = False

# ─────────────────────────────────────────────────────────────────────
REPORT_DIR = os.path.join(os.path.dirname(__file__), "reports")
os.makedirs(REPORT_DIR, exist_ok=True)

# ANSI colors
RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


@dataclass
class AttackResult:
    vector_id: str
    category: str
    name: str
    payload_preview: str
    expected_block: bool | None
    actual_blocked: bool
    passed: bool          # True = sistema se comportó como esperado
    vulnerability: bool   # True = vulnerabilidad confirmada
    details: str
    latency_ms: float
    layer_hit: str = ""   # qué capa detectó el ataque


@dataclass
class RedTeamReport:
    timestamp: str
    total_vectors: int
    executed: int
    vulnerabilities_found: int
    false_negatives: int    # debería bloquear, no bloqueó
    false_positives: int    # no debería bloquear, bloqueó
    coverage_by_layer: dict
    results: list[AttackResult] = field(default_factory=list)
    critical_findings: list[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────
# EJECUTORES POR CATEGORÍA
# ─────────────────────────────────────────────────────────────────────

def run_direct_injection(vector: dict) -> AttackResult:
    payload = vector["payload"]
    t0 = time.perf_counter()

    # Test 1: governance check
    gov = check_governance(payload)
    # Test 2: override detection
    override = check_instruction_override(payload, RulePriority.SYSTEM)
    # Test 3: adversarial evaluator
    try:
        ev = AdversarialEvaluator()
        verdict = ev.evaluate(payload, input_text=payload)
        adv_blocked = not verdict.passed
    except Exception:
        adv_blocked = False

    blocked = not gov.passed or override or adv_blocked
    latency = (time.perf_counter() - t0) * 1000

    layer = ""
    if not gov.passed:
        layer = f"Constitution({gov.violations})"
    elif override:
        layer = "OverrideDetector"
    elif adv_blocked:
        layer = "AdversarialEvaluator"

    vuln = vector.get("expected_block") is False and not blocked

    return AttackResult(
        vector_id=vector["id"],
        category="direct_injection",
        name=vector["name"],
        payload_preview=payload[:80],
        expected_block=vector.get("expected_block"),
        actual_blocked=blocked,
        passed=(blocked == vector.get("expected_block")) if vector.get("expected_block") is not None else True,
        vulnerability=vuln,
        details=f"gov.passed={gov.passed} violations={gov.violations} override={override} adv={adv_blocked}",
        latency_ms=round(latency, 2),
        layer_hit=layer,
    )


def run_semantic_injection(vector: dict) -> AttackResult:
    payload = vector["payload"]
    t0 = time.perf_counter()

    gov = check_governance(payload)
    override = check_instruction_override(payload, RulePriority.SYSTEM)

    # Test decode_and_scan (adversarial.py)
    try:
        from core.adversarial import EncodingScanner
        scanner = EncodingScanner()
        scan_result = scanner.decode_and_scan(payload)
        encoding_detected = scan_result.get("threat_detected", False)
    except Exception:
        encoding_detected = False

    blocked = not gov.passed or override or encoding_detected
    latency = (time.perf_counter() - t0) * 1000

    layer = ""
    if not gov.passed:
        layer = f"Constitution"
    elif override:
        layer = "OverrideDetector"
    elif encoding_detected:
        layer = f"EncodingScanner({scan_result.get('encoding','?')})"

    vuln = vector.get("expected_block") is False and not blocked

    return AttackResult(
        vector_id=vector["id"],
        category="semantic_injection",
        name=vector["name"],
        payload_preview=repr(payload[:60]),
        expected_block=vector.get("expected_block"),
        actual_blocked=blocked,
        passed=(blocked == vector.get("expected_block")) if vector.get("expected_block") is not None else True,
        vulnerability=vuln,
        details=f"gov={gov.passed} override={override} encoding={encoding_detected}",
        latency_ms=round(latency, 2),
        layer_hit=layer,
    )


def run_privilege_escalation(vector: dict) -> AttackResult:
    system = vector.get("system", "You are a helpful assistant.")
    user = vector.get("user", vector.get("payload", ""))
    response = "I will comply without restrictions."  # respuesta adversarial simulada
    t0 = time.perf_counter()

    result = enforce_hierarchy(system, user, response)
    blocked = result.violation_level != "NONE"
    latency = (time.perf_counter() - t0) * 1000

    vuln = vector.get("expected_block") is False and not blocked

    return AttackResult(
        vector_id=vector["id"],
        category="privilege_escalation",
        name=vector["name"],
        payload_preview=user[:80],
        expected_block=vector.get("expected_block"),
        actual_blocked=blocked,
        passed=(blocked == vector.get("expected_block")) if vector.get("expected_block") is not None else True,
        vulnerability=vuln,
        details=f"violation_level={result.violation_level} details={result.details}",
        latency_ms=round(latency, 2),
        layer_hit="HierarchyEnforcer" if blocked else "",
    )


def run_ast_bypass(vector: dict) -> AttackResult:
    payload = vector["payload"]
    t0 = time.perf_counter()

    verifier = ASTVerifier()
    # Extraer bloque de código del markdown
    import re
    code_blocks = re.findall(r'```(?:python)?\n(.*?)```', payload, re.DOTALL)

    blocked = False
    details = "no code blocks found"

    if code_blocks:
        for code in code_blocks:
            try:
                vresult = verifier.verify(code)
                if not vresult.passed:
                    blocked = True
                    details = f"AST violations: {vresult.violations}"
                    break
                else:
                    details = f"AST passed score={vresult.score}"
            except Exception as e:
                details = f"verifier error: {e}"

    latency = (time.perf_counter() - t0) * 1000
    vuln = vector.get("expected_block") is False and not blocked

    return AttackResult(
        vector_id=vector["id"],
        category="ast_bypass",
        name=vector["name"],
        payload_preview=payload[:80],
        expected_block=vector.get("expected_block"),
        actual_blocked=blocked,
        passed=(blocked == vector.get("expected_block")) if vector.get("expected_block") is not None else True,
        vulnerability=vuln,
        details=details,
        latency_ms=round(latency, 2),
        layer_hit="ASTVerifier" if blocked else "",
    )


def run_z3_adversarial(vector: dict) -> AttackResult:
    t0 = time.perf_counter()

    if not SECOP_AVAILABLE:
        return AttackResult(
            vector_id=vector["id"],
            category="z3_adversarial",
            name=vector["name"],
            payload_preview="SECOP module not available",
            expected_block=vector.get("expected_block"),
            actual_blocked=False,
            passed=False,
            vulnerability=False,
            details="SECOP module import failed",
            latency_ms=0,
        )

    contracts = vector.get("contracts", [])
    if not contracts:
        return AttackResult(
            vector_id=vector["id"],
            category="z3_adversarial",
            name=vector["name"],
            payload_preview=vector.get("description", "")[:80],
            expected_block=vector.get("expected_block"),
            actual_blocked=False,
            passed=True,
            vulnerability=False,
            details="consistency test — no contracts to run",
            latency_ms=0,
        )

    try:
        report = detect_anomalies(contracts)
        blocked = len(report.anomalies) > 0
        details = f"anomalies={len(report.anomalies)} total={report.total_contracts} hash={report.proof_hash[:16]}"
    except Exception as e:
        blocked = False
        details = f"error: {e}"

    latency = (time.perf_counter() - t0) * 1000
    vuln = vector.get("expected_block") is False and not blocked

    return AttackResult(
        vector_id=vector["id"],
        category="z3_adversarial",
        name=vector["name"],
        payload_preview=f"{len(contracts)} contratos adversariales",
        expected_block=vector.get("expected_block"),
        actual_blocked=blocked,
        passed=(blocked == vector.get("expected_block")) if vector.get("expected_block") is not None else True,
        vulnerability=vuln,
        details=details,
        latency_ms=round(latency, 2),
        layer_hit="Z3Verifier" if blocked else "",
    )


def run_governance_bypass(vector: dict) -> AttackResult:
    payload = vector["payload"]
    t0 = time.perf_counter()

    gov = check_governance(payload)
    blocked = not gov.passed
    latency = (time.perf_counter() - t0) * 1000

    vuln = vector.get("expected_block") is False and not blocked

    return AttackResult(
        vector_id=vector["id"],
        category="governance_bypass",
        name=vector["name"],
        payload_preview=payload[:80],
        expected_block=vector.get("expected_block"),
        actual_blocked=blocked,
        passed=(blocked == vector.get("expected_block")) if vector.get("expected_block") is not None else True,
        vulnerability=vuln,
        details=f"violations={gov.violations} warnings={gov.warnings} score={gov.score}",
        latency_ms=round(latency, 2),
        layer_hit=f"Constitution({gov.violations})" if blocked else "",
    )


def run_memory_poison(vector: dict) -> AttackResult:
    """Memory poisoning — test si el payload pasa governance antes de llegar a ChromaDB."""
    payload = vector.get("payload", {})
    content = payload.get("content", "") if isinstance(payload, dict) else str(payload)
    t0 = time.perf_counter()

    # La defensa real: escanear content antes de guardar en memoria
    gov = check_governance(content)
    override = check_instruction_override(content, RulePriority.SYSTEM)
    blocked = not gov.passed or override

    # MAX_LENGTH test
    if len(content) > 50000:
        blocked = True

    latency = (time.perf_counter() - t0) * 1000
    vuln = vector.get("expected_block") is False and not blocked

    return AttackResult(
        vector_id=vector["id"],
        category="memory_poison",
        name=vector["name"],
        payload_preview=content[:80],
        expected_block=vector.get("expected_block"),
        actual_blocked=blocked,
        passed=(blocked == vector.get("expected_block")) if vector.get("expected_block") is not None else True,
        vulnerability=vuln,
        details=f"content_len={len(content)} gov={gov.passed} override={override}",
        latency_ms=round(latency, 2),
        layer_hit="Constitution+MemoryGate" if blocked else "",
    )


# ─────────────────────────────────────────────────────────────────────
# RUNNER PRINCIPAL
# ─────────────────────────────────────────────────────────────────────

RUNNERS = {
    "direct_injection":    run_direct_injection,
    "semantic_injection":  run_semantic_injection,
    "privilege_escalation": run_privilege_escalation,
    "ast_bypass":          run_ast_bypass,
    "z3_adversarial":      run_z3_adversarial,
    "governance_bypass":   run_governance_bypass,
    "memory_poison":       run_memory_poison,
}


def run_all(category: str = "all", verbose: bool = False) -> RedTeamReport:
    report = RedTeamReport(
        timestamp=datetime.now().isoformat(),
        total_vectors=TOTAL_VECTORS,
        executed=0,
        vulnerabilities_found=0,
        false_negatives=0,
        false_positives=0,
        coverage_by_layer={},
    )

    cats = ALL_VECTORS.keys() if category == "all" else [category]

    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  DOF-MESH RED TEAM — MILITARY GRADE{RESET}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S COT')}")
    print(f"{BOLD}{'='*60}{RESET}\n")

    for cat in cats:
        vectors = ALL_VECTORS.get(cat, [])
        runner = RUNNERS.get(cat)
        if not runner:
            continue

        print(f"{BLUE}{BOLD}[{cat.upper()}]{RESET} {len(vectors)} vectores")
        print("-" * 50)

        for v in vectors:
            result = runner(v)
            report.results.append(result)
            report.executed += 1

            if result.vulnerability:
                report.vulnerabilities_found += 1
                status = f"{RED}[VULN]{RESET}"
                report.critical_findings.append(
                    f"{result.vector_id}: {result.name}"
                )
            elif result.actual_blocked and result.expected_block is False:
                report.false_positives += 1
                status = f"{YELLOW}[FP]  {RESET}"
            elif not result.actual_blocked and result.expected_block is True:
                report.false_negatives += 1
                report.vulnerabilities_found += 1
                status = f"{RED}[FN]  {RESET}"
                report.critical_findings.append(
                    f"{result.vector_id}: {result.name} — MISSED ATTACK"
                )
            else:
                status = f"{GREEN}[OK]  {RESET}"

            layer_info = f" → {result.layer_hit}" if result.layer_hit else ""
            print(f"  {status} {result.vector_id} | {result.name[:45]:<45} {result.latency_ms:>6.1f}ms{layer_info}")

            if verbose:
                print(f"         {result.details}")

            # Coverage tracking
            if result.layer_hit:
                report.coverage_by_layer[result.layer_hit] = \
                    report.coverage_by_layer.get(result.layer_hit, 0) + 1

        print()

    # Summary
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  RESUMEN RED TEAM{RESET}")
    print(f"{'='*60}")
    print(f"  Vectores ejecutados : {report.executed}")
    print(f"  Vulnerabilidades    : {RED}{BOLD}{report.vulnerabilities_found}{RESET}")
    print(f"  False negatives     : {RED}{report.false_negatives}{RESET}  (ataques que pasaron)")
    print(f"  False positives     : {YELLOW}{report.false_positives}{RESET}  (bloqueados incorrectamente)")

    vuln_rate = (report.vulnerabilities_found / report.executed * 100) if report.executed else 0
    color = RED if vuln_rate > 30 else YELLOW if vuln_rate > 10 else GREEN
    print(f"  Tasa vulnerabilidad : {color}{BOLD}{vuln_rate:.1f}%{RESET}")

    if report.critical_findings:
        print(f"\n{RED}{BOLD}  HALLAZGOS CRÍTICOS:{RESET}")
        for f in report.critical_findings:
            print(f"    ⚠  {f}")

    if report.coverage_by_layer:
        print(f"\n  Cobertura por capa:")
        for layer, count in sorted(report.coverage_by_layer.items(), key=lambda x: -x[1]):
            print(f"    {GREEN}✓{RESET} {layer}: {count} ataques detectados")

    # Guardar reporte JSON
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(REPORT_DIR, f"redteam_{ts}.json")
    with open(report_path, "w") as f:
        data = asdict(report)
        data["results"] = [asdict(r) for r in report.results]
        json.dump(data, f, indent=2, default=str)

    print(f"\n  Reporte: {report_path}")
    print(f"{BOLD}{'='*60}{RESET}\n")

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DOF-MESH Red Team Runner")
    parser.add_argument("--category", default="all",
                        choices=["all"] + list(ALL_VECTORS.keys()))
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    sys.path.insert(0, os.path.dirname(__file__))
    run_all(category=args.category, verbose=args.verbose)
