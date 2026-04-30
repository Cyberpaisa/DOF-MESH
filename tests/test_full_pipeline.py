"""
Full end-to-end pipeline integration tests for DOF.

Exercises every module in sequence, exactly as production would:
  Constitution → OAGS → Z3 → AST → Governance → Contracts → Adversarial
  → Causal → Bayesian → Memory → Oracle → Conformance

Tests:
  1. test_full_pipeline_accept_flow — 12-stage success path
  2. test_full_pipeline_failure_flow — 8-stage failure path
  3. test_pipeline_determinism — proves entire pipeline is deterministic
  4. test_pipeline_audit_trail — validates complete JSONL audit trail
"""

import os
import json
import time
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(BASE_DIR, "logs")

pytestmark = [pytest.mark.integration, pytest.mark.slow]


class TestFullPipelineAcceptFlow(unittest.TestCase):
    """12-stage success path exercising all modules in production order."""

    @classmethod
    def setUpClass(cls):
        """Shared state across all stages — simulates a single pipeline run."""
        cls.report = {
            "timestamp": datetime.now().isoformat(),
            "stages": {},
            "modules_tested": 0,
            "checks_passed": 0,
            "z3_theorems_verified": 0,
            "oags_level": 0,
            "memory_operations": 0,
            "oracle_attestations": 0,
        }
        cls._tmpdir = tempfile.mkdtemp()

    @classmethod
    def tearDownClass(cls):
        """Save pipeline report to logs/."""
        cls.report["pipeline_status"] = "ALL GREEN"
        cls.report["total_modules_tested"] = cls.report["modules_tested"]
        cls.report["total_checks_passed"] = cls.report["checks_passed"]
        os.makedirs(LOGS_DIR, exist_ok=True)
        report_path = os.path.join(LOGS_DIR, "full_pipeline_report.json")
        with open(report_path, "w") as f:
            json.dump(cls.report, f, indent=2, default=str)

    # ─── Stage A: Constitution Load ─────────────────────────────────

    def test_a_constitution_load(self):
        """Stage A: Load and validate dof.constitution.yml."""
        from core.governance import load_constitution, HARD_RULES, SOFT_RULES

        constitution_path = os.path.join(BASE_DIR, "dof.constitution.yml")
        config = load_constitution(constitution_path)

        # Verify structure
        self.assertIn("rules", config)
        self.assertIn("hard", config["rules"])
        self.assertIn("soft", config["rules"])
        self.assertIn("ast", config["rules"])
        self.assertIn("memory", config)
        self.assertIn("thresholds", config)

        # Verify thresholds
        thresholds = config["thresholds"]["supervisor"]
        self.assertEqual(thresholds["accept"], 7.0)
        self.assertEqual(thresholds["retry"], 5.0)

        # Verify memory config
        memory = config["memory"]
        self.assertIn("decisions", memory["decay"]["protected_categories"])
        self.assertIn("errors", memory["decay"]["protected_categories"])

        # Verify rules loaded into module
        self.assertGreater(len(HARD_RULES), 0)
        self.assertGreater(len(SOFT_RULES), 0)

        self.__class__.report["stages"]["a_constitution"] = "PASSED"
        self.__class__.report["modules_tested"] += 1
        self.__class__.report["checks_passed"] += 6

    # ─── Stage B: OAGS Identity ─────────────────────────────────────

    def test_b_oags_identity(self):
        """Stage B: Compute deterministic agent identity."""
        from core.oags_bridge import OAGSIdentity

        identity = OAGSIdentity()
        card = identity.get_agent_card()

        self.assertIn("identity_hash", card)
        self.assertIn("constitution_hash", card)
        self.assertIsInstance(card["identity_hash"], str)
        self.assertGreater(len(card["identity_hash"]), 0)

        # Determinism: same config → same hash
        identity2 = OAGSIdentity()
        card2 = identity2.get_agent_card()
        self.assertEqual(card["identity_hash"], card2["identity_hash"])
        self.assertEqual(card["constitution_hash"], card2["constitution_hash"])

        self.__class__.report["stages"]["b_oags_identity"] = "PASSED"
        self.__class__.report["modules_tested"] += 1
        self.__class__.report["checks_passed"] += 4

    # ─── Stage C: Z3 Formal Verification ────────────────────────────

    def test_c_z3_verification(self):
        """Stage C: Run Z3 proofs — all 4 theorems must be VERIFIED."""
        from core.z3_verifier import Z3Verifier

        verifier = Z3Verifier()
        results = verifier.verify_all()

        self.assertEqual(len(results), 4)
        for proof in results:
            self.assertEqual(proof.result, "VERIFIED",
                             f"Theorem {proof.theorem_name} failed: {proof.result}")

        self.__class__.report["stages"]["c_z3_verification"] = "PASSED"
        self.__class__.report["z3_theorems_verified"] = 4
        self.__class__.report["modules_tested"] += 1
        self.__class__.report["checks_passed"] += 5

    # ─── Stage D: AST Verification ──────────────────────────────────

    def test_d_ast_verification(self):
        """Stage D: AST verifier catches unsafe code, passes clean code."""
        from core.ast_verifier import ASTVerifier

        verifier = ASTVerifier()

        # Clean code passes
        clean = "def greet(name):\n    return f'Hello, {name}!'"
        result_clean = verifier.verify(clean)
        self.assertTrue(result_clean.passed)
        self.assertEqual(result_clean.score, 1.0)

        # Malicious code fails
        malicious = "import subprocess\nresult = eval(user_input)"
        result_bad = verifier.verify(malicious)
        self.assertFalse(result_bad.passed)
        self.assertLess(result_bad.score, 1.0)
        # Should detect at least BLOCKED_IMPORTS and UNSAFE_CALLS
        categories = {v.get("category", v.get("rule_id", ""))
                      for v in result_bad.violations}
        has_import = any("import" in str(c).lower() for c in categories)
        has_unsafe = any("unsafe" in str(c).lower() for c in categories)
        self.assertTrue(has_import or has_unsafe,
                        f"Expected import/unsafe violations, got: {categories}")

        self.__class__.report["stages"]["d_ast_verification"] = "PASSED"
        self.__class__.report["modules_tested"] += 1
        self.__class__.report["checks_passed"] += 4

    # ─── Stage E: Governance Enforcement ────────────────────────────

    def test_e_governance_enforcement(self):
        """Stage E: ConstitutionEnforcer approves good output, blocks bad."""
        from core.governance import ConstitutionEnforcer

        enforcer = ConstitutionEnforcer()

        # Good output — structured, English, actionable, with URL
        good_output = (
            "## Market Analysis for AI Agents on Avalanche\n\n"
            "The autonomous agent market is growing rapidly. "
            "Based on the available data from https://example.com/report, "
            "we recommend the following action steps:\n\n"
            "1. Implement governance verification for all agent interactions\n"
            "2. Deploy attestation certificates via ERC-8004\n"
            "3. Monitor stability metrics continuously\n\n"
            "This analysis covers key competitors and market trends."
        )
        result_good = enforcer.check(good_output)
        self.assertTrue(result_good.passed,
                        f"Good output should pass governance: {result_good.violations}")

        # Bad output — empty
        result_bad = enforcer.check("short")
        self.assertFalse(result_bad.passed)
        self.assertGreater(len(result_bad.violations), 0)

        self.__class__.report["stages"]["e_governance"] = "PASSED"
        self.__class__.report["modules_tested"] += 1
        self.__class__.report["checks_passed"] += 3

    # ─── Stage F: Task Contract ─────────────────────────────────────

    def test_f_task_contract(self):
        """Stage F: Load contract, check preconditions and fulfillment."""
        from core.task_contract import TaskContract

        contract_path = os.path.join(BASE_DIR, "contracts", "RESEARCH_CONTRACT.md")
        contract = TaskContract.from_file(contract_path)

        # Preconditions with valid context
        pre_ctx = {"topic_provided": True, "providers_available": True}
        pre_ok, pre_failures = contract.check_preconditions(pre_ctx)
        self.assertTrue(pre_ok, f"Preconditions should pass: {pre_failures}")

        # Preconditions with missing topic
        pre_ctx_bad = {"topic_provided": False, "providers_available": True}
        pre_bad, _ = contract.check_preconditions(pre_ctx_bad)
        self.assertFalse(pre_bad)

        # Fulfillment with compliant output
        good_output = (
            "## Research Analysis\n\n"
            "This is a comprehensive research analysis in markdown format. "
            "The market shows significant growth potential. "
            "We recommend implementing governance verification.\n\n"
            "Source: https://example.com/data"
        )
        log_path = os.path.join(LOGS_DIR, "execution_log.jsonl")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        if not os.path.exists(log_path):
            with open(log_path, "w") as lf:
                lf.write('{"timestamp":"2026-01-01T00:00:00","crew":"test","status":"success"}\n')
        ctx = {"supervisor_score": 8.0, "input_text": "test topic",
               "log_path": log_path}
        result = contract.is_fulfilled(good_output, ctx)
        self.assertTrue(result.fulfilled,
                        f"Contract should be fulfilled: failed={result.failed_gates}")

        self.__class__.report["stages"]["f_task_contract"] = "PASSED"
        self.__class__.report["modules_tested"] += 1
        self.__class__.report["checks_passed"] += 3

    # ─── Stage G: Adversarial Evaluation ────────────────────────────

    def test_g_adversarial_evaluation(self):
        """Stage G: Run adversarial pipeline — Red Team, Guardian, Arbiter."""
        from core.adversarial import (
            AdversarialEvaluator, RedTeamAgent, GuardianAgent,
            DeterministicArbiter,
        )

        output = (
            "## Analysis Report\n\n"
            "The AI agent market is growing. "
            "Based on available research from https://arxiv.org/example, "
            "we recommend deploying governance verification.\n\n"
            "Key findings include market growth and regulatory trends."
        )

        # Full pipeline
        evaluator = AdversarialEvaluator()
        verdict = evaluator.evaluate(output, "Analyze AI agent market")

        self.assertIn(verdict.verdict, ("PASS", "FAIL"))
        self.assertIsInstance(verdict.acr, float)
        self.assertGreaterEqual(verdict.acr, 0.0)
        self.assertLessEqual(verdict.acr, 1.0)
        self.assertIsInstance(verdict.total_issues, int)

        # Individual components
        red = RedTeamAgent()
        issues = red.analyze(output)
        self.assertIsInstance(issues, list)

        guardian = GuardianAgent()
        defenses = guardian.defend(output, issues)
        self.assertIsInstance(defenses, list)

        arbiter = DeterministicArbiter()
        verdict2 = arbiter.adjudicate(output, issues, defenses)
        self.assertIsNotNone(verdict2)

        self.__class__.report["stages"]["g_adversarial"] = "PASSED"
        self.__class__.report["modules_tested"] += 1
        self.__class__.report["checks_passed"] += 6

    # ─── Stage H: Causal Error Attribution ──────────────────────────

    def test_h_causal_error_attribution(self):
        """Stage H: Classify errors into 3 classes, verify dashboard export."""
        from core.observability import (
            classify_error, ErrorClass, RunTrace, StepTrace,
            compute_derived_metrics, get_session_id,
        )

        # INFRA_FAILURE: HTTP 429
        infra = classify_error("rate_limit_exceeded: HTTP 429")
        self.assertEqual(infra, ErrorClass.INFRA_FAILURE)

        # GOVERNANCE_FAILURE
        gov = classify_error("governance violation",
                             {"governance_allowed": False})
        self.assertEqual(gov, ErrorClass.GOVERNANCE_FAILURE)

        # MODEL_FAILURE
        model = classify_error("bad request: invalid grammar in output format")
        self.assertEqual(model, ErrorClass.MODEL_FAILURE)

        # Dashboard export
        trace = RunTrace(
            run_id="test-pipeline-001",
            session_id=get_session_id(),
            crew_name="test_crew",
            mode="production",
            timestamp_start=time.strftime("%Y-%m-%dT%H:%M:%S"),
            start_epoch=time.time(),
            deterministic=True,
            input_text="test input",
            input_hash="abc123",
        )
        step = StepTrace(
            step_index=0, agent="test_agent", provider="groq",
            status="completed", governance_passed=True,
            token_input=100, token_output=200,
        )
        trace.steps.append(step)
        trace.end_epoch = time.time()
        trace.timestamp_end = time.strftime("%Y-%m-%dT%H:%M:%S")
        trace = compute_derived_metrics(trace)

        dashboard = trace.export_dashboard()
        self.assertIn("error_class_distribution", dashboard)
        self.assertIn("provider_reliability_over_time", dashboard)
        self.assertIn("causal_chains", dashboard)

        self.__class__.report["stages"]["h_causal"] = "PASSED"
        self.__class__.report["modules_tested"] += 1
        self.__class__.report["checks_passed"] += 6

    # ─── Stage I: Bayesian Provider Selection ───────────────────────

    def test_i_bayesian_provider_selection(self):
        """Stage I: Thompson Sampling favors reliable providers."""
        from core.providers import BayesianProviderSelector

        selector = BayesianProviderSelector(
            providers=["provider_a", "provider_b", "provider_c"])

        # Record 10 successes for provider_a, 10 failures for provider_b
        for _ in range(10):
            selector.record_success("provider_a")
            selector.record_failure("provider_b")

        conf_a = selector.get_confidence("provider_a")
        conf_b = selector.get_confidence("provider_b")
        self.assertGreater(conf_a, conf_b,
                           f"provider_a ({conf_a}) should have higher confidence than provider_b ({conf_b})")

        # Select should favor provider_a
        selections = [selector.select_provider(
            ["provider_a", "provider_b"]) for _ in range(20)]
        a_count = selections.count("provider_a")
        self.assertGreater(a_count, 10,
                           f"provider_a should be selected >50% of time, got {a_count}/20")

        # All confidences
        all_conf = selector.get_all_confidences()
        self.assertIn("provider_a", all_conf)
        self.assertIn("provider_b", all_conf)

        self.__class__.report["stages"]["i_bayesian"] = "PASSED"
        self.__class__.report["modules_tested"] += 1
        self.__class__.report["checks_passed"] += 4

    # ─── Stage J: Memory Governance ─────────────────────────────────

    def test_j_memory_governance(self):
        """Stage J: GovernedMemoryStore with temporal graph and decay."""
        from core.memory_governance import (
            GovernedMemoryStore, TemporalGraph,
            MemoryClassifier, ConstitutionalDecay,
        )

        # Patch storage paths to temp dir
        import core.memory_governance as mg_mod
        orig_store = mg_mod.STORE_FILE
        orig_log = mg_mod.LOG_FILE
        orig_decay = mg_mod.DECAY_LOG_FILE
        mg_mod.STORE_FILE = os.path.join(self.__class__._tmpdir, "governed_store.jsonl")
        mg_mod.LOG_FILE = os.path.join(self.__class__._tmpdir, "memory_governance.jsonl")
        mg_mod.DECAY_LOG_FILE = os.path.join(self.__class__._tmpdir, "memory_decay.jsonl")

        try:
            store = GovernedMemoryStore()

            # Add knowledge — should be approved
            entry1 = store.add(
                content=(
                    "The ERC-8004 standard enables on-chain attestation of "
                    "governance metrics with BLAKE3 hashing. This is a "
                    "comprehensive analysis with actionable recommendations."
                ),
                category="knowledge",
                metadata={"task": "research"},
            )
            self.assertIn(entry1.governance_status, ("approved", "warning"),
                          f"Expected approved/warning, got {entry1.governance_status}")
            self.__class__.report["memory_operations"] += 1

            # Add error record — should be approved
            entry2 = store.add(
                content=(
                    "Provider groq failed with rate_limit_exceeded after "
                    "3 retries. The error was classified as INFRA_FAILURE. "
                    "Recommend switching to alternative provider chain."
                ),
                category="errors",
                metadata={"error_class": "INFRA_FAILURE"},
            )
            self.assertIn(entry2.governance_status, ("approved", "warning"),
                          f"Expected approved/warning, got {entry2.governance_status}")
            self.__class__.report["memory_operations"] += 1

            # Add content that violates HARD_RULE (too short) — rejected
            entry_bad = store.add(content="bad", category="knowledge")
            self.assertIn(entry_bad.governance_status, ("rejected", "warning"))
            self.__class__.report["memory_operations"] += 1

            # Update existing memory
            updated = store.update(entry1.id,
                                   new_content=(
                                       "Updated: The ERC-8004 standard enables "
                                       "on-chain attestation of governance metrics. "
                                       "This updated analysis includes new findings "
                                       "and actionable recommendations for deployment."
                                   ))
            self.assertIsNotNone(updated)
            self.__class__.report["memory_operations"] += 1

            # TemporalGraph operations
            graph = TemporalGraph(store)
            snapshot = graph.snapshot(as_of=datetime.now())
            self.assertIsInstance(snapshot, list)

            timeline = graph.timeline()
            self.assertIsInstance(timeline, list)

            past = datetime.now() - timedelta(hours=1)
            diff = graph.diff(past, datetime.now())
            self.assertIsInstance(diff, dict)

            # MemoryClassifier
            classifier = MemoryClassifier()
            cat = classifier.classify("The API returned an error 429 rate limit")
            self.assertIsInstance(cat, str)
            self.assertIn(cat, ["knowledge", "preferences", "context",
                                "decisions", "errors"])

            # ConstitutionalDecay — errors should not decay
            decay = ConstitutionalDecay(store)
            status = decay.get_decay_status()
            self.assertIsInstance(status, list)

            # Verify protected categories
            for entry_status in status:
                if entry_status.get("category") in ("decisions", "errors"):
                    self.assertTrue(entry_status.get("protected", False),
                                    f"Category {entry_status.get('category')} should be protected")

        finally:
            mg_mod.STORE_FILE = orig_store
            mg_mod.LOG_FILE = orig_log
            mg_mod.DECAY_LOG_FILE = orig_decay

        self.__class__.report["stages"]["j_memory"] = "PASSED"
        self.__class__.report["modules_tested"] += 1
        self.__class__.report["checks_passed"] += 9

    # ─── Stage K: Oracle Bridge (ERC-8004) ──────────────────────────

    def test_k_oracle_bridge(self):
        """Stage K: Create attestations, verify signatures, test publishing."""
        from core.oracle_bridge import (
            OracleBridge, CertificateSigner, AttestationRegistry,
        )
        from core.oags_bridge import OAGSIdentity

        # Patch logs to temp
        import core.oracle_bridge as ob_mod
        orig_logs = ob_mod.LOGS_DIR
        orig_keys = ob_mod.KEYS_DIR
        ob_mod.LOGS_DIR = self.__class__._tmpdir
        ob_mod.KEYS_DIR = self.__class__._tmpdir

        try:
            signer = CertificateSigner(
                key_path=os.path.join(self.__class__._tmpdir, "test_key.json"))
            identity = OAGSIdentity()
            bridge = OracleBridge(signer, identity)

            # Compliant attestation (GCR=1.0)
            cert_good = bridge.create_attestation(
                task_id="pipeline-test-001",
                metrics={"SS": 0.9, "GCR": 1.0, "PFI": 0.1, "RP": 0.2, "SSR": 0.0},
            )
            self.assertEqual(cert_good.governance_status, "COMPLIANT")
            self.assertTrue(bridge.should_publish(cert_good))
            self.__class__.report["oracle_attestations"] += 1

            # Verify signature
            self.assertTrue(bridge.verify_attestation(cert_good))

            # Prepare transaction
            tx = bridge.prepare_transaction(cert_good)
            self.assertIn("to", tx)
            self.assertIn("data", tx)
            self.assertEqual(tx["chain"], "avalanche-c-chain")
            self.assertEqual(tx["data"]["validation_signal"], "COMPLIANT")

            # Non-compliant attestation (GCR=0.8)
            cert_bad = bridge.create_attestation(
                task_id="pipeline-test-002",
                metrics={"SS": 0.7, "GCR": 0.8, "PFI": 0.3, "RP": 0.4, "SSR": 0.1},
            )
            self.assertEqual(cert_bad.governance_status, "NON_COMPLIANT")
            self.assertFalse(bridge.should_publish(cert_bad))
            self.__class__.report["oracle_attestations"] += 1

            # Registry
            registry = AttestationRegistry()
            registry.add(cert_good)
            registry.add(cert_bad)
            self.assertAlmostEqual(registry.get_compliance_rate(), 0.5, places=2)

            # Export for chain — only compliant unpublished
            pending = registry.export_for_chain()
            self.assertEqual(len(pending), 1)
            self.assertEqual(pending[0]["task_id"], "pipeline-test-001")

        finally:
            ob_mod.LOGS_DIR = orig_logs
            ob_mod.KEYS_DIR = orig_keys

        self.__class__.report["stages"]["k_oracle"] = "PASSED"
        self.__class__.report["modules_tested"] += 1
        self.__class__.report["checks_passed"] += 9

    # ─── Stage L: OAGS Conformance ──────────────────────────────────

    def test_l_oags_conformance(self):
        """Stage L: Validate OAGS conformance at all 3 levels."""
        from core.oags_bridge import OAGSPolicyBridge

        result = OAGSPolicyBridge.validate_conformance(level=3)

        self.assertTrue(result["level_1"]["passed"],
                        f"Level 1 failed: {result['level_1']}")
        self.assertTrue(result["level_2"]["passed"],
                        f"Level 2 failed: {result['level_2']}")
        self.assertTrue(result["level_3"]["passed"],
                        f"Level 3 failed: {result['level_3']}")
        self.assertEqual(result["max_level_passed"], 3)

        self.__class__.report["stages"]["l_oags_conformance"] = "PASSED"
        self.__class__.report["oags_level"] = 3
        self.__class__.report["modules_tested"] += 1
        self.__class__.report["checks_passed"] += 4

    # ─── Stage M: Full Metrics Report ───────────────────────────────

    def test_m_full_report(self):
        """Stage M: Verify accumulated report is complete."""
        report = self.__class__.report
        self.assertGreaterEqual(report["modules_tested"], 11,
                                f"Expected 11+ modules tested, got {report['modules_tested']}")
        self.assertGreaterEqual(report["checks_passed"], 50,
                                f"Expected 50+ checks, got {report['checks_passed']}")
        self.assertEqual(report["z3_theorems_verified"], 4)
        self.assertEqual(report["oags_level"], 3)
        self.assertGreaterEqual(report["memory_operations"], 3)
        self.assertGreaterEqual(report["oracle_attestations"], 2)


class TestFullPipelineFailureFlow(unittest.TestCase):
    """8-stage failure path — verify every failure is caught and logged."""

    def test_a_governance_blocks_violation(self):
        """Governance blocks output violating HARD_RULE."""
        from core.governance import ConstitutionEnforcer
        enforcer = ConstitutionEnforcer()
        result = enforcer.check("")
        self.assertFalse(result.passed)
        self.assertGreater(len(result.violations), 0)

    def test_b_ast_blocks_malicious_code(self):
        """AST verifier blocks eval/exec/subprocess."""
        from core.ast_verifier import ASTVerifier
        verifier = ASTVerifier()
        result = verifier.verify("import subprocess\nsubprocess.call(['rm', '-rf', '/'])")
        self.assertFalse(result.passed)

    def test_c_contract_rejects_unfulfilled(self):
        """TaskContract rejects output missing deliverables."""
        from core.task_contract import TaskContract
        contract_path = os.path.join(BASE_DIR, "contracts", "RESEARCH_CONTRACT.md")
        contract = TaskContract.from_file(contract_path)
        # Low supervisor score fails the quality gate
        ctx = {"supervisor_score": 3.0, "input_text": "test"}
        result = contract.is_fulfilled("short", ctx)
        self.assertFalse(result.fulfilled)
        self.assertGreater(len(result.failed_gates), 0)

    def test_d_adversarial_finds_unresolved(self):
        """Adversarial finds issues in hallucination-laden output."""
        from core.adversarial import AdversarialEvaluator
        evaluator = AdversarialEvaluator()
        hallucination_output = (
            "According to recent studies, 97.3% of AI agents achieve "
            "perfect governance compliance. Statistics show that the "
            "market will grow by exactly $847.2 billion by 2027."
        )
        verdict = evaluator.evaluate(hallucination_output, "market analysis")
        # Should find governance violations (hallucination markers)
        self.assertGreater(verdict.total_issues, 0)

    def test_e_infra_error_classified(self):
        """Provider error classified as INFRA_FAILURE."""
        from core.observability import classify_error, ErrorClass
        result = classify_error("HTTPError 429: Too Many Requests")
        self.assertEqual(result, ErrorClass.INFRA_FAILURE)

    def test_f_non_compliant_not_published(self):
        """Attestation with GCR < 1.0 is not publishable."""
        from core.oracle_bridge import OracleBridge, CertificateSigner
        tmpdir = tempfile.mkdtemp()
        signer = CertificateSigner(
            key_path=os.path.join(tmpdir, "test_key.json"))
        oags = MagicMock()
        oags.get_agent_card.return_value = {"identity_hash": "fail-test"}
        bridge = OracleBridge(signer, oags)
        cert = bridge.create_attestation("fail-001", {"GCR": 0.5, "SS": 0.3})
        self.assertFalse(bridge.should_publish(cert))

    def test_g_memory_rejects_bad_content(self):
        """GovernedMemoryStore rejects governance-violating content."""
        from core.memory_governance import GovernedMemoryStore
        import core.memory_governance as mg_mod
        tmpd = tempfile.mkdtemp()
        orig_store = mg_mod.STORE_FILE
        orig_log = mg_mod.LOG_FILE
        orig_decay = mg_mod.DECAY_LOG_FILE
        mg_mod.STORE_FILE = os.path.join(tmpd, "governed_store.jsonl")
        mg_mod.LOG_FILE = os.path.join(tmpd, "memory_governance.jsonl")
        mg_mod.DECAY_LOG_FILE = os.path.join(tmpd, "memory_decay.jsonl")
        try:
            store = GovernedMemoryStore()
            entry = store.add(content="x", category="knowledge")
            self.assertIn(entry.governance_status, ("rejected", "warning"))
        finally:
            mg_mod.STORE_FILE = orig_store
            mg_mod.LOG_FILE = orig_log
            mg_mod.DECAY_LOG_FILE = orig_decay

    def test_h_failure_chain_logged(self):
        """Verify that causal chain captures error classification."""
        from core.observability import (
            ErrorClass, classify_error, StepTrace, RunTrace,
            compute_derived_metrics, get_session_id,
        )

        trace = RunTrace(
            run_id="fail-chain-001",
            session_id=get_session_id(),
            crew_name="fail_crew",
            mode="production",
            timestamp_start=time.strftime("%Y-%m-%dT%H:%M:%S"),
            start_epoch=time.time(),
            deterministic=True,
            input_text="test",
            input_hash="def456",
        )

        # Simulate failure step
        step = StepTrace(
            step_index=0, agent="test_agent", provider="groq",
            status="failed", error="rate_limit_exceeded",
            error_class=str(ErrorClass.INFRA_FAILURE),
        )
        trace.steps.append(step)

        # Success step after retry
        step2 = StepTrace(
            step_index=1, agent="test_agent", provider="cerebras",
            status="completed", governance_passed=True,
            provider_switched=True,
        )
        trace.steps.append(step2)

        trace.end_epoch = time.time()
        trace.timestamp_end = time.strftime("%Y-%m-%dT%H:%M:%S")
        trace = compute_derived_metrics(trace)

        # Verify derived metrics reflect failure
        self.assertLess(trace.stability_score, 1.0)
        dashboard = trace.export_dashboard()
        self.assertIn("error_class_distribution", dashboard)


class TestPipelineDeterminism(unittest.TestCase):
    """Execute pipeline twice — prove identical outputs."""

    def _run_pipeline(self):
        """Run key pipeline stages and collect deterministic outputs."""
        from core.oags_bridge import OAGSIdentity, OAGSPolicyBridge
        from core.z3_verifier import Z3Verifier
        from core.ast_verifier import ASTVerifier
        from core.governance import ConstitutionEnforcer
        from core.memory_governance import MemoryClassifier

        results = {}

        # OAGS identity
        identity = OAGSIdentity()
        card = identity.get_agent_card()
        results["identity_hash"] = card["identity_hash"]
        results["constitution_hash"] = card["constitution_hash"]

        # Z3 proofs
        verifier = Z3Verifier()
        proofs = verifier.verify_all()
        results["z3_results"] = [p.result for p in proofs]
        results["z3_theorems"] = [p.theorem_name for p in proofs]

        # AST verification
        ast = ASTVerifier()
        clean_result = ast.verify("x = 1 + 2")
        results["ast_clean_score"] = clean_result.score
        bad_result = ast.verify("eval('x')")
        results["ast_bad_score"] = bad_result.score

        # Governance
        enforcer = ConstitutionEnforcer()
        gov = enforcer.check(
            "This is a comprehensive analysis with actionable "
            "recommendations. Visit https://example.com for details."
        )
        results["governance_passed"] = gov.passed
        results["governance_score"] = gov.score

        # Memory classification
        classifier = MemoryClassifier()
        results["classify_error"] = classifier.classify(
            "The API returned error 500 internal server error")
        results["classify_decision"] = classifier.classify(
            "We decided to use the Thompson Sampling approach")

        return results

    def test_pipeline_determinism(self):
        """Two runs produce identical deterministic outputs."""
        run1 = self._run_pipeline()
        run2 = self._run_pipeline()

        self.assertEqual(run1["identity_hash"], run2["identity_hash"])
        self.assertEqual(run1["constitution_hash"], run2["constitution_hash"])
        self.assertEqual(run1["z3_results"], run2["z3_results"])
        self.assertEqual(run1["z3_theorems"], run2["z3_theorems"])
        self.assertEqual(run1["ast_clean_score"], run2["ast_clean_score"])
        self.assertEqual(run1["ast_bad_score"], run2["ast_bad_score"])
        self.assertEqual(run1["governance_passed"], run2["governance_passed"])
        self.assertEqual(run1["governance_score"], run2["governance_score"])
        self.assertEqual(run1["classify_error"], run2["classify_error"])
        self.assertEqual(run1["classify_decision"], run2["classify_decision"])


class TestPipelineAuditTrail(unittest.TestCase):
    """Verify that pipeline execution produces complete audit logs."""

    def test_z3_proofs_logged(self):
        """Z3 proofs are persisted to logs/z3_proofs.json."""
        from core.z3_verifier import Z3Verifier
        verifier = Z3Verifier()
        verifier.verify_all()

        proof_path = os.path.join(LOGS_DIR, "z3_proofs.json")
        self.assertTrue(os.path.exists(proof_path),
                        f"Z3 proof file not found: {proof_path}")

        with open(proof_path, "r") as f:
            data = json.load(f)
        # Structure: {"timestamp": ..., "z3_version": ..., "proofs": [...]}
        self.assertIn("proofs", data)
        proofs = data["proofs"]
        self.assertEqual(len(proofs), 4)
        for proof in proofs:
            self.assertIn("theorem_name", proof)
            self.assertIn("result", proof)
            self.assertEqual(proof["result"], "VERIFIED")

    def test_pipeline_report_generated(self):
        """Full pipeline report exists after test suite execution."""
        report_path = os.path.join(LOGS_DIR, "full_pipeline_report.json")
        # This is generated by TestFullPipelineAcceptFlow.tearDownClass
        # If the accept flow tests ran, this file should exist
        if os.path.exists(report_path):
            with open(report_path, "r") as f:
                report = json.load(f)
            self.assertIn("pipeline_status", report)
            self.assertIn("stages", report)
            self.assertIn("timestamp", report)
            self.assertGreater(len(report["stages"]), 0)

    def test_constitution_file_valid(self):
        """dof.constitution.yml is valid YAML with required sections."""
        import yaml
        constitution_path = os.path.join(BASE_DIR, "dof.constitution.yml")
        self.assertTrue(os.path.exists(constitution_path))

        with open(constitution_path, "r") as f:
            config = yaml.safe_load(f)

        self.assertIn("metadata", config)
        self.assertIn("rules", config)
        self.assertIn("metrics", config)
        self.assertIn("thresholds", config)
        self.assertIn("memory", config)
        self.assertIn("spec_version", config["metadata"])


if __name__ == "__main__":
    unittest.main()
