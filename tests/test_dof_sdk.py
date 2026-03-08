"""
Tests for dof-sdk v0.2.2 — public API, quick functions, CLI.

All tests are deterministic, no network or LLM calls.
"""

import os
import sys
import json
import unittest
from io import StringIO

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestDOFImports(unittest.TestCase):
    """Test that all public exports are importable."""

    def test_version(self):
        from dof import __version__
        self.assertEqual(__version__, "0.2.4")

    def test_governance_exports(self):
        from dof import (
            Constitution, ConstitutionEnforcer, GovernanceResult,
            load_constitution, get_constitution, HARD_RULES, SOFT_RULES,
            PII_PATTERNS,
        )
        self.assertIsNotNone(Constitution)
        self.assertIsNotNone(PII_PATTERNS)
        self.assertTrue(len(HARD_RULES) >= 4)
        self.assertTrue(len(SOFT_RULES) >= 5)

    def test_metrics_exports(self):
        from dof import Metrics, MetricResult
        self.assertIsNotNone(Metrics)
        self.assertIsNotNone(MetricResult)

    def test_observability_exports(self):
        from dof import (
            RunTrace, StepTrace, RunTraceStore, ErrorClass,
            classify_error, causal_trace, compute_derived_metrics,
            estimate_tokens, set_deterministic, get_session_id,
            reset_session, TokenTracker,
        )
        self.assertIsNotNone(RunTrace)

    def test_ast_verifier_export(self):
        from dof import ASTVerifier
        v = ASTVerifier()
        result = v.verify("x = 1 + 2")
        self.assertTrue(result.passed)

    def test_adversarial_exports(self):
        from dof import (
            AdversarialEvaluator, RedTeamAgent, GuardianAgent,
            DeterministicArbiter,
        )
        self.assertIsNotNone(AdversarialEvaluator)

    def test_data_oracle_export(self):
        from dof import DataOracle, OracleVerdict, FactClaim
        self.assertIsNotNone(DataOracle)

    def test_memory_governance_exports(self):
        from dof import (
            GovernedMemoryStore, TemporalGraph, MemoryClassifier,
            ConstitutionalDecay, MemoryEntry, ConflictError,
        )
        self.assertIsNotNone(GovernedMemoryStore)

    def test_merkle_tree_export(self):
        from dof import MerkleTree, MerkleBatcher, MerkleBatch
        self.assertIsNotNone(MerkleTree)

    def test_execution_dag_export(self):
        from dof import ExecutionDAG, DAGNode, DAGEdge
        self.assertIsNotNone(ExecutionDAG)

    def test_agentleak_exports(self):
        from dof import AgentLeakMapper, PrivacyLeakGenerator, PrivacyBenchmarkRunner
        self.assertIsNotNone(AgentLeakMapper)

    def test_z3_verifier_optional(self):
        from dof import Z3Verifier
        # Z3 is optional — may be None if z3-solver not installed
        # But in our dev environment it should be available
        self.assertIsNotNone(Z3Verifier)

    def test_all_exports_list(self):
        import dof
        self.assertIn("Constitution", dof.__all__)
        self.assertIn("ASTVerifier", dof.__all__)
        self.assertIn("DataOracle", dof.__all__)
        self.assertIn("GenericAdapter", dof.__all__)
        self.assertIn("AgentLeakMapper", dof.__all__)
        self.assertIn("Z3Verifier", dof.__all__)


class TestQuickVerify(unittest.TestCase):
    """Test dof.quick.verify()."""

    def test_verify_clean_text(self):
        from dof.quick import verify
        result = verify(
            "## Analysis Report\n\nThe DOF framework achieves 96.8% F1 score "
            "on adversarial benchmarks. The system processes requests in under "
            "30 milliseconds.\n\nWe recommend continued monitoring."
        )
        self.assertIn("status", result)
        self.assertIn(result["status"], ["pass", "warn", "blocked"])
        self.assertIn("violations", result)
        self.assertIn("layers", result)
        self.assertIn("constitution", result["layers"])
        self.assertIn("ast", result["layers"])
        self.assertIn("oracle", result["layers"])
        self.assertIn("latency_ms", result)
        self.assertGreater(result["latency_ms"], 0)

    def test_verify_returns_blocked_for_violations(self):
        from dof.quick import verify
        # Empty text triggers NO_EMPTY_OUTPUT hard rule
        result = verify("short")
        self.assertEqual(result["status"], "blocked")
        self.assertTrue(len(result["violations"]) > 0)


class TestQuickVerifyCode(unittest.TestCase):
    """Test dof.quick.verify_code()."""

    def test_verify_code_safe(self):
        from dof.quick import verify_code
        result = verify_code("x = 1 + 2\nprint(x)")
        self.assertTrue(result["passed"])
        self.assertIsInstance(result["score"], (int, float))
        self.assertIsInstance(result["violations"], list)
        self.assertIsInstance(result["blocked_patterns"], list)

    def test_verify_code_unsafe(self):
        from dof.quick import verify_code
        result = verify_code('API_KEY = "sk-abc123def456ghi789jkl012mno345pqr678"')
        self.assertFalse(result["passed"])
        self.assertTrue(len(result["violations"]) > 0)


class TestQuickCheckFacts(unittest.TestCase):
    """Test dof.quick.check_facts()."""

    def test_check_facts_basic(self):
        from dof.quick import check_facts
        result = check_facts("Bitcoin was created in 2009 by Satoshi Nakamoto.")
        self.assertIn("overall_status", result)
        self.assertIn("claims_checked", result)
        self.assertIn("verified", result)
        self.assertIn("discrepancies", result)
        self.assertIn("contradictions", result)
        self.assertIn("oracle_score", result)
        self.assertIn("strategies_used", result)
        self.assertIn("latency_ms", result)
        self.assertEqual(len(result["strategies_used"]), 6)


class TestQuickProve(unittest.TestCase):
    """Test dof.quick.prove()."""

    def test_prove_all_verified(self):
        from dof.quick import prove
        result = prove()
        self.assertTrue(result["verified"])
        self.assertIsInstance(result["theorems"], list)
        self.assertTrue(len(result["theorems"]) >= 4)
        for t in result["theorems"]:
            self.assertEqual(t["result"], "VERIFIED")
            self.assertIn("name", t)
            self.assertIn("time_ms", t)


class TestQuickHealth(unittest.TestCase):
    """Test dof.quick.health()."""

    def test_health_components(self):
        from dof.quick import health
        result = health()
        self.assertIn("components", result)
        self.assertIn("total", result)
        self.assertIn("available", result)
        self.assertIn("version", result)
        self.assertEqual(result["version"], "0.2.4")
        self.assertEqual(result["total"], 16)
        self.assertGreater(result["available"], 10)


class TestCLIParsing(unittest.TestCase):
    """Test CLI argument parsing and commands."""

    def test_cli_version_json(self):
        from dof.cli import main
        old_argv = sys.argv
        old_stdout = sys.stdout
        try:
            sys.argv = ["dof", "--json", "version"]
            sys.stdout = StringIO()
            main()
            output = sys.stdout.getvalue()
            data = json.loads(output)
            self.assertEqual(data["version"], "0.2.4")
        finally:
            sys.argv = old_argv
            sys.stdout = old_stdout

    def test_cli_health_json(self):
        from dof.cli import main
        old_argv = sys.argv
        old_stdout = sys.stdout
        try:
            sys.argv = ["dof", "--json", "health"]
            sys.stdout = StringIO()
            main()
            output = sys.stdout.getvalue()
            data = json.loads(output)
            self.assertIn("components", data)
            self.assertEqual(data["version"], "0.2.4")
        finally:
            sys.argv = old_argv
            sys.stdout = old_stdout

    def test_cli_verify_json(self):
        from dof.cli import main
        old_argv = sys.argv
        old_stdout = sys.stdout
        try:
            text = (
                "## Report\n\nThe system achieves excellent performance "
                "across all benchmarks. We recommend continued optimization "
                "and monitoring of key metrics for production readiness."
            )
            sys.argv = ["dof", "--json", "verify", text]
            sys.stdout = StringIO()
            main()
            output = sys.stdout.getvalue()
            data = json.loads(output)
            self.assertIn("status", data)
            self.assertIn("layers", data)
        finally:
            sys.argv = old_argv
            sys.stdout = old_stdout


class TestMainModule(unittest.TestCase):
    """Test dof.__main__ delegates to cli."""

    def test_main_importable(self):
        import dof.__main__
        self.assertTrue(hasattr(dof.__main__, "main"))


if __name__ == "__main__":
    unittest.main()
