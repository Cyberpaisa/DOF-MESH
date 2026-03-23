"""Tests for core/agentleak_benchmark.py — AgentLeakMapper, PrivacyLeakGenerator, metrics."""

import unittest

from core.agentleak_benchmark import (
    AgentLeakMapper,
    PrivacyBenchmarkResult,
    PrivacyLeakGenerator,
    _compute_privacy_result,
)


# ─────────────────────────────────────────────────────────────────────
# AgentLeakMapper
# ─────────────────────────────────────────────────────────────────────

class TestAgentLeakMapper(unittest.TestCase):

    def test_seven_channels(self):
        self.assertEqual(len(AgentLeakMapper.get_channels()), 7)

    def test_channel_names_are_strings(self):
        for ch in AgentLeakMapper.get_channels():
            self.assertIsInstance(ch, str)

    def test_known_channels_present(self):
        channels = AgentLeakMapper.get_channels()
        for expected in ("inter_agent_messages", "shared_memory", "tool_inputs",
                         "tool_outputs", "system_prompts", "context_windows",
                         "intermediate_reasoning"):
            self.assertIn(expected, channels)

    def test_get_component_known_channel(self):
        comp = AgentLeakMapper.get_component("tool_inputs")
        self.assertEqual(comp, "ASTVerifier")

    def test_get_component_unknown_returns_unknown(self):
        comp = AgentLeakMapper.get_component("nonexistent_channel")
        self.assertEqual(comp, "Unknown")

    def test_all_channels_have_components(self):
        for ch in AgentLeakMapper.get_channels():
            comp = AgentLeakMapper.get_component(ch)
            self.assertNotEqual(comp, "Unknown")

    def test_map_pii_to_channels(self):
        channels = AgentLeakMapper.map_category_to_channels("PII_LEAK")
        self.assertIsInstance(channels, list)
        self.assertGreater(len(channels), 0)

    def test_map_api_key_to_channels(self):
        channels = AgentLeakMapper.map_category_to_channels("API_KEY_LEAK")
        self.assertIn("tool_inputs", channels)

    def test_map_memory_to_channels(self):
        channels = AgentLeakMapper.map_category_to_channels("MEMORY_LEAK")
        self.assertIn("shared_memory", channels)

    def test_map_tool_input_to_channels(self):
        channels = AgentLeakMapper.map_category_to_channels("TOOL_INPUT_LEAK")
        self.assertIn("tool_inputs", channels)

    def test_map_unknown_category(self):
        channels = AgentLeakMapper.map_category_to_channels("UNKNOWN")
        self.assertEqual(channels, [])

    def test_channel_test_summary_returns_all_channels(self):
        summary = AgentLeakMapper.channel_test_summary()
        for ch in AgentLeakMapper.get_channels():
            self.assertIn(ch, summary)

    def test_channel_test_summary_lists_are_lists(self):
        summary = AgentLeakMapper.channel_test_summary()
        for val in summary.values():
            self.assertIsInstance(val, list)


# ─────────────────────────────────────────────────────────────────────
# _compute_privacy_result
# ─────────────────────────────────────────────────────────────────────

class TestComputePrivacyResult(unittest.TestCase):

    def test_perfect_detection(self):
        r = _compute_privacy_result("PII_LEAK", 10, 10, 0, 0, [1.0] * 20)
        self.assertAlmostEqual(r.f1, 1.0)
        self.assertAlmostEqual(r.dr, 1.0)
        self.assertAlmostEqual(r.fpr, 0.0)

    def test_zero_detection(self):
        r = _compute_privacy_result("API_KEY", 0, 10, 0, 10, [1.0] * 20)
        self.assertAlmostEqual(r.dr, 0.0)
        self.assertAlmostEqual(r.f1, 0.0)

    def test_all_fp(self):
        r = _compute_privacy_result("test", 0, 0, 10, 0, [1.0] * 10)
        self.assertAlmostEqual(r.precision, 0.0)

    def test_total_tests_correct(self):
        r = _compute_privacy_result("cat", 5, 5, 2, 3, [1.0] * 15)
        self.assertEqual(r.tests_total, 15)

    def test_latency_mean(self):
        r = _compute_privacy_result("cat", 1, 1, 0, 0, [10.0, 20.0, 30.0])
        self.assertAlmostEqual(r.latency_mean_ms, 20.0)

    def test_empty_latencies_no_crash(self):
        r = _compute_privacy_result("cat", 1, 1, 0, 0, [])
        self.assertGreaterEqual(r.latency_mean_ms, 0.0)

    def test_metrics_rounded_to_4dp(self):
        r = _compute_privacy_result("cat", 7, 3, 2, 1, [1.5] * 13)
        for attr in ("dr", "fpr", "precision", "recall", "f1"):
            val = getattr(r, attr)
            self.assertEqual(val, round(val, 4))

    def test_recall_equals_dr(self):
        r = _compute_privacy_result("cat", 8, 4, 2, 2, [1.0] * 16)
        self.assertAlmostEqual(r.recall, r.dr)

    def test_to_dict_has_all_fields(self):
        r = _compute_privacy_result("PII", 5, 5, 0, 0, [1.0] * 10)
        d = r.to_dict()
        for key in ("category", "tests_total", "true_positives", "true_negatives",
                     "false_positives", "false_negatives", "dr", "fpr",
                     "precision", "recall", "f1", "latency_mean_ms", "latency_p99_ms"):
            self.assertIn(key, d)


# ─────────────────────────────────────────────────────────────────────
# PrivacyBenchmarkResult dataclass
# ─────────────────────────────────────────────────────────────────────

class TestPrivacyBenchmarkResult(unittest.TestCase):

    def _make(self):
        return PrivacyBenchmarkResult(
            category="PII_LEAK", tests_total=50, true_positives=24,
            true_negatives=25, false_positives=1, false_negatives=0,
            dr=1.0, fpr=0.04, precision=0.96, recall=1.0, f1=0.98,
            latency_mean_ms=0.5, latency_p99_ms=1.2,
        )

    def test_fields_accessible(self):
        r = self._make()
        self.assertEqual(r.category, "PII_LEAK")
        self.assertEqual(r.tests_total, 50)

    def test_to_dict_type(self):
        self.assertIsInstance(self._make().to_dict(), dict)


# ─────────────────────────────────────────────────────────────────────
# PrivacyLeakGenerator — generate_pii_tests
# ─────────────────────────────────────────────────────────────────────

class TestPrivacyLeakGeneratorPII(unittest.TestCase):

    def setUp(self):
        self.gen = PrivacyLeakGenerator(seed=42)

    def test_count(self):
        self.assertEqual(len(self.gen.generate_pii_tests(50)), 50)

    def test_balanced(self):
        tests = self.gen.generate_pii_tests(50)
        leaks = sum(1 for t in tests if t["has_leak"])
        self.assertEqual(leaks, 25)

    def test_required_keys(self):
        for t in self.gen.generate_pii_tests(10):
            for key in ("text", "has_leak", "category", "channel"):
                self.assertIn(key, t)

    def test_category_label(self):
        for t in self.gen.generate_pii_tests(10):
            self.assertEqual(t["category"], "PII_LEAK")

    def test_deterministic(self):
        a = self.gen.generate_pii_tests(20)
        b = PrivacyLeakGenerator(seed=42).generate_pii_tests(20)
        self.assertEqual([t["text"] for t in a], [t["text"] for t in b])

    def test_different_seeds_differ(self):
        a = PrivacyLeakGenerator(seed=1).generate_pii_tests(20)
        b = PrivacyLeakGenerator(seed=99).generate_pii_tests(20)
        texts_a = [t["text"] for t in a]
        texts_b = [t["text"] for t in b]
        self.assertNotEqual(texts_a, texts_b)


# ─────────────────────────────────────────────────────────────────────
# PrivacyLeakGenerator — generate_api_key_tests
# ─────────────────────────────────────────────────────────────────────

class TestPrivacyLeakGeneratorAPIKey(unittest.TestCase):

    def setUp(self):
        self.gen = PrivacyLeakGenerator(seed=42)

    def test_count(self):
        self.assertEqual(len(self.gen.generate_api_key_tests(50)), 50)

    def test_balanced(self):
        tests = self.gen.generate_api_key_tests(50)
        leaks = sum(1 for t in tests if t["has_leak"])
        self.assertEqual(leaks, 25)

    def test_required_keys(self):
        for t in self.gen.generate_api_key_tests(10):
            for key in ("text", "has_leak", "category"):
                self.assertIn(key, t)

    def test_category_label(self):
        for t in self.gen.generate_api_key_tests(10):
            self.assertEqual(t["category"], "API_KEY_LEAK")

    def test_deterministic(self):
        a = self.gen.generate_api_key_tests(20)
        b = PrivacyLeakGenerator(seed=42).generate_api_key_tests(20)
        self.assertEqual([t["text"] for t in a], [t["text"] for t in b])


# ─────────────────────────────────────────────────────────────────────
# PrivacyLeakGenerator — generate_memory_leak_tests
# ─────────────────────────────────────────────────────────────────────

class TestPrivacyLeakGeneratorMemory(unittest.TestCase):

    def setUp(self):
        self.gen = PrivacyLeakGenerator(seed=42)

    def test_count(self):
        self.assertEqual(len(self.gen.generate_memory_leak_tests(50)), 50)

    def test_balanced(self):
        tests = self.gen.generate_memory_leak_tests(50)
        leaks = sum(1 for t in tests if t["has_leak"])
        self.assertEqual(leaks, 25)

    def test_category_label(self):
        for t in self.gen.generate_memory_leak_tests(10):
            self.assertEqual(t["category"], "MEMORY_LEAK")

    def test_deterministic(self):
        a = self.gen.generate_memory_leak_tests(20)
        b = PrivacyLeakGenerator(seed=42).generate_memory_leak_tests(20)
        self.assertEqual([t["text"] for t in a], [t["text"] for t in b])


# ─────────────────────────────────────────────────────────────────────
# PrivacyLeakGenerator — generate_tool_input_leak_tests
# ─────────────────────────────────────────────────────────────────────

class TestPrivacyLeakGeneratorToolInput(unittest.TestCase):

    def setUp(self):
        self.gen = PrivacyLeakGenerator(seed=42)

    def test_count(self):
        self.assertEqual(len(self.gen.generate_tool_input_leak_tests(50)), 50)

    def test_balanced(self):
        tests = self.gen.generate_tool_input_leak_tests(50)
        leaks = sum(1 for t in tests if t["has_leak"])
        self.assertEqual(leaks, 25)

    def test_category_label(self):
        for t in self.gen.generate_tool_input_leak_tests(10):
            self.assertEqual(t["category"], "TOOL_INPUT_LEAK")

    def test_deterministic(self):
        a = self.gen.generate_tool_input_leak_tests(20)
        b = PrivacyLeakGenerator(seed=42).generate_tool_input_leak_tests(20)
        self.assertEqual([t["text"] for t in a], [t["text"] for t in b])


if __name__ == "__main__":
    unittest.main()
