"""
DOF Quick API — convenience functions for common operations.

Usage:
    from dof.quick import verify, verify_code, check_facts, prove, benchmark

    result = verify("Bitcoin was created in 2009")
    code_result = verify_code("x = eval(input())")
    facts = check_facts("Ethereum launched in 2015")
    proofs = prove()
    bench = benchmark()
"""

import re
import time


def verify(text: str) -> dict:
    """Run Constitution + AST + DataOracle in one call.

    Returns:
        {status, violations, score, layers: {constitution, ast, oracle}, latency_ms}
    """
    from core.governance import ConstitutionEnforcer
    from core.ast_verifier import ASTVerifier
    from core.data_oracle import DataOracle

    start = time.time()
    violations = []
    layers = {}

    # Constitution check
    enforcer = ConstitutionEnforcer()
    gov_result = enforcer.check(text)
    layers["constitution"] = {
        "passed": gov_result.passed,
        "score": gov_result.score,
        "violations": gov_result.violations,
        "warnings": gov_result.warnings,
    }
    violations.extend(gov_result.violations)

    # AST check on embedded code blocks
    code_blocks = re.findall(r'```(?:python|py)?\s*\n(.*?)```', text, re.DOTALL)
    ast_violations = []
    verifier = ASTVerifier()
    for block in code_blocks:
        ast_result = verifier.verify(block.strip())
        if not ast_result.passed:
            ast_violations.extend(ast_result.violations)
    layers["ast"] = {
        "code_blocks_found": len(code_blocks),
        "violations": ast_violations,
        "passed": len(ast_violations) == 0,
    }
    for v in ast_violations:
        violations.append(f"[AST] {v.get('message', str(v))}")

    # DataOracle check
    oracle = DataOracle()
    verdict = oracle.verify(text)
    layers["oracle"] = {
        "overall_status": verdict.overall_status,
        "verified_count": verdict.verified_count,
        "discrepancy_count": verdict.discrepancy_count,
        "contradiction_count": verdict.contradiction_count,
        "oracle_score": verdict.oracle_score,
    }
    if verdict.discrepancy_count > 0:
        violations.append(f"[ORACLE] {verdict.discrepancy_count} factual discrepancies found")

    elapsed = (time.time() - start) * 1000

    if not gov_result.passed:
        status = "blocked"
    elif violations:
        status = "warn"
    else:
        status = "pass"

    return {
        "status": status,
        "violations": violations,
        "score": gov_result.score,
        "layers": layers,
        "latency_ms": round(elapsed, 2),
    }


def verify_code(code: str) -> dict:
    """AST verification only.

    Returns:
        {score, violations, blocked_patterns, latency_ms}
    """
    from core.ast_verifier import ASTVerifier

    start = time.time()
    verifier = ASTVerifier()
    result = verifier.verify(code)
    elapsed = (time.time() - start) * 1000

    blocked_patterns = list({v.get("rule_id", "") for v in result.violations
                            if v.get("severity") == "block"})

    return {
        "passed": result.passed,
        "score": result.score,
        "violations": result.violations,
        "blocked_patterns": blocked_patterns,
        "latency_ms": round(elapsed, 2),
    }


def check_facts(text: str) -> dict:
    """DataOracle fact-checking only.

    Returns:
        {claims_checked, verified, discrepancies, contradictions, flags, strategies_used, latency_ms}
    """
    from core.data_oracle import DataOracle

    start = time.time()
    oracle = DataOracle()
    verdict = oracle.verify(text)
    elapsed = (time.time() - start) * 1000

    flags = []
    for claim in verdict.fact_claims:
        if isinstance(claim, dict) and claim.get("status") == "DISCREPANCY":
            flags.append({
                "claim": claim.get("claim_text", ""),
                "extracted": claim.get("extracted_value"),
                "expected": claim.get("verified_value"),
                "evidence": claim.get("evidence", ""),
            })
    for contradiction in verdict.contradictions:
        if isinstance(contradiction, dict):
            flags.append({
                "type": "contradiction",
                "entity": contradiction.get("entity", ""),
                "value_1": contradiction.get("value_1", ""),
                "value_2": contradiction.get("value_2", ""),
            })

    strategies_used = [
        "pattern_check", "cross_reference_check", "consistency_check",
        "entity_extraction_check", "numerical_plausibility_check",
        "self_consistency_check",
    ]

    return {
        "overall_status": verdict.overall_status,
        "claims_checked": verdict.verified_count + verdict.discrepancy_count + verdict.unverified_count,
        "verified": verdict.verified_count,
        "discrepancies": verdict.discrepancy_count,
        "contradictions": verdict.contradiction_count,
        "oracle_score": verdict.oracle_score,
        "flags": flags,
        "strategies_used": strategies_used,
        "latency_ms": round(elapsed, 2),
    }


def prove() -> dict:
    """Run Z3 verify_all().

    Returns:
        {verified, theorems: [{name, result, time_ms}], total_ms}
    """
    from core.z3_verifier import Z3Verifier

    start = time.time()
    verifier = Z3Verifier()
    results = verifier.verify_all()
    elapsed = (time.time() - start) * 1000

    theorems = []
    for r in results:
        theorems.append({
            "name": r.theorem_name,
            "result": r.result,
            "time_ms": round(r.proof_time_ms, 2),
        })

    all_verified = all(r.result == "VERIFIED" for r in results)

    return {
        "verified": all_verified,
        "theorems": theorems,
        "total_ms": round(elapsed, 2),
    }


def benchmark(category: str = "all") -> dict:
    """Run BenchmarkRunner.

    Args:
        category: "all", "governance", "code_safety", "hallucination", or "consistency"

    Returns:
        {categories: [{name, fdr, fpr, f1, tests}], overall_f1, total_ms}
    """
    from core.test_generator import TestGenerator, BenchmarkRunner

    start = time.time()
    gen = TestGenerator(seed=42)
    dataset = gen.generate_full_dataset(n_per_category=100)
    runner = BenchmarkRunner(dataset)
    results = runner.run_full_benchmark()
    elapsed = (time.time() - start) * 1000

    # Clean up dataset file
    import os
    if "path" in dataset and os.path.exists(dataset["path"]):
        os.unlink(dataset["path"])

    valid_cats = ["hallucination", "code_safety", "governance", "consistency"]
    if category != "all" and category in valid_cats:
        cats_to_show = [category]
    else:
        cats_to_show = valid_cats

    categories = []
    for cat in cats_to_show:
        r = results[cat]
        categories.append({
            "name": cat,
            "fdr": r["fdr"],
            "fpr": r["fpr"],
            "f1": r["f1"],
            "tests": r["total_tests"],
        })

    return {
        "categories": categories,
        "overall_f1": results["overall_f1"],
        "total_ms": round(elapsed, 2),
    }


def privacy_benchmark() -> dict:
    """Run AgentLeak PrivacyBenchmarkRunner.

    Returns:
        {categories: [{name, dr, fpr, f1}], overall_dr, overall_fpr, total_ms}
    """
    from core.agentleak_benchmark import PrivacyLeakGenerator, PrivacyBenchmarkRunner

    start = time.time()
    gen = PrivacyLeakGenerator(seed=42)
    dataset = gen.generate_full_dataset(n_per_category=50)
    runner = PrivacyBenchmarkRunner(dataset)
    results = runner.run_full_benchmark()
    elapsed = (time.time() - start) * 1000

    # Clean up dataset file
    import os
    if "path" in dataset and os.path.exists(dataset["path"]):
        os.unlink(dataset["path"])

    categories = []
    for cat in ["PII_LEAK", "API_KEY_LEAK", "MEMORY_LEAK", "TOOL_INPUT_LEAK"]:
        r = results[cat]
        categories.append({
            "name": cat,
            "dr": r["dr"],
            "fpr": r["fpr"],
            "f1": r["f1"],
        })

    overall = results["overall"]
    return {
        "categories": categories,
        "overall_dr": overall["overall_dr"],
        "overall_fpr": overall["overall_fpr"],
        "overall_f1": overall["overall_f1"],
        "total_ms": round(elapsed, 2),
    }


def health() -> dict:
    """Status check of all components.

    Returns:
        {components: {name: bool}, total, available, version}
    """
    from dof import __version__

    components = {}

    checks = [
        ("ConstitutionEnforcer", "core.governance", "ConstitutionEnforcer"),
        ("ASTVerifier", "core.ast_verifier", "ASTVerifier"),
        ("DataOracle", "core.data_oracle", "DataOracle"),
        ("GovernedMemoryStore", "core.memory_governance", "GovernedMemoryStore"),
        ("ExecutionDAG", "core.execution_dag", "ExecutionDAG"),
        ("LoopGuard", "core.loop_guard", "LoopGuard"),
        ("TokenTracker", "core.observability", "TokenTracker"),
        ("MerkleTree", "core.merkle_tree", "MerkleTree"),
        ("CertificateSigner", "core.oracle_bridge", "CertificateSigner"),
        ("OAGSIdentity", "core.oags_bridge", "OAGSIdentity"),
        ("GenericAdapter", "integrations.langgraph_adapter", "GenericAdapter"),
        ("TestGenerator", "core.test_generator", "TestGenerator"),
        ("AgentLeakMapper", "core.agentleak_benchmark", "AgentLeakMapper"),
        ("Z3Verifier", "core.z3_verifier", "Z3Verifier"),
        ("BayesianProviderSelector", "core.providers", "BayesianProviderSelector"),
        ("RuntimeObserver", "core.runtime_observer", "RuntimeObserver"),
    ]

    for name, module, cls_name in checks:
        try:
            mod = __import__(module, fromlist=[cls_name])
            getattr(mod, cls_name)
            components[name] = True
        except (ImportError, AttributeError):
            components[name] = False

    total = len(components)
    available = sum(1 for v in components.values() if v)

    return {
        "components": components,
        "total": total,
        "available": available,
        "version": __version__,
    }
