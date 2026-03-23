"""
Tests for core/l0_triage.py — Deterministic pre-LLM filtering layer.

All tests are deterministic, zero LLM calls, zero network.
Covers all 5 triage checks and the TriageDecision dataclass.
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.l0_triage import L0Triage, TriageDecision


# ── helpers ─────────────────────────────────────────────────────────

# A valid input that passes all checks by default
VALID_INPUT = "Analyze the formal Z3 invariants for DOF governance module."
PROVIDERS   = ["groq", "cerebras"]


def triage() -> L0Triage:
    return L0Triage()


# ─────────────────────────────────────────────────────────────────────
# TriageDecision dataclass
# ─────────────────────────────────────────────────────────────────────

class TestTriageDecision(unittest.TestCase):

    def test_has_required_fields(self):
        d = TriageDecision(
            proceed=True, reason="all_checks_passed",
            input_tokens_est=10, attempt=1, checks={}
        )
        for attr in ("proceed", "reason", "input_tokens_est", "attempt",
                     "checks", "timestamp"):
            self.assertTrue(hasattr(d, attr), f"Missing: {attr}")

    def test_timestamp_auto_set(self):
        import time
        before = time.time()
        d = TriageDecision(proceed=True, reason="x",
                           input_tokens_est=5, attempt=1, checks={})
        after = time.time()
        self.assertGreaterEqual(d.timestamp, before)
        self.assertLessEqual(d.timestamp, after)

    def test_proceed_bool(self):
        d = TriageDecision(proceed=False, reason="y",
                           input_tokens_est=0, attempt=0, checks={})
        self.assertIsInstance(d.proceed, bool)


# ─────────────────────────────────────────────────────────────────────
# Check 1 — input_too_short  (< MIN_INPUT_TOKENS tokens)
# ─────────────────────────────────────────────────────────────────────

class TestInputTooShort(unittest.TestCase):

    def setUp(self):
        self.t = triage()

    def test_empty_input_blocked(self):
        d = self.t.evaluate("", attempt=1)
        self.assertFalse(d.proceed)
        self.assertEqual(d.reason, "input_too_short")

    def test_single_char_blocked(self):
        d = self.t.evaluate("x", attempt=1)
        self.assertFalse(d.proceed)
        self.assertEqual(d.reason, "input_too_short")

    def test_exactly_min_tokens_passes(self):
        # MIN_INPUT_TOKENS = 3, token ≈ 4 chars  →  need ≥ 12 chars
        text = "a" * (L0Triage.MIN_INPUT_TOKENS * 4)
        d = self.t.evaluate(text, attempt=1)
        self.assertNotEqual(d.reason, "input_too_short")

    def test_short_input_has_correct_check_key(self):
        d = self.t.evaluate("hi", attempt=1)
        self.assertIn("input_length", d.checks)
        self.assertEqual(d.checks["input_length"], "FAIL")

    def test_input_tokens_estimated(self):
        text = "a" * 40
        d = self.t.evaluate(text, attempt=1)
        self.assertEqual(d.input_tokens_est, len(text) // 4)


# ─────────────────────────────────────────────────────────────────────
# Check 1b — input_too_long  (> MAX_INPUT_TOKENS tokens)
# ─────────────────────────────────────────────────────────────────────

class TestInputTooLong(unittest.TestCase):

    def setUp(self):
        self.t = triage()

    def test_overflow_blocked(self):
        # MAX_INPUT_TOKENS = 50000 tokens  →  > 200 000 chars
        huge = "word " * 50001 * 4
        d = self.t.evaluate(huge, attempt=1)
        self.assertFalse(d.proceed)
        self.assertEqual(d.reason, "input_too_long")

    def test_overflow_check_key(self):
        huge = "word " * 50001 * 4
        d = self.t.evaluate(huge, attempt=1)
        self.assertIn("input_length", d.checks)
        self.assertEqual(d.checks["input_length"], "FAIL_OVERFLOW")


# ─────────────────────────────────────────────────────────────────────
# Check 2 — retry_exhaustion  (attempt > MAX_RETRIES_BEFORE_SKIP)
# ─────────────────────────────────────────────────────────────────────

class TestRetryExhaustion(unittest.TestCase):

    def setUp(self):
        self.t = triage()

    def test_at_max_retries_still_proceeds(self):
        d = self.t.evaluate(VALID_INPUT, attempt=L0Triage.MAX_RETRIES_BEFORE_SKIP)
        self.assertNotEqual(d.reason, "retry_exhaustion")

    def test_one_over_max_blocked(self):
        d = self.t.evaluate(VALID_INPUT, attempt=L0Triage.MAX_RETRIES_BEFORE_SKIP + 1)
        self.assertFalse(d.proceed)
        self.assertEqual(d.reason, "retry_exhaustion")

    def test_high_attempt_blocked(self):
        d = self.t.evaluate(VALID_INPUT, attempt=100)
        self.assertFalse(d.proceed)
        self.assertEqual(d.reason, "retry_exhaustion")

    def test_retry_check_fail_key_present(self):
        d = self.t.evaluate(VALID_INPUT, attempt=99)
        self.assertIn("retry_exhaustion", d.checks)
        self.assertEqual(d.checks["retry_exhaustion"], "FAIL")


# ─────────────────────────────────────────────────────────────────────
# Check 3 — no_providers
# ─────────────────────────────────────────────────────────────────────

class TestProviderAvailability(unittest.TestCase):

    def setUp(self):
        self.t = triage()

    def test_empty_provider_list_blocked(self):
        d = self.t.evaluate(VALID_INPUT, attempt=1, active_providers=[])
        self.assertFalse(d.proceed)
        self.assertEqual(d.reason, "no_providers")

    def test_none_providers_not_blocked(self):
        # None means "not checking providers" — should not block
        d = self.t.evaluate(VALID_INPUT, attempt=1, active_providers=None)
        self.assertNotEqual(d.reason, "no_providers")

    def test_single_provider_sufficient(self):
        d = self.t.evaluate(VALID_INPUT, attempt=1, active_providers=["groq"])
        self.assertNotEqual(d.reason, "no_providers")

    def test_multiple_providers_passes(self):
        d = self.t.evaluate(VALID_INPUT, attempt=1, active_providers=PROVIDERS)
        self.assertNotEqual(d.reason, "no_providers")

    def test_no_providers_check_key(self):
        d = self.t.evaluate(VALID_INPUT, attempt=1, active_providers=[])
        self.assertIn("providers", d.checks)
        self.assertEqual(d.checks["providers"], "FAIL")


# ─────────────────────────────────────────────────────────────────────
# Check 4 — repeated_identical_errors
# ─────────────────────────────────────────────────────────────────────

class TestRepeatedErrors(unittest.TestCase):

    def setUp(self):
        self.t = triage()

    def test_three_same_errors_blocked(self):
        errors = ["RateLimitError", "RateLimitError", "RateLimitError"]
        d = self.t.evaluate(VALID_INPUT, attempt=1, prev_errors=errors)
        self.assertFalse(d.proceed)
        self.assertEqual(d.reason, "repeated_identical_errors")

    def test_two_same_errors_not_blocked(self):
        errors = ["RateLimitError", "RateLimitError"]
        d = self.t.evaluate(VALID_INPUT, attempt=1, prev_errors=errors)
        self.assertNotEqual(d.reason, "repeated_identical_errors")

    def test_three_different_errors_not_blocked(self):
        errors = ["ErrorA", "ErrorB", "ErrorC"]
        d = self.t.evaluate(VALID_INPUT, attempt=1, prev_errors=errors)
        self.assertNotEqual(d.reason, "repeated_identical_errors")

    def test_two_same_one_different_not_blocked(self):
        errors = ["ErrorA", "ErrorA", "ErrorB"]
        d = self.t.evaluate(VALID_INPUT, attempt=1, prev_errors=errors)
        self.assertNotEqual(d.reason, "repeated_identical_errors")

    def test_no_errors_passes(self):
        d = self.t.evaluate(VALID_INPUT, attempt=1, prev_errors=[])
        self.assertNotEqual(d.reason, "repeated_identical_errors")

    def test_none_errors_passes(self):
        d = self.t.evaluate(VALID_INPUT, attempt=1, prev_errors=None)
        self.assertNotEqual(d.reason, "repeated_identical_errors")

    def test_five_same_errors_blocked(self):
        errors = ["Timeout"] * 5
        d = self.t.evaluate(VALID_INPUT, attempt=1, prev_errors=errors)
        self.assertFalse(d.proceed)
        self.assertEqual(d.reason, "repeated_identical_errors")

    def test_repeated_error_check_key(self):
        errors = ["X", "X", "X"]
        d = self.t.evaluate(VALID_INPUT, attempt=1, prev_errors=errors)
        self.assertIn("repeated_errors", d.checks)
        self.assertEqual(d.checks["repeated_errors"], "FAIL")


# ─────────────────────────────────────────────────────────────────────
# Check 5 — empty_input (whitespace only)
# ─────────────────────────────────────────────────────────────────────

class TestEmptyInput(unittest.TestCase):

    def setUp(self):
        self.t = triage()

    def test_whitespace_only_blocked(self):
        # Use enough chars to pass length check, but all whitespace
        d = self.t.evaluate("   " * 20, attempt=1)
        self.assertFalse(d.proceed)
        self.assertEqual(d.reason, "empty_input")

    def test_tabs_and_newlines_blocked(self):
        d = self.t.evaluate("\t\n\r  " * 20, attempt=1)
        self.assertFalse(d.proceed)
        self.assertEqual(d.reason, "empty_input")

    def test_real_content_not_blocked(self):
        d = self.t.evaluate(VALID_INPUT, attempt=1)
        self.assertNotEqual(d.reason, "empty_input")


# ─────────────────────────────────────────────────────────────────────
# Happy path — all checks passed
# ─────────────────────────────────────────────────────────────────────

class TestAllChecksPassed(unittest.TestCase):

    def setUp(self):
        self.t = triage()

    def test_valid_input_proceeds(self):
        d = self.t.evaluate(VALID_INPUT, attempt=1,
                            active_providers=PROVIDERS, prev_errors=[])
        self.assertTrue(d.proceed)
        self.assertEqual(d.reason, "all_checks_passed")

    def test_all_check_keys_present_on_pass(self):
        d = self.t.evaluate(VALID_INPUT, attempt=1,
                            active_providers=PROVIDERS, prev_errors=[])
        for key in ("input_length", "retry_exhaustion", "providers",
                    "repeated_errors", "input_quality"):
            self.assertIn(key, d.checks, f"Missing check key: {key}")

    def test_all_checks_are_pass_on_success(self):
        d = self.t.evaluate(VALID_INPUT, attempt=1,
                            active_providers=PROVIDERS, prev_errors=[])
        for key, val in d.checks.items():
            self.assertEqual(val, "PASS", f"Check {key!r} not PASS: {val!r}")

    def test_attempt_preserved_in_decision(self):
        d = self.t.evaluate(VALID_INPUT, attempt=3)
        self.assertEqual(d.attempt, 3)

    def test_returns_triage_decision(self):
        d = self.t.evaluate(VALID_INPUT, attempt=1)
        self.assertIsInstance(d, TriageDecision)

    def test_first_attempt_passes(self):
        d = self.t.evaluate(VALID_INPUT, attempt=1)
        self.assertTrue(d.proceed)


# ─────────────────────────────────────────────────────────────────────
# get_stats() — smoke test (reads actual log, values may vary)
# ─────────────────────────────────────────────────────────────────────

class TestGetStats(unittest.TestCase):

    def test_returns_dict_with_required_keys(self):
        t = triage()
        # Trigger one decision to ensure the log file exists
        t.evaluate(VALID_INPUT, attempt=1)
        stats = t.get_stats()
        for key in ("total", "proceeded", "skipped", "skip_rate", "skip_reasons"):
            self.assertIn(key, stats, f"Missing stats key: {key}")

    def test_total_is_int(self):
        t = triage()
        t.evaluate(VALID_INPUT, attempt=1)
        stats = t.get_stats()
        self.assertIsInstance(stats["total"], int)

    def test_skip_rate_in_unit_range(self):
        t = triage()
        t.evaluate(VALID_INPUT, attempt=1)
        stats = t.get_stats()
        self.assertGreaterEqual(stats["skip_rate"], 0.0)
        self.assertLessEqual(stats["skip_rate"], 1.0)

    def test_proceeded_plus_skipped_equals_total(self):
        t = triage()
        t.evaluate(VALID_INPUT, attempt=1)
        stats = t.get_stats()
        self.assertEqual(stats["proceeded"] + stats["skipped"], stats["total"])

    def test_skip_reasons_is_dict(self):
        t = triage()
        t.evaluate(VALID_INPUT, attempt=1)
        stats = t.get_stats()
        self.assertIsInstance(stats["skip_reasons"], dict)


class TestGetStatsIsolated(unittest.TestCase):
    """Isolated get_stats() tests using a temp log file."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.log_path = os.path.join(self.tmp.name, "metrics", "l0_triage.jsonl")
        os.makedirs(os.path.dirname(self.log_path))
        self.addCleanup(self.tmp.cleanup)

    def _triage(self):
        with patch("core.l0_triage.TRIAGE_LOG", self.log_path):
            return L0Triage()

    def _write(self, rows):
        with open(self.log_path, "w") as f:
            for row in rows:
                f.write(json.dumps(row) + "\n")

    def test_missing_log_returns_zeros(self):
        os.remove(self.log_path) if os.path.exists(self.log_path) else None
        with patch("core.l0_triage.TRIAGE_LOG", self.log_path):
            stats = L0Triage().get_stats()
        self.assertEqual(stats["total"], 0)
        self.assertEqual(stats["skip_reasons"], {})

    def test_skip_reasons_counted_per_reason(self):
        self._write([
            {"proceed": False, "reason": "input_too_short"},
            {"proceed": False, "reason": "input_too_short"},
            {"proceed": False, "reason": "retry_exhaustion"},
            {"proceed": True,  "reason": "all_checks_passed"},
        ])
        with patch("core.l0_triage.TRIAGE_LOG", self.log_path):
            stats = L0Triage().get_stats()
        self.assertEqual(stats["total"], 4)
        self.assertEqual(stats["skip_reasons"]["input_too_short"], 2)
        self.assertEqual(stats["skip_reasons"]["retry_exhaustion"], 1)
        self.assertNotIn("all_checks_passed", stats["skip_reasons"])

    def test_corrupt_lines_skipped_gracefully(self):
        with open(self.log_path, "w") as f:
            f.write(json.dumps({"proceed": True, "reason": "all_checks_passed"}) + "\n")
            f.write("NOT_VALID_JSON\n")
            f.write(json.dumps({"proceed": False, "reason": "no_providers"}) + "\n")
        with patch("core.l0_triage.TRIAGE_LOG", self.log_path):
            stats = L0Triage().get_stats()
        # 2 valid lines; 1 corrupt skipped without crashing
        self.assertEqual(stats["total"], 2)
        self.assertEqual(stats["skipped"], 1)

    def test_blank_lines_ignored(self):
        with open(self.log_path, "w") as f:
            f.write("\n   \n")
            f.write(json.dumps({"proceed": True, "reason": "all_checks_passed"}) + "\n")
        with patch("core.l0_triage.TRIAGE_LOG", self.log_path):
            stats = L0Triage().get_stats()
        self.assertEqual(stats["total"], 1)


if __name__ == "__main__":
    unittest.main()
