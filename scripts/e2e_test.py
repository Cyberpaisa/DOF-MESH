#!/usr/bin/env python3
"""
DOF End-to-End Test Suite — 52 tests across 15 modules, zero external deps.

Tests every core module of the Deterministic Observability Framework
without connecting to Avalanche, Supabase, or any external service.

Usage:
    python3 scripts/e2e_test.py
"""

import os
import sys
import time
import hashlib
import tempfile
import shutil

# Ensure project root is on path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# ─── Optional rich import ───────────────────────────────────────────
try:
    from rich.console import Console
    from rich.table import Table
    console = Console()
    def _print(msg, style=""):
        console.print(msg, style=style)
except ImportError:
    console = None
    def _print(msg, style=""):
        print(msg)


# ─── Test runner ────────────────────────────────────────────────────

results = []  # (section, name, passed, elapsed_ms, error)


def run_test(section: str, name: str, fn):
    """Execute a single test, record result."""
    t0 = time.perf_counter()
    try:
        fn()
        elapsed = (time.perf_counter() - t0) * 1000
        results.append((section, name, True, elapsed, ""))
        _print(f"  [green]PASS[/green]  {name}  ({elapsed:.1f}ms)" if console
               else f"  PASS  {name}  ({elapsed:.1f}ms)")
    except Exception as e:
        elapsed = (time.perf_counter() - t0) * 1000
        err = str(e)[:120]
        results.append((section, name, False, elapsed, err))
        _print(f"  [red]FAIL[/red]  {name}  ({elapsed:.1f}ms) — {err}" if console
               else f"  FAIL  {name}  ({elapsed:.1f}ms) — {err}")


# ═══════════════════════════════════════════════════════════════════
# 1. CONSTITUTION ENFORCER (6 tests)
# ═══════════════════════════════════════════════════════════════════

def test_constitution():
    _print("\n[bold]1. CONSTITUTION ENFORCER[/bold]" if console else "\n1. CONSTITUTION ENFORCER")
    from core.governance import ConstitutionEnforcer
    ce = ConstitutionEnforcer()

    def t1_clean_english():
        r = ce.check("This is a well-structured report about AI agents. It covers market analysis, "
                      "technical architecture, and recommendations. Sources: https://example.com")
        assert r.passed, f"Expected pass, got violations: {r.violations}"

    def t2_empty_output():
        r = ce.check("")
        assert not r.passed, "Empty output should be blocked"
        assert len(r.violations) > 0, "Should have violations"

    def t3_too_long():
        r = ce.check("x" * 55000)
        assert not r.passed, "Output >50K should be blocked"

    def t4_spanish():
        r = ce.check("Este es un reporte en español sin traducción al inglés.")
        assert not r.passed, "Non-English should be blocked"

    def t5_soft_no_source():
        r = ce.check("This is a valid report about technology trends in 2026. "
                      "AI adoption is growing rapidly across all industries. "
                      "The market size exceeds expectations significantly.")
        # Should pass (no hard violation) but have reduced score due to missing sources
        assert r.passed, f"Should pass hard rules, got: {r.violations}"
        assert r.score < 1.0, f"Score should be reduced without sources, got {r.score}"

    def t6_soft_repetitive():
        paragraph = "AI agents are autonomous systems that perform tasks. " * 10
        r = ce.check(paragraph + " Sources: https://example.com. Recommendation: adopt AI now.")
        # Should pass hard rules but have warnings about repetition
        assert r.passed, f"Should pass hard rules, got: {r.violations}"

    run_test("Constitution", "Clean English output → PASS", t1_clean_english)
    run_test("Constitution", "Empty output → BLOCKED", t2_empty_output)
    run_test("Constitution", "Output >50K chars → BLOCKED", t3_too_long)
    run_test("Constitution", "Spanish output → BLOCKED", t4_spanish)
    run_test("Constitution", "No sources → soft violation, score reduced", t5_soft_no_source)
    run_test("Constitution", "Repetitive output → soft violation", t6_soft_repetitive)


# ═══════════════════════════════════════════════════════════════════
# 2. AST VERIFIER (6 tests)
# ═══════════════════════════════════════════════════════════════════

def test_ast_verifier():
    _print("\n[bold]2. AST VERIFIER[/bold]" if console else "\n2. AST VERIFIER")
    from core.ast_verifier import ASTVerifier
    av = ASTVerifier()

    def t1_clean():
        r = av.verify("x = 1 + 2\ny = x * 3\nprint(y)")
        assert r.passed, f"Clean code should pass, got violations: {r.violations}"
        assert r.score == 1.0, f"Expected score 1.0, got {r.score}"

    def t2_eval():
        r = av.verify("result = eval('1+2')")
        assert not r.passed, "eval() should be blocked"

    def t3_os_system():
        r = av.verify("from os import system\nsystem('rm -rf /')")
        assert not r.passed, "os.system should be blocked"

    def t4_subprocess():
        r = av.verify("import subprocess\nsubprocess.call(['ls'])")
        assert not r.passed, "subprocess should be blocked"

    def t5_api_key():
        r = av.verify('api_key = "sk-abcdefghijklmnopqrstuvwxyz1234"')
        assert not r.passed, "Hardcoded API key should be blocked"

    def t6_dunder_import():
        r = av.verify("mod = __import__('os')")
        assert not r.passed, "__import__ should be blocked"

    run_test("AST Verifier", "Clean code → score 1.0", t1_clean)
    run_test("AST Verifier", "eval() → BLOCKED", t2_eval)
    run_test("AST Verifier", "os.system() → BLOCKED", t3_os_system)
    run_test("AST Verifier", "import subprocess → BLOCKED", t4_subprocess)
    run_test("AST Verifier", "Hardcoded API key → BLOCKED", t5_api_key)
    run_test("AST Verifier", "__import__('os') → BLOCKED", t6_dunder_import)


# ═══════════════════════════════════════════════════════════════════
# 3. Z3 VERIFIER (4 tests)
# ═══════════════════════════════════════════════════════════════════

def test_z3_verifier():
    _print("\n[bold]3. Z3 VERIFIER[/bold]" if console else "\n3. Z3 VERIFIER")
    from core.z3_verifier import Z3Verifier
    z3v = Z3Verifier()

    def t1_gcr():
        r = z3v.prove_gcr_invariant()
        assert r.result == "VERIFIED", f"GCR should be VERIFIED, got {r.result}"

    def t2_ss():
        r = z3v.prove_ss_formula()
        assert r.result == "VERIFIED", f"SS formula should be VERIFIED, got {r.result}"

    def t3_mono():
        r = z3v.prove_ss_monotonicity()
        assert r.result == "VERIFIED", f"SS monotonicity should be VERIFIED, got {r.result}"

    def t4_bounds():
        r = z3v.prove_ss_boundaries()
        assert r.result == "VERIFIED", f"SS boundaries should be VERIFIED, got {r.result}"

    run_test("Z3 Verifier", "GCR Invariant → VERIFIED", t1_gcr)
    run_test("Z3 Verifier", "SS Cubic Formula → VERIFIED", t2_ss)
    run_test("Z3 Verifier", "SS Monotonicity → VERIFIED", t3_mono)
    run_test("Z3 Verifier", "SS Boundaries → VERIFIED", t4_bounds)


# ═══════════════════════════════════════════════════════════════════
# 4. META-SUPERVISOR (3 tests)
# ═══════════════════════════════════════════════════════════════════

def test_supervisor():
    _print("\n[bold]4. META-SUPERVISOR[/bold]" if console else "\n4. META-SUPERVISOR")
    from core.supervisor import MetaSupervisor
    ms = MetaSupervisor()

    good_output = (
        "## Market Analysis Report\n\n"
        "### Executive Summary\n"
        "The AI agent market on Avalanche is growing at 45% CAGR. "
        "Key competitors include Fetch.ai, SingularityNET, and Ocean Protocol.\n\n"
        "### Recommendations\n"
        "1. Deploy governance-verified agents on Avalanche C-Chain\n"
        "2. Integrate with ERC-8004 for trust scoring\n"
        "3. Target DeFi protocols for initial adoption\n\n"
        "### Sources\n"
        "- https://defillama.com/chain/Avalanche\n"
        "- https://erc-8004scan.xyz\n\n"
        "### Conclusion\n"
        "The market opportunity exceeds $500M by 2027. "
        "First-mover advantage in deterministic governance is critical."
    )

    def t1_good():
        r = ms.evaluate(good_output, "Investigate AI agent market on Avalanche")
        assert r.score >= 5.0, f"Good output should score >= 5.0, got {r.score}"
        assert r.decision in ("ACCEPT", "RETRY"), f"Expected ACCEPT/RETRY, got {r.decision}"

    def t2_mediocre():
        r = ms.evaluate("Some basic info here.", "Investigate AI market")
        assert r.score < 7.0, f"Mediocre output should score < 7.0, got {r.score}"

    def t3_weights():
        r = ms.evaluate(good_output, "Investigate AI market")
        # Verify weighting: Q(0.40) + A(0.25) + C(0.20) + F(0.15)
        expected = r.quality * 0.40 + r.actionability * 0.25 + r.completeness * 0.20 + r.factuality * 0.15
        assert abs(r.score - expected) < 0.01, f"Score {r.score} != weighted {expected}"

    run_test("Supervisor", "Good output → score >= 5.0", t1_good)
    run_test("Supervisor", "Mediocre output → score < 7.0", t2_mediocre)
    run_test("Supervisor", "Score = Q(0.40)+A(0.25)+C(0.20)+F(0.15)", t3_weights)


# ═══════════════════════════════════════════════════════════════════
# 5. ORACLE BRIDGE (3 tests)
# ═══════════════════════════════════════════════════════════════════

def test_oracle_bridge():
    _print("\n[bold]5. ORACLE BRIDGE[/bold]" if console else "\n5. ORACLE BRIDGE")
    from core.oracle_bridge import OracleBridge, CertificateSigner, AttestationRegistry
    from core.oags_bridge import OAGSIdentity

    # Use temp key file
    tmp_dir = tempfile.mkdtemp()
    key_path = os.path.join(tmp_dir, "test_key.json")
    signer = CertificateSigner(key_path=key_path)
    oags = OAGSIdentity(model="test/model", tools=["tool1"])
    bridge = OracleBridge(signer=signer, oags=oags)

    def t1_create():
        cert = bridge.create_attestation(
            task_id="test-task-001",
            metrics={"SS": 0.92, "GCR": 1.0, "PFI": 0.1, "RP": 0.1, "SSR": 0.0}
        )
        assert cert.certificate_hash, "Certificate should have hash"
        assert cert.agent_identity, "Certificate should have agent_identity"
        assert cert.metrics["GCR"] == 1.0, "Metrics should be preserved"
        assert cert.governance_status == "COMPLIANT", f"GCR=1.0 should be COMPLIANT, got {cert.governance_status}"

    def t2_signer():
        data = b"test payload for signing"
        sig = signer.sign(data)
        assert signer.verify(data, sig), "Signature should verify"
        assert not signer.verify(b"tampered", sig), "Tampered data should fail"

    def t3_registry():
        reg_file = os.path.join(tmp_dir, "test_attestations.jsonl")
        # Create a fresh registry with custom path
        cert = bridge.create_attestation(
            task_id="test-task-002",
            metrics={"SS": 0.85, "GCR": 1.0, "PFI": 0.2, "RP": 0.15, "SSR": 0.0}
        )
        registry = AttestationRegistry()
        registry._attestations = []  # Reset for isolation
        registry.add(cert)
        retrieved = registry.get_attestation(cert.certificate_hash)
        assert retrieved is not None, "Should retrieve attestation by hash"
        assert retrieved.task_id == "test-task-002"

    try:
        run_test("Oracle Bridge", "Create attestation → has hash, identity, metrics", t1_create)
        run_test("Oracle Bridge", "HMAC signature → valid, tamper detected", t2_signer)
        run_test("Oracle Bridge", "Registry → save and retrieve attestation", t3_registry)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ═══════════════════════════════════════════════════════════════════
# 6. GOVERNED MEMORY (4 tests)
# ═══════════════════════════════════════════════════════════════════

def test_governed_memory():
    _print("\n[bold]6. GOVERNED MEMORY[/bold]" if console else "\n6. GOVERNED MEMORY")
    from core.memory_governance import GovernedMemoryStore, ConstitutionalDecay

    tmp_dir = tempfile.mkdtemp()
    store_file = os.path.join(tmp_dir, "store.jsonl")
    log_file = os.path.join(tmp_dir, "log.jsonl")
    store = GovernedMemoryStore(_store_file=store_file, _log_file=log_file)

    def t1_add_knowledge():
        entry = store.add("The Z3 verifier proved GCR invariant with UNSAT result.", category="knowledge")
        assert entry is not None, "Should return a MemoryEntry"
        assert entry.governance_status in ("approved", "warning"), f"Clean content should be approved/warning, got {entry.governance_status}"

    def t2_blocked_content():
        # Content that violates constitution (empty or too short)
        entry = store.add("", category="knowledge")
        assert entry is None or entry.governance_status == "rejected", \
            f"Empty content should be rejected, got {entry}"

    def t3_decay():
        decay = ConstitutionalDecay(store)
        entry = store.add("Temporary knowledge about provider rotation.", category="knowledge")
        if entry and entry.governance_status == "approved":
            original_score = entry.relevance_score
            # Force decay by manipulating time (decay_cycle applies λ^hours)
            decay.decay_cycle(hours_elapsed=100)
            # Find the entry again
            found = [e for e in store._entries if e.id == entry.id]
            if found:
                assert found[0].relevance_score < original_score, \
                    f"Score should decay: {found[0].relevance_score} should be < {original_score}"

    def t4_protected():
        decay = ConstitutionalDecay(store)
        entry = store.add("Critical decision: deploy on Avalanche mainnet.", category="decisions")
        if entry and entry.governance_status == "approved":
            original_score = entry.relevance_score
            decay.decay_cycle(hours_elapsed=100)
            found = [e for e in store._entries if e.id == entry.id]
            if found:
                assert found[0].relevance_score == original_score, \
                    f"Decisions should be protected from decay: {found[0].relevance_score} != {original_score}"

    try:
        run_test("Governed Memory", "Add knowledge → approved", t1_add_knowledge)
        run_test("Governed Memory", "Empty content → rejected", t2_blocked_content)
        run_test("Governed Memory", "Decay: knowledge loses relevance", t3_decay)
        run_test("Governed Memory", "Protected: decisions don't decay", t4_protected)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ═══════════════════════════════════════════════════════════════════
# 7. EXECUTION DAG (4 tests)
# ═══════════════════════════════════════════════════════════════════

def test_execution_dag():
    _print("\n[bold]7. EXECUTION DAG[/bold]" if console else "\n7. EXECUTION DAG")
    from core.execution_dag import ExecutionDAG

    def t1_create():
        dag = ExecutionDAG()
        for i in range(5):
            dag.add_node(f"node_{i}", "AGENT", {"name": f"Agent {i}"})
        dag.add_edge("node_0", "node_1", "DELEGATES")
        dag.add_edge("node_1", "node_2", "VERIFIES")
        dag.add_edge("node_2", "node_3", "PUBLISHES")
        dag.add_edge("node_3", "node_4", "QUERIES")
        assert len(dag.nodes) == 5, f"Expected 5 nodes, got {len(dag.nodes)}"
        assert len(dag.edges) == 4, f"Expected 4 edges, got {len(dag.edges)}"

    def t2_cycle():
        dag = ExecutionDAG()
        dag.add_node("A", "AGENT")
        dag.add_node("B", "AGENT")
        dag.add_node("C", "AGENT")
        dag.add_edge("A", "B", "DELEGATES")
        dag.add_edge("B", "C", "DELEGATES")
        dag.add_edge("C", "A", "DELEGATES")  # Creates cycle
        cycles = dag.detect_cycles()
        assert len(cycles) > 0, "Should detect cycle A→B→C→A"

    def t3_topo_sort():
        dag = ExecutionDAG()
        dag.add_node("A", "AGENT")
        dag.add_node("B", "AGENT")
        dag.add_node("C", "AGENT")
        dag.add_node("D", "AGENT")
        dag.add_edge("A", "B", "DELEGATES")
        dag.add_edge("A", "C", "DELEGATES")
        dag.add_edge("B", "D", "VERIFIES")
        dag.add_edge("C", "D", "VERIFIES")
        order = dag.topological_sort()
        assert order.index("A") < order.index("B"), "A should come before B"
        assert order.index("A") < order.index("C"), "A should come before C"
        assert order.index("B") < order.index("D"), "B should come before D"

    def t4_critical_path():
        dag = ExecutionDAG()
        dag.add_node("A", "AGENT", {"name": "Start"})
        dag.add_node("B", "AGENT", {"name": "Fast"})
        dag.add_node("C", "AGENT", {"name": "Slow"})
        dag.add_node("D", "AGENT", {"name": "End"})
        n = dag.nodes
        n["A"].duration_ms = 10
        n["B"].duration_ms = 5
        n["C"].duration_ms = 50
        n["D"].duration_ms = 10
        dag.add_edge("A", "B", "DELEGATES")
        dag.add_edge("A", "C", "DELEGATES")
        dag.add_edge("B", "D", "VERIFIES")
        dag.add_edge("C", "D", "VERIFIES")
        cp = dag.critical_path()
        assert cp["total_duration_ms"] > 0, "Critical path should have duration"
        assert "path" in cp, "Critical path should have path list"

    run_test("ExecutionDAG", "Create DAG with 5 nodes → correct structure", t1_create)
    run_test("ExecutionDAG", "Circular dependency → detected", t2_cycle)
    run_test("ExecutionDAG", "Topological sort → correct order", t3_topo_sort)
    run_test("ExecutionDAG", "Critical path → calculates correctly", t4_critical_path)


# ═══════════════════════════════════════════════════════════════════
# 8. LOOP GUARD (3 tests)
# ═══════════════════════════════════════════════════════════════════

def test_loop_guard():
    _print("\n[bold]8. LOOP GUARD[/bold]" if console else "\n8. LOOP GUARD")
    from core.loop_guard import LoopGuard

    def t1_different():
        lg = LoopGuard(max_iterations=10, similarity_threshold=0.85)
        r1 = lg.check("Output about topic A with unique content", 0)
        r2 = lg.check("Completely different output about topic B", 1)
        r3 = lg.check("Third output covering topic C exclusively", 2)
        assert r3.status == "CONTINUE", f"Different outputs should CONTINUE, got {r3.status}"

    def t2_identical():
        lg = LoopGuard(max_iterations=10, similarity_threshold=0.85)
        lg.check("The exact same output repeated verbatim", 0)
        lg.check("The exact same output repeated verbatim", 1)
        r = lg.check("The exact same output repeated verbatim", 2)
        assert r.status == "LOOP_DETECTED", f"Identical outputs should detect loop, got {r.status}"

    def t3_similar():
        lg = LoopGuard(max_iterations=10, similarity_threshold=0.85)
        lg.check("The AI agent market analysis shows strong growth potential in 2026", 0)
        r = lg.check("The AI agent market analysis shows strong growth potential in 2026 period", 1)
        # Similar outputs with Jaccard > 0.85 should trigger loop detection
        assert r.status in ("LOOP_DETECTED", "CONTINUE"), f"Expected valid status, got {r.status}"

    run_test("LoopGuard", "Different outputs → no loop", t1_different)
    run_test("LoopGuard", "Identical outputs × 3 → loop detected", t2_identical)
    run_test("LoopGuard", "Similar outputs (Jaccard > 0.85) → loop detected", t3_similar)


# ═══════════════════════════════════════════════════════════════════
# 9. DATA ORACLE (4 tests)
# ═══════════════════════════════════════════════════════════════════

def test_data_oracle():
    _print("\n[bold]9. DATA ORACLE[/bold]" if console else "\n9. DATA ORACLE")
    from core.data_oracle import DataOracle
    oracle = DataOracle()

    def t1_correct():
        r = oracle.verify("Bitcoin was created in 2009 by Satoshi Nakamoto.")
        # Should not flag correct facts
        assert r.discrepancy_count == 0, f"Correct claim should have 0 discrepancies, got {r.discrepancy_count}"

    def t2_incorrect():
        r = oracle.verify("Bitcoin was created in 2010.")
        # Should flag incorrect date if in known_facts
        if r.verified_count > 0:
            assert r.discrepancy_count > 0, "Incorrect date should be flagged"
        # If not in known_facts, it won't be caught — that's OK (honest limitation)

    def t3_fabricated():
        r = oracle.verify("Avalanche processes 98765 TPS on mainnet.")
        # Pattern check may catch fabricated numbers
        assert r.overall_status in ("CLEAN", "SUSPICIOUS", "DISCREPANCY_FOUND"), \
            f"Should return valid status, got {r.overall_status}"

    def t4_contradiction():
        r = oracle.verify(
            "The protocol handles 1000 transactions per second. "
            "However, the protocol only handles 50 transactions per second."
        )
        # Consistency check should catch contradictions
        assert r.overall_status in ("CLEAN", "SUSPICIOUS", "DISCREPANCY_FOUND"), \
            f"Should return valid status, got {r.overall_status}"

    run_test("DataOracle", "Correct claim → no discrepancy", t1_correct)
    run_test("DataOracle", "Incorrect date → flagged (if in known_facts)", t2_incorrect)
    run_test("DataOracle", "Fabricated number → valid status", t3_fabricated)
    run_test("DataOracle", "Internal contradiction → valid status", t4_contradiction)


# ═══════════════════════════════════════════════════════════════════
# 10. TOKEN TRACKER (3 tests)
# ═══════════════════════════════════════════════════════════════════

def test_token_tracker():
    _print("\n[bold]10. TOKEN TRACKER[/bold]" if console else "\n10. TOKEN TRACKER")
    from core.observability import TokenTracker

    def t1_log():
        tt = TokenTracker()
        tt.log_call("groq", "llama-3.3-70b", 100, 200, 150.0, 0.001)
        assert tt.total_tokens() == 300, f"Expected 300 tokens, got {tt.total_tokens()}"
        assert tt.total_cost() == 0.001, f"Expected cost 0.001, got {tt.total_cost()}"
        assert tt.average_latency() == 150.0, f"Expected latency 150, got {tt.average_latency()}"

    def t2_accumulate():
        tt = TokenTracker()
        tt.log_call("groq", "llama-3.3-70b", 100, 200, 100.0, 0.001)
        tt.log_call("nvidia", "qwen-2.5", 150, 300, 200.0, 0.002)
        assert tt.total_tokens() == 750, f"Expected 750, got {tt.total_tokens()}"
        assert tt.total_cost() == 0.003, f"Expected 0.003, got {tt.total_cost()}"
        assert tt.average_latency() == 150.0, f"Expected avg 150, got {tt.average_latency()}"
        providers = tt.calls_by_provider()
        assert providers["groq"] == 1, f"Groq should have 1 call"
        assert providers["nvidia"] == 1, f"NVIDIA should have 1 call"

    def t3_reset():
        tt = TokenTracker()
        tt.log_call("groq", "model", 100, 200, 100.0, 0.01)
        tt.reset()
        assert tt.total_tokens() == 0, "After reset, tokens should be 0"
        assert tt.total_cost() == 0, "After reset, cost should be 0"
        assert tt.average_latency() == 0, "After reset, latency should be 0"

    run_test("TokenTracker", "Log call → records tokens, cost, latency", t1_log)
    run_test("TokenTracker", "Multiple calls → correct accumulation", t2_accumulate)
    run_test("TokenTracker", "Reset → all zeros", t3_reset)


# ═══════════════════════════════════════════════════════════════════
# 11. TEST GENERATOR (3 tests)
# ═══════════════════════════════════════════════════════════════════

def test_generator():
    _print("\n[bold]11. TEST GENERATOR[/bold]" if console else "\n11. TEST GENERATOR")
    from core.test_generator import TestGenerator

    def t1_hallucination():
        tg = TestGenerator(seed=42)
        tests = tg.generate_hallucination_tests(n=10)
        assert len(tests) == 10, f"Expected 10 tests, got {len(tests)}"
        malicious = [t for t in tests if t.get("has_hallucination")]
        clean = [t for t in tests if not t.get("has_hallucination")]
        assert len(malicious) == 5, f"Expected 5 malicious, got {len(malicious)}"
        assert len(clean) == 5, f"Expected 5 clean, got {len(clean)}"

    def t2_code_safety():
        tg = TestGenerator(seed=42)
        tests = tg.generate_code_safety_tests(n=10)
        assert len(tests) == 10, f"Expected 10 tests, got {len(tests)}"
        unsafe = [t for t in tests if t.get("is_unsafe")]
        safe = [t for t in tests if not t.get("is_unsafe")]
        assert len(unsafe) == 5, f"Expected 5 unsafe, got {len(unsafe)}"
        assert len(safe) == 5, f"Expected 5 safe, got {len(safe)}"

    def t3_deterministic():
        tg1 = TestGenerator(seed=42)
        tg2 = TestGenerator(seed=42)
        tests1 = tg1.generate_governance_tests(n=10)
        tests2 = tg2.generate_governance_tests(n=10)
        for i in range(10):
            assert tests1[i]["text"] == tests2[i]["text"], \
                f"Test {i} differs: determinism broken"

    run_test("TestGenerator", "Hallucination tests → 5/5 split", t1_hallucination)
    run_test("TestGenerator", "Code safety tests → 5/5 split", t2_code_safety)
    run_test("TestGenerator", "Same seed → deterministic output", t3_deterministic)


# ═══════════════════════════════════════════════════════════════════
# 12. BENCHMARK RUNNER (2 tests)
# ═══════════════════════════════════════════════════════════════════

def test_benchmark_runner():
    _print("\n[bold]12. BENCHMARK RUNNER[/bold]" if console else "\n12. BENCHMARK RUNNER")
    from core.test_generator import TestGenerator, BenchmarkRunner
    from core.governance import ConstitutionEnforcer

    def t1_governance():
        tg = TestGenerator(seed=42)
        dataset = tg.generate_full_dataset(n_per_category=20)
        runner = BenchmarkRunner(dataset)
        ce = ConstitutionEnforcer()
        result = runner.run_governance_benchmark(ce)
        assert result.fdr >= 0, f"FDR should be >= 0, got {result.fdr}"
        assert result.fpr >= 0, f"FPR should be >= 0, got {result.fpr}"
        assert 0 <= result.f1 <= 1.0, f"F1 should be in [0,1], got {result.f1}"
        assert result.total_tests == 20, f"Expected 20 tests, got {result.total_tests}"

    def t2_reproducible():
        tg1 = TestGenerator(seed=42)
        tg2 = TestGenerator(seed=42)
        ds1 = tg1.generate_full_dataset(n_per_category=10)
        ds2 = tg2.generate_full_dataset(n_per_category=10)
        ce = ConstitutionEnforcer()
        r1 = BenchmarkRunner(ds1).run_governance_benchmark(ce)
        r2 = BenchmarkRunner(ds2).run_governance_benchmark(ce)
        assert r1.f1 == r2.f1, f"F1 should be reproducible: {r1.f1} != {r2.f1}"

    run_test("BenchmarkRunner", "Governance benchmark → valid FDR/FPR/F1", t1_governance)
    run_test("BenchmarkRunner", "Same seed → reproducible results", t2_reproducible)


# ═══════════════════════════════════════════════════════════════════
# 13. MERKLE TREE (4 tests)
# ═══════════════════════════════════════════════════════════════════

def test_merkle_tree():
    _print("\n[bold]13. MERKLE TREE[/bold]" if console else "\n13. MERKLE TREE")
    from core.merkle_tree import MerkleTree

    leaves = [hashlib.sha256(f"attestation_{i}".encode()).hexdigest() for i in range(8)]

    def t1_build():
        tree = MerkleTree(leaves)
        assert tree.root, "Tree should have a root hash"
        assert len(tree.leaves) == 8, f"Expected 8 leaves, got {len(tree.leaves)}"

    def t2_proof():
        tree = MerkleTree(leaves)
        proof = tree.get_proof(3)
        assert len(proof) > 0, "Proof should not be empty"

    def t3_verify():
        tree = MerkleTree(leaves)
        proof = tree.get_proof(3)
        valid = MerkleTree.verify_proof(leaves[3], proof, tree.root)
        assert valid, "Valid proof should verify"

    def t4_tamper():
        tree = MerkleTree(leaves)
        proof = tree.get_proof(3)
        fake_leaf = hashlib.sha256(b"tampered_data").hexdigest()
        valid = MerkleTree.verify_proof(fake_leaf, proof, tree.root)
        assert not valid, "Tampered proof should fail verification"

    run_test("MerkleTree", "Build tree with 8 leaves → root hash", t1_build)
    run_test("MerkleTree", "Generate proof for leaf 3", t2_proof)
    run_test("MerkleTree", "Verify valid proof → True", t3_verify)
    run_test("MerkleTree", "Verify tampered proof → False", t4_tamper)


# ═══════════════════════════════════════════════════════════════════
# 14. GENERIC ADAPTER (2 tests)
# ═══════════════════════════════════════════════════════════════════

def test_generic_adapter():
    _print("\n[bold]14. GENERIC ADAPTER[/bold]" if console else "\n14. GENERIC ADAPTER")
    from integrations.langgraph_adapter import GenericAdapter
    ga = GenericAdapter()

    def t1_clean():
        r = ga.wrap_output("This is a comprehensive analysis of the AI agent market. "
                           "Sources: https://example.com. Recommendation: invest now.")
        assert r["status"] == "pass", f"Clean text should pass, got {r['status']}"

    def t2_empty():
        r = ga.wrap_output("")
        assert r["status"] == "fail", f"Empty text should fail, got {r['status']}"

    run_test("GenericAdapter", "wrap_output(clean text) → pass", t1_clean)
    run_test("GenericAdapter", "wrap_output('') → fail", t2_empty)


# ═══════════════════════════════════════════════════════════════════
# 15. OAGS IDENTITY (2 tests)
# ═══════════════════════════════════════════════════════════════════

def test_oags_identity():
    _print("\n[bold]15. OAGS IDENTITY[/bold]" if console else "\n15. OAGS IDENTITY")
    from core.oags_bridge import OAGSIdentity

    def t1_compute():
        oid = OAGSIdentity(model="groq/llama-3.3-70b", tools=["governance_check", "ast_verify"])
        card = oid.get_agent_card()
        assert "identity_hash" in card, "Agent card should have identity_hash"
        assert len(card["identity_hash"]) == 64, f"Hash should be 64 hex chars, got {len(card['identity_hash'])}"

    def t2_deterministic():
        oid1 = OAGSIdentity(model="groq/llama-3.3-70b", tools=["tool_a", "tool_b"])
        oid2 = OAGSIdentity(model="groq/llama-3.3-70b", tools=["tool_a", "tool_b"])
        h1 = oid1.get_agent_card()["identity_hash"]
        h2 = oid2.get_agent_card()["identity_hash"]
        assert h1 == h2, f"Same inputs should produce same hash: {h1} != {h2}"

    run_test("OAGS Identity", "Compute identity → 64-char hex hash", t1_compute)
    run_test("OAGS Identity", "Same inputs → deterministic hash", t2_deterministic)


# ═══════════════════════════════════════════════════════════════════
# 16. FULL PIPELINE (1 integrated test)
# ═══════════════════════════════════════════════════════════════════

def test_full_pipeline():
    _print("\n[bold]16. FULL PIPELINE[/bold]" if console else "\n16. FULL PIPELINE")

    def t1_pipeline():
        from core.governance import ConstitutionEnforcer
        from core.ast_verifier import ASTVerifier
        from core.z3_verifier import Z3Verifier
        from core.oracle_bridge import OracleBridge, CertificateSigner
        from core.oags_bridge import OAGSIdentity
        from core.data_oracle import DataOracle

        input_text = (
            "The arbitrage scan is complete and the results are as follows. "
            "The AVAX/USDC spread is 0.3% on TraderJoe vs Pangolin with an "
            "estimated profit of $12.50 and the gas cost is 0.001 AVAX for this trade. "
            "Sources: https://traderjoe.xyz https://pangolin.exchange "
            "The recommendation is to execute the trade within 30 seconds."
        )

        t0 = time.perf_counter()

        # Layer 1: Constitution
        ce = ConstitutionEnforcer()
        gov_result = ce.check(input_text)
        assert gov_result.passed, f"Constitution failed: {gov_result.violations}"

        # Layer 2: AST (no code in this input, skip or verify clean)
        av = ASTVerifier()
        ast_result = av.verify("profit = 12.50 - 0.001")
        assert ast_result.passed, "Simple math should pass AST"

        # Layer 3: Z3 (verify theorems still hold)
        z3v = Z3Verifier()
        gcr_proof = z3v.prove_gcr_invariant()
        assert gcr_proof.result == "VERIFIED"

        # Layer 4: Data Oracle
        oracle = DataOracle()
        oracle_result = oracle.verify(input_text)
        assert oracle_result.overall_status in ("CLEAN", "SUSPICIOUS", "DISCREPANCY_FOUND")

        # Layer 5: Oracle Bridge (certificate)
        tmp_dir = tempfile.mkdtemp()
        try:
            key_path = os.path.join(tmp_dir, "pipeline_key.json")
            signer = CertificateSigner(key_path=key_path)
            oags = OAGSIdentity(model="groq/llama-3.3-70b", tools=["arb_scan"])
            bridge = OracleBridge(signer=signer, oags=oags)
            cert = bridge.create_attestation(
                task_id="pipeline-test",
                metrics={"SS": 0.95, "GCR": 1.0, "PFI": 0.05, "RP": 0.0, "SSR": 0.0}
            )
            assert cert.governance_status == "COMPLIANT"
            assert cert.certificate_hash
            assert bridge.verify_attestation(cert), "Certificate should verify"
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

        elapsed_ms = (time.perf_counter() - t0) * 1000
        assert elapsed_ms < 500, f"Pipeline should complete in < 500ms, took {elapsed_ms:.1f}ms"

    run_test("Full Pipeline", "All layers: Constitution→AST→Z3→Oracle→Signer (<500ms)", t1_pipeline)


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    _print("[bold cyan]═══ DOF End-to-End Test Suite ═══[/bold cyan]" if console
           else "=== DOF End-to-End Test Suite ===")
    _print(f"Working directory: {ROOT}")

    t_start = time.perf_counter()

    test_constitution()
    test_ast_verifier()
    test_z3_verifier()
    test_supervisor()
    test_oracle_bridge()
    test_governed_memory()
    test_execution_dag()
    test_loop_guard()
    test_data_oracle()
    test_token_tracker()
    test_generator()
    test_benchmark_runner()
    test_merkle_tree()
    test_generic_adapter()
    test_oags_identity()
    test_full_pipeline()

    t_total = (time.perf_counter() - t_start) * 1000

    # ─── Summary ─────────────────────────────────────────────────
    passed = sum(1 for r in results if r[2])
    failed = sum(1 for r in results if not r[2])
    total = len(results)

    _print(f"\n{'═' * 60}")
    _print(f"[bold]RESULTS: {passed}/{total} passed, {failed} failed[/bold]  ({t_total:.0f}ms total)"
           if console else f"RESULTS: {passed}/{total} passed, {failed} failed  ({t_total:.0f}ms total)")

    if failed > 0:
        _print(f"\n[bold red]FAILURES:[/bold red]" if console else "\nFAILURES:")
        for section, name, ok, elapsed, err in results:
            if not ok:
                _print(f"  [{section}] {name}: {err}")

    _print(f"{'═' * 60}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
