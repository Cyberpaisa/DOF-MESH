"""Tests for TokenTracker in core/observability.py."""

import unittest

from core.observability import TokenTracker


class TestLogCallAddsEntry(unittest.TestCase):
    """log_call adds entry to calls list."""

    def test_log_call_adds_entry(self):
        t = TokenTracker()
        t.log_call("groq", "llama-3.3-70b", 500, 200, 1200.0, 0.0)
        self.assertEqual(len(t.calls), 1)
        entry = t.calls[0]
        self.assertEqual(entry["provider"], "groq")
        self.assertEqual(entry["model"], "llama-3.3-70b")
        self.assertEqual(entry["prompt_tokens"], 500)
        self.assertEqual(entry["completion_tokens"], 200)
        self.assertEqual(entry["total_tokens"], 700)
        self.assertEqual(entry["latency_ms"], 1200.0)
        self.assertEqual(entry["cost_estimate"], 0.0)
        self.assertIn("timestamp", entry)


class TestTotalTokens(unittest.TestCase):
    """total_tokens sums correctly."""

    def test_total_tokens(self):
        t = TokenTracker()
        t.log_call("groq", "llama-3.3-70b", 500, 200, 1200.0, 0.0)
        t.log_call("minimax", "m2.1", 300, 150, 800.0, 0.0)
        self.assertEqual(t.total_tokens(), 1150)


class TestTotalCost(unittest.TestCase):
    """total_cost sums correctly."""

    def test_total_cost(self):
        t = TokenTracker()
        t.log_call("groq", "llama-3.3-70b", 500, 200, 1200.0, 0.01)
        t.log_call("minimax", "m2.1", 300, 150, 800.0, 0.02)
        self.assertAlmostEqual(t.total_cost(), 0.03, places=6)


class TestCallsByProvider(unittest.TestCase):
    """calls_by_provider counts per provider."""

    def test_calls_by_provider(self):
        t = TokenTracker()
        t.log_call("groq", "llama-3.3-70b", 500, 200, 1200.0, 0.0)
        t.log_call("groq", "llama-3.3-70b", 300, 100, 600.0, 0.0)
        t.log_call("minimax", "m2.1", 200, 150, 800.0, 0.0)
        result = t.calls_by_provider()
        self.assertIsInstance(result, dict)
        self.assertEqual(result["groq"], 2)
        self.assertEqual(result["minimax"], 1)


class TestAverageLatency(unittest.TestCase):
    """average_latency calculates mean."""

    def test_average_latency(self):
        t = TokenTracker()
        t.log_call("groq", "llama-3.3-70b", 500, 200, 1200.0, 0.0)
        t.log_call("minimax", "m2.1", 300, 150, 800.0, 0.0)
        self.assertEqual(t.average_latency(), 1000.0)


class TestToDict(unittest.TestCase):
    """to_dict serializes everything."""

    def test_to_dict(self):
        t = TokenTracker()
        t.log_call("groq", "llama-3.3-70b", 100, 50, 500.0, 0.005)
        d = t.to_dict()
        expected_keys = {"calls", "total_tokens", "total_cost",
                         "total_calls", "calls_by_provider", "average_latency_ms"}
        self.assertEqual(set(d.keys()), expected_keys)
        self.assertEqual(d["total_calls"], 1)
        self.assertEqual(d["total_tokens"], 150)
        self.assertAlmostEqual(d["total_cost"], 0.005)
        self.assertEqual(d["calls_by_provider"], {"groq": 1})
        self.assertEqual(d["average_latency_ms"], 500.0)
        self.assertEqual(len(d["calls"]), 1)


class TestReset(unittest.TestCase):
    """reset clears history."""

    def test_reset(self):
        t = TokenTracker()
        t.log_call("groq", "llama-3.3-70b", 500, 200, 1200.0, 0.0)
        self.assertEqual(len(t.calls), 1)
        t.reset()
        self.assertEqual(len(t.calls), 0)
        self.assertEqual(t.total_tokens(), 0)


class TestEmptyTracker(unittest.TestCase):
    """Empty tracker returns zeros."""

    def test_empty_tracker(self):
        t = TokenTracker()
        self.assertEqual(t.total_tokens(), 0)
        self.assertEqual(t.total_cost(), 0)
        self.assertEqual(t.average_latency(), 0)
        self.assertEqual(t.calls_by_provider(), {})
        d = t.to_dict()
        self.assertEqual(d["total_calls"], 0)


if __name__ == "__main__":
    unittest.main()
