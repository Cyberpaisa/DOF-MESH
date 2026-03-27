"""Tests for Smart LLM Router — task_type routing, circuit breaker, analytics."""

import os
import sys
import time
import types
import unittest
from unittest.mock import MagicMock, patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# ─────────────────────────────────────────────────────────────────────
# Pre-import: mock 'crewai' if not installed so llm_config can load
# ─────────────────────────────────────────────────────────────────────
if "crewai" not in sys.modules:
    _crewai_mock = types.ModuleType("crewai")
    _crewai_mock.LLM = MagicMock  # placeholder; overridden by class-level @patch
    sys.modules["crewai"] = _crewai_mock

# Force re-import of llm_config with the mock in place
if "llm_config" in sys.modules:
    del sys.modules["llm_config"]


# ─────────────────────────────────────────────────────────────────────
# Helper: mock all API keys so provider getters return LLM objects
# ─────────────────────────────────────────────────────────────────────

_MOCK_KEYS = {
    "GROQ_API_KEY": "test-groq-key",
    "NVIDIA_API_KEY": "test-nvidia-key",
    "NVIDIA_NIM_API_KEY": "test-nvidia-key",
    "CEREBRAS_API_KEY": "test-cerebras-key",
    "MINIMAX_API_KEY": "test-minimax-key",
    "ZHIPU_API_KEY": "test-zhipu-key",
    "GEMINI_API_KEY": "test-gemini-key",
    "SAMBANOVA_API_KEY": "test-sambanova-key",
    "OPENROUTER_API_KEY": "test-openrouter-key",
}


def _get_env(key, default=None):
    return _MOCK_KEYS.get(key, default)


class _FakeLLM:
    """Lightweight stand-in for crewai.LLM used to capture which model was selected."""
    def __init__(self, **kwargs):
        self.model = kwargs.get("model", "unknown")
        self.kwargs = kwargs


@patch("llm_config.LLM", _FakeLLM)
@patch("os.getenv", side_effect=_get_env)
class TestGetLLMSmartTaskType(unittest.TestCase):
    """Test that explicit task_type routes to the correct provider/model."""

    def setUp(self):
        import llm_config
        llm_config._exhausted_providers.clear()
        llm_config._circuit_breaker.clear()
        llm_config._routing_log.clear()

    def test_architecture_task_type(self, mock_env):
        from llm_config import get_llm_smart
        llm = get_llm_smart("verifier", task_type="architecture")
        self.assertIn("kimi-k2.5", llm.model)

    def test_research_task_type(self, mock_env):
        from llm_config import get_llm_smart
        llm = get_llm_smart("verifier", task_type="research")
        self.assertIn("deepseek", llm.model)

    def test_verification_task_type(self, mock_env):
        from llm_config import get_llm_smart
        llm = get_llm_smart("verifier", task_type="verification")
        self.assertIn("MiniMax", llm.model)

    def test_fast_task_type(self, mock_env):
        from llm_config import get_llm_smart
        llm = get_llm_smart("verifier", task_type="fast")
        self.assertIn("glm-4.7", llm.model)

    def test_fallback_task_type(self, mock_env):
        from llm_config import get_llm_smart
        llm = get_llm_smart("verifier", task_type="fallback")
        self.assertIn("groq", llm.model.lower()) or self.assertIn("llama", llm.model.lower())

    def test_large_context_routes_gemini(self, mock_env):
        from llm_config import get_llm_smart
        llm = get_llm_smart("verifier", context_size=60_000)
        self.assertIn("gemini", llm.model)

    def test_default_uses_role_chain(self, mock_env):
        from llm_config import get_llm_smart
        # With small context and no task_type, should fall through to cerebras or role chain
        llm = get_llm_smart("verifier", task_text="hello", context_size=100)
        self.assertIsNotNone(llm)

    def test_routing_log_populated(self, mock_env):
        from llm_config import get_llm_smart, get_routing_log
        get_llm_smart("verifier", task_type="fast")
        log = get_routing_log()
        self.assertGreater(len(log), 0)
        self.assertEqual(log[-1]["task_type"], "fast")
        self.assertIn("zhipu", log[-1]["chosen_provider"])


@patch("llm_config.LLM", _FakeLLM)
@patch("os.getenv", side_effect=_get_env)
class TestCircuitBreaker(unittest.TestCase):
    """Circuit breaker: 3 failures in 5 minutes → provider degraded."""

    def setUp(self):
        import llm_config
        llm_config._exhausted_providers.clear()
        llm_config._circuit_breaker.clear()
        llm_config._routing_log.clear()

    def test_circuit_breaker_degrades_provider(self, mock_env):
        from llm_config import record_provider_failure, is_provider_degraded
        # Less than threshold — not degraded
        record_provider_failure("nvidia")
        record_provider_failure("nvidia")
        self.assertFalse(is_provider_degraded("nvidia"))

        # Third failure triggers degradation
        record_provider_failure("nvidia")
        self.assertTrue(is_provider_degraded("nvidia"))

    def test_circuit_breaker_does_not_affect_other_providers(self, mock_env):
        from llm_config import record_provider_failure, is_provider_degraded
        for _ in range(3):
            record_provider_failure("nvidia")
        self.assertTrue(is_provider_degraded("nvidia"))
        self.assertFalse(is_provider_degraded("groq"))

    def test_degraded_provider_skipped_in_routing(self, mock_env):
        from llm_config import get_llm_smart, record_provider_failure
        # Degrade nvidia
        for _ in range(3):
            record_provider_failure("nvidia")
        # architecture would normally go to nvidia — should fallback
        llm = get_llm_smart("verifier", task_type="architecture")
        # Should still return something (fallback chain)
        self.assertIsNotNone(llm)


@patch("llm_config.LLM", _FakeLLM)
@patch("os.getenv", side_effect=_get_env)
class TestRoutingStats(unittest.TestCase):
    """get_routing_stats() returns distribution and failure rates."""

    def setUp(self):
        import llm_config
        llm_config._exhausted_providers.clear()
        llm_config._circuit_breaker.clear()
        llm_config._routing_log.clear()

    def test_empty_stats(self, mock_env):
        from llm_config import get_routing_stats
        stats = get_routing_stats()
        self.assertEqual(stats["total_decisions"], 0)

    def test_stats_after_routing(self, mock_env):
        from llm_config import get_llm_smart, get_routing_stats
        get_llm_smart("verifier", task_type="fast")
        get_llm_smart("verifier", task_type="fast")
        get_llm_smart("verifier", task_type="verification")
        stats = get_routing_stats()
        self.assertEqual(stats["total_decisions"], 3)
        self.assertIn("zhipu", stats["provider_distribution"])


if __name__ == "__main__":
    unittest.main()
