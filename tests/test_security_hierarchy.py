"""
Tests for core/security_hierarchy.py — L0→L4 security verification pipeline.

All tests are deterministic, zero LLM, zero network.
Uses real sub-modules (L0Triage, ConstitutionEnforcer, ASTVerifier) — no mocking.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.security_hierarchy import (
    HierarchyResult,
    LayerResult,
    SecurityHierarchy,
    verify_full,
)

# ── Fixtures ─────────────────────────────────────────────────────────

# Long enough to pass L0 (>3 tokens ≈ >12 chars), clean enough for L1
CLEAN_INPUT  = "Analyze the security properties of the DOF governance module."
CLEAN_OUTPUT = (
    "The DOF governance module enforces constitutional constraints deterministically. "
    "All hard rules are checked before any agent output is accepted. "
    "Violations are logged with full audit trails for compliance review."
)

# Code containing eval() — triggers L2 and should fail it.
# Must be long enough to pass L1 governance (English text present).
CODE_WITH_EVAL = (
    "The following script evaluates the user input directly. "
    "This is a common pattern in some codebases.\n\n"
    "```python\nresult = eval(user_input)\nprint(result)\n```\n\n"
    "Please review this approach carefully before deploying."
)


# ─────────────────────────────────────────────────────────────────────
# LayerResult dataclass
# ─────────────────────────────────────────────────────────────────────

class TestLayerResult(unittest.TestCase):

    def test_fields_set(self):
        r = LayerResult(layer="L0", passed=True, reason="ok")
        self.assertEqual(r.layer, "L0")
        self.assertTrue(r.passed)
        self.assertEqual(r.reason, "ok")

    def test_score_default_one(self):
        r = LayerResult(layer="L1", passed=True, reason="x")
        self.assertAlmostEqual(r.score, 1.0)

    def test_details_default_empty(self):
        r = LayerResult(layer="L2", passed=False, reason="y")
        self.assertIsInstance(r.details, dict)

    def test_time_ms_default_zero(self):
        r = LayerResult(layer="L3", passed=True, reason="z")
        self.assertEqual(r.time_ms, 0.0)


# ─────────────────────────────────────────────────────────────────────
# HierarchyResult dataclass
# ─────────────────────────────────────────────────────────────────────

class TestHierarchyResult(unittest.TestCase):

    def test_fields_set(self):
        r = HierarchyResult(passed=True, failed_at="NONE")
        self.assertTrue(r.passed)
        self.assertEqual(r.failed_at, "NONE")

    def test_layers_default_empty(self):
        r = HierarchyResult(passed=True, failed_at="NONE")
        self.assertIsInstance(r.layers, list)

    def test_timestamp_set(self):
        import time
        before = time.time()
        r = HierarchyResult(passed=True, failed_at="NONE")
        self.assertGreaterEqual(r.timestamp, before)


# ─────────────────────────────────────────────────────────────────────
# _looks_like_code()
# ─────────────────────────────────────────────────────────────────────

class TestLooksLikeCode(unittest.TestCase):

    def setUp(self):
        self.h = SecurityHierarchy()

    def test_python_def(self):
        self.assertTrue(self.h._looks_like_code("def my_func():"))

    def test_import_statement(self):
        self.assertTrue(self.h._looks_like_code("import os"))

    def test_eval_call(self):
        self.assertTrue(self.h._looks_like_code("x = eval(user_input)"))

    def test_exec_call(self):
        self.assertTrue(self.h._looks_like_code("exec(malicious_code)"))

    def test_code_fence(self):
        self.assertTrue(self.h._looks_like_code("```python\nprint('hi')\n```"))

    def test_class_keyword(self):
        self.assertTrue(self.h._looks_like_code("class MyClass:"))

    def test_javascript_function(self):
        self.assertTrue(self.h._looks_like_code("function foo() { return 1; }"))

    def test_plain_text_is_not_code(self):
        self.assertFalse(self.h._looks_like_code(
            "The governance module enforces constitutional constraints."
        ))

    def test_empty_string(self):
        self.assertFalse(self.h._looks_like_code(""))


# ─────────────────────────────────────────────────────────────────────
# verify() — return type and structure
# ─────────────────────────────────────────────────────────────────────

class TestVerifyStructure(unittest.TestCase):

    def setUp(self):
        self.h = SecurityHierarchy()

    def test_returns_hierarchy_result(self):
        r = self.h.verify(CLEAN_INPUT, CLEAN_OUTPUT)
        self.assertIsInstance(r, HierarchyResult)

    def test_has_five_layers(self):
        r = self.h.verify(CLEAN_INPUT, CLEAN_OUTPUT)
        self.assertEqual(len(r.layers), 5)

    def test_layer_names_in_order(self):
        r = self.h.verify(CLEAN_INPUT, CLEAN_OUTPUT)
        names = [l.layer for l in r.layers]
        self.assertEqual(names, ["L0", "L1", "L2", "L3", "L4"])

    def test_proof_hash_non_empty(self):
        r = self.h.verify(CLEAN_INPUT, CLEAN_OUTPUT)
        self.assertIsInstance(r.proof_hash, str)
        self.assertGreater(len(r.proof_hash), 0)

    def test_proof_hash_is_hex(self):
        r = self.h.verify(CLEAN_INPUT, CLEAN_OUTPUT)
        self.assertTrue(all(c in "0123456789abcdef" for c in r.proof_hash))

    def test_total_time_positive(self):
        r = self.h.verify(CLEAN_INPUT, CLEAN_OUTPUT)
        self.assertGreater(r.total_time_ms, 0)

    def test_proof_hash_deterministic(self):
        """Same layer results must yield the same proof hash."""
        r1 = self.h.verify(CLEAN_INPUT, CLEAN_OUTPUT)
        r2 = self.h.verify(CLEAN_INPUT, CLEAN_OUTPUT)
        self.assertEqual(r1.proof_hash, r2.proof_hash)


# ─────────────────────────────────────────────────────────────────────
# verify() — happy path (clean input/output)
# ─────────────────────────────────────────────────────────────────────

class TestVerifyHappyPath(unittest.TestCase):

    def setUp(self):
        self.h = SecurityHierarchy()
        self.result = self.h.verify(CLEAN_INPUT, CLEAN_OUTPUT, attempt=1)

    def test_overall_passed(self):
        self.assertTrue(self.result.passed)

    def test_failed_at_none(self):
        self.assertEqual(self.result.failed_at, "NONE")

    def test_l0_passed(self):
        l0 = next(l for l in self.result.layers if l.layer == "L0")
        self.assertTrue(l0.passed)

    def test_l3_never_blocks(self):
        l3 = next(l for l in self.result.layers if l.layer == "L3")
        # L3 is scoring only — must always pass regardless of score
        self.assertTrue(l3.passed)

    def test_layer_scores_in_range(self):
        for l in self.result.layers:
            self.assertGreaterEqual(l.score, 0.0, f"{l.layer} score < 0")
            self.assertLessEqual(l.score, 1.0, f"{l.layer} score > 1")


# ─────────────────────────────────────────────────────────────────────
# verify() — L0 short-circuit (bad input)
# ─────────────────────────────────────────────────────────────────────

class TestVerifyL0Block(unittest.TestCase):

    def setUp(self):
        self.h = SecurityHierarchy()

    def test_too_short_input_fails_at_l0(self):
        r = self.h.verify("hi", CLEAN_OUTPUT, attempt=1)
        self.assertFalse(r.passed)
        self.assertEqual(r.failed_at, "L0")

    def test_only_l0_layer_returned_on_short_circuit(self):
        r = self.h.verify("hi", CLEAN_OUTPUT, attempt=1)
        # Should stop at L0 — only 1 layer recorded
        self.assertEqual(len(r.layers), 1)
        self.assertEqual(r.layers[0].layer, "L0")

    def test_retry_exhaustion_fails_at_l0(self):
        from core.l0_triage import L0Triage
        r = self.h.verify(CLEAN_INPUT, CLEAN_OUTPUT,
                          attempt=L0Triage.MAX_RETRIES_BEFORE_SKIP + 1)
        self.assertFalse(r.passed)
        self.assertEqual(r.failed_at, "L0")

    def test_no_providers_fails_at_l0(self):
        r = self.h.verify(CLEAN_INPUT, CLEAN_OUTPUT,
                          attempt=1, active_providers=[])
        self.assertFalse(r.passed)
        self.assertEqual(r.failed_at, "L0")


# ─────────────────────────────────────────────────────────────────────
# verify() — L2 code gate
# ─────────────────────────────────────────────────────────────────────

class TestVerifyL2(unittest.TestCase):

    def setUp(self):
        self.h = SecurityHierarchy()

    def test_l2_skipped_for_plain_text(self):
        r = self.h.verify(CLEAN_INPUT, CLEAN_OUTPUT)
        l2 = next(l for l in r.layers if l.layer == "L2")
        self.assertEqual(l2.reason, "skipped_no_code")

    def test_l2_runs_when_contains_code_true(self):
        # Use a code output that is long enough to pass L1 governance checks
        code_output = (
            "The following helper function processes the input value safely. "
            "It applies a simple transformation and returns the result.\n\n"
            "def foo(): pass\n\n"
            "This implementation is straightforward and has no side effects."
        )
        r = self.h.verify(CLEAN_INPUT, code_output, contains_code=True)
        l2 = next(l for l in r.layers if l.layer == "L2")
        self.assertNotEqual(l2.reason, "skipped_no_code")

    def test_l2_runs_when_code_detected(self):
        # _looks_like_code detects "def " → L2 runs automatically
        code_output = (
            "The process function below multiplies the input by two. "
            "It is deterministic and has no external dependencies.\n\n"
            "def process(x):\n    return x * 2\n\n"
            "This is safe for use in production environments."
        )
        r = self.h.verify(CLEAN_INPUT, code_output)
        l2 = next(l for l in r.layers if l.layer == "L2")
        self.assertNotEqual(l2.reason, "skipped_no_code")

    def test_eval_in_output_blocked(self):
        # eval() is caught by the pipeline — either at L1 (ConstitutionEnforcer
        # runs AST checks inline) or L2 (ASTVerifier). Either way the pipeline
        # must block and not pass.
        r = self.h.verify(CLEAN_INPUT, CODE_WITH_EVAL, contains_code=True)
        self.assertFalse(r.passed)
        self.assertIn(r.failed_at, ("L1", "L2"))


# ─────────────────────────────────────────────────────────────────────
# report()
# ─────────────────────────────────────────────────────────────────────

class TestReport(unittest.TestCase):

    def setUp(self):
        self.h = SecurityHierarchy()

    def test_report_is_string(self):
        r = self.h.verify(CLEAN_INPUT, CLEAN_OUTPUT)
        self.assertIsInstance(self.h.report(r), str)

    def test_report_pass_on_clean(self):
        r = self.h.verify(CLEAN_INPUT, CLEAN_OUTPUT)
        self.assertIn("PASS", self.h.report(r))

    def test_report_fail_on_bad_input(self):
        r = self.h.verify("hi", CLEAN_OUTPUT)
        report = self.h.report(r)
        self.assertIn("FAIL", report)
        self.assertIn("L0", report)

    def test_report_contains_proof_hash(self):
        r = self.h.verify(CLEAN_INPUT, CLEAN_OUTPUT)
        report = self.h.report(r)
        self.assertIn("Proof hash", report)
        self.assertIn(r.proof_hash[:16], report)

    def test_report_shows_all_layer_names(self):
        r = self.h.verify(CLEAN_INPUT, CLEAN_OUTPUT)
        report = self.h.report(r)
        for layer in ("L0", "L1", "L2", "L3", "L4"):
            self.assertIn(layer, report)


# ─────────────────────────────────────────────────────────────────────
# verify_full() convenience function
# ─────────────────────────────────────────────────────────────────────

class TestVerifyFull(unittest.TestCase):

    def test_returns_hierarchy_result(self):
        r = verify_full(CLEAN_INPUT, CLEAN_OUTPUT)
        self.assertIsInstance(r, HierarchyResult)

    def test_clean_text_passes(self):
        r = verify_full(CLEAN_INPUT, CLEAN_OUTPUT)
        self.assertTrue(r.passed)

    def test_kwargs_forwarded(self):
        r = verify_full(CLEAN_INPUT, CLEAN_OUTPUT,
                        attempt=1, active_providers=["groq"])
        self.assertIsInstance(r, HierarchyResult)


if __name__ == "__main__":
    unittest.main()
