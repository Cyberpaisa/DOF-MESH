"""Tests for TokenTracker in core/observability.py."""

import unittest
from collections import Counter

from core.observability import TokenTracker


class TestTokenTrackerLogCall(unittest.TestCase):
    """log_call records calls correctly."""

    def test_log_call_returns_dict(self):
        t = TokenTracker()
        call = t.log_call("groq", "llama-3.3-70b", 500, 200, 1200.0)
        self.assertIsInstance(call, dict)
        self.assertEqual(call["provider"], "groq")
        self.assertEqual(call["model"], "llama-3.3-70b")
        self.assertEqual(call["prompt_tokens"], 500)
        self.assertEqual(call["completion_tokens"], 200)
        self.assertEqual(call["total_tokens"], 700)
        self.assertEqual(call["latency_ms"], 1200.0)
        self.assertEqual(call["cost_estimate"], 0.0)
        self.assertIn("timestamp", call)

    def test_log_call_with_cost(self):
        t = TokenTracker()
        call = t.log_call("openai", "gpt-4", 1000, 500, 3000.0, 0.045)
        self.assertEqual(call["cost_estimate"], 0.045)

    def test_multiple_calls_accumulate(self):
        t = TokenTracker()
        t.log_call("groq", "llama-3.3-70b", 100, 50, 500.0)
        t.log_call("minimax", "m2.1", 200, 100, 800.0)
        self.assertEqual(len(t.calls), 2)


class TestTokenTrackerTotals(unittest.TestCase):
    """Aggregation methods compute correct totals."""

    def setUp(self):
        self.t = TokenTracker()
        self.t.log_call("groq", "llama-3.3-70b", 500, 200, 1200.0, 0.0)
        self.t.log_call("minimax", "m2.1", 300, 150, 800.0, 0.01)

    def test_total_tokens(self):
        self.assertEqual(self.t.total_tokens(), 1150)

    def test_total_prompt_tokens(self):
        self.assertEqual(self.t.total_prompt_tokens(), 800)

    def test_total_completion_tokens(self):
        self.assertEqual(self.t.total_completion_tokens(), 350)

    def test_total_cost(self):
        self.assertAlmostEqual(self.t.total_cost(), 0.01, places=6)

    def test_total_latency(self):
        self.assertEqual(self.t.total_latency_ms(), 2000.0)

    def test_avg_latency(self):
        self.assertEqual(self.t.avg_latency_ms(), 1000.0)


class TestTokenTrackerEmpty(unittest.TestCase):
    """Edge case: empty tracker."""

    def test_empty_totals(self):
        t = TokenTracker()
        self.assertEqual(t.total_tokens(), 0)
        self.assertEqual(t.total_cost(), 0.0)
        self.assertEqual(t.avg_latency_ms(), 0.0)
        self.assertEqual(t.calls_by_provider(), Counter())
        self.assertEqual(t.tokens_by_provider(), {})


class TestTokenTrackerByProvider(unittest.TestCase):
    """Per-provider breakdowns."""

    def setUp(self):
        self.t = TokenTracker()
        self.t.log_call("groq", "llama-3.3-70b", 500, 200, 1200.0)
        self.t.log_call("groq", "llama-3.3-70b", 300, 100, 600.0)
        self.t.log_call("minimax", "m2.1", 200, 150, 800.0)

    def test_calls_by_provider(self):
        counts = self.t.calls_by_provider()
        self.assertEqual(counts["groq"], 2)
        self.assertEqual(counts["minimax"], 1)

    def test_tokens_by_provider(self):
        tokens = self.t.tokens_by_provider()
        self.assertEqual(tokens["groq"], 1100)  # (500+200) + (300+100)
        self.assertEqual(tokens["minimax"], 350)  # 200+150


class TestTokenTrackerToDict(unittest.TestCase):
    """Serialization produces complete audit dict."""

    def test_to_dict_keys(self):
        t = TokenTracker()
        t.log_call("groq", "llama-3.3-70b", 100, 50, 500.0)
        d = t.to_dict()
        expected_keys = {
            "call_count", "total_tokens", "total_prompt_tokens",
            "total_completion_tokens", "total_cost", "total_latency_ms",
            "avg_latency_ms", "calls_by_provider", "tokens_by_provider", "calls",
        }
        self.assertEqual(set(d.keys()), expected_keys)
        self.assertEqual(d["call_count"], 1)
        self.assertEqual(d["total_tokens"], 150)


class TestTokenTrackerReset(unittest.TestCase):
    """reset() clears all state."""

    def test_reset(self):
        t = TokenTracker()
        t.log_call("groq", "llama-3.3-70b", 500, 200, 1200.0)
        self.assertEqual(len(t.calls), 1)
        t.reset()
        self.assertEqual(len(t.calls), 0)
        self.assertEqual(t.total_tokens(), 0)


class TestTokenTrackerImport(unittest.TestCase):
    """TokenTracker is importable from dof package."""

    def test_dof_import(self):
        from dof import TokenTracker as TT
        self.assertIs(TT, TokenTracker)


if __name__ == "__main__":
    unittest.main()
