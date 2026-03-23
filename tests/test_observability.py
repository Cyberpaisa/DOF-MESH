"""Tests for core/observability.py — TokenTracker, classify_error, estimate_tokens,
compute_derived_metrics, StepTrace, RunTrace, export_dashboard."""

import time
import unittest

from core.observability import (
    ErrorClass, RunTrace, StepTrace, TokenTracker,
    classify_error, compute_derived_metrics, estimate_tokens,
)


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


class TestClassifyError(unittest.TestCase):

    def test_governance_via_context(self):
        self.assertEqual(classify_error("err", {"governance_violations": ["X"]}), ErrorClass.GOVERNANCE_FAILURE)

    def test_governance_via_message(self):
        self.assertEqual(classify_error("governance check blocked"), ErrorClass.GOVERNANCE_FAILURE)

    def test_infra_rate_limit(self):
        self.assertEqual(classify_error("429 rate_limit exceeded"), ErrorClass.INFRA_FAILURE)

    def test_infra_timeout(self):
        self.assertEqual(classify_error("connection timed out"), ErrorClass.INFRA_FAILURE)

    def test_provider_auth(self):
        self.assertEqual(classify_error("invalid api_key provided"), ErrorClass.PROVIDER_FAILURE)

    def test_llm_token_limit(self):
        self.assertEqual(classify_error("max_tokens exceeded"), ErrorClass.LLM_FAILURE)

    def test_model_parse_error(self):
        self.assertEqual(classify_error("pydantic validation error"), ErrorClass.MODEL_FAILURE)

    def test_memory_chromadb(self):
        self.assertEqual(classify_error("chromadb collection not found"), ErrorClass.MEMORY_FAILURE)

    def test_hash_failure(self):
        self.assertEqual(classify_error("non-hexadecimal digit found"), ErrorClass.HASH_FAILURE)

    def test_z3_failure(self):
        self.assertEqual(classify_error("z3 proof failed"), ErrorClass.Z3_FAILURE)

    def test_agent_failure(self):
        self.assertEqual(classify_error("tool_call_failed for agent"), ErrorClass.AGENT_FAILURE)

    def test_unknown(self):
        self.assertEqual(classify_error("something unexpected xyz123"), ErrorClass.UNKNOWN)

    def test_exception_object_accepted(self):
        self.assertEqual(classify_error(RuntimeError("rate_limit exceeded")), ErrorClass.INFRA_FAILURE)

    def test_cross_provider_infra(self):
        self.assertEqual(classify_error("err", {"retry_provider_different": True, "retry_succeeded": True}),
                         ErrorClass.INFRA_FAILURE)

    def test_cross_provider_model(self):
        self.assertEqual(classify_error("err", {"retry_provider_different": True, "retry_same_failure": True}),
                         ErrorClass.MODEL_FAILURE)


class TestEstimateTokens(unittest.TestCase):

    def test_empty_returns_zero(self):
        self.assertEqual(estimate_tokens(""), 0)

    def test_at_least_1(self):
        self.assertGreaterEqual(estimate_tokens("hi"), 1)

    def test_400_chars_100_tokens(self):
        self.assertEqual(estimate_tokens("a" * 400), 100)

    def test_longer_more_tokens(self):
        self.assertGreater(estimate_tokens("word " * 100), estimate_tokens("word"))


class TestStepTrace(unittest.TestCase):

    def test_defaults(self):
        s = StepTrace(step_index=0, agent="a", provider="groq")
        self.assertEqual(s.status, "pending")
        self.assertTrue(s.governance_passed)
        self.assertEqual(s.retries, 0)

    def test_custom_values(self):
        s = StepTrace(0, "b", "cerebras", latency_ms=200.0, status="completed", retries=1)
        self.assertEqual(s.latency_ms, 200.0)
        self.assertEqual(s.status, "completed")


class TestRunTraceToDict(unittest.TestCase):

    def _make(self):
        return RunTrace(run_id="r1", session_id="s1", crew_name="test", mode="research",
                        timestamp_start="", start_epoch=time.time(), deterministic=False,
                        input_text="hello", input_hash="abc")

    def test_to_dict_has_run_id(self):
        self.assertEqual(self._make().to_dict()["run_id"], "r1")

    def test_steps_serialized_as_list(self):
        t = self._make()
        t.steps.append(StepTrace(step_index=0, agent="a", provider="groq"))
        d = t.to_dict()
        self.assertEqual(len(d["steps"]), 1)
        self.assertEqual(d["steps"][0]["agent"], "a")


class TestComputeDerivedMetrics(unittest.TestCase):

    def _trace(self, steps=None):
        t = RunTrace(run_id="x", session_id="s", crew_name="c", mode="m",
                     timestamp_start="", start_epoch=time.time(), deterministic=False,
                     input_text="", input_hash="")
        t.end_epoch = time.time()
        if steps:
            t.steps = steps
        return t

    def test_empty_steps_stability_1(self):
        self.assertAlmostEqual(compute_derived_metrics(self._trace()).stability_score, 1.0)

    def test_failed_step_reduces_stability(self):
        steps = [StepTrace(0, "a", "g", status="failed"), StepTrace(1, "b", "g", status="completed")]
        t = compute_derived_metrics(self._trace(steps))
        self.assertAlmostEqual(t.stability_score, 0.5)

    def test_all_pass_gcr_1(self):
        steps = [StepTrace(i, "a", "g", governance_passed=True) for i in range(4)]
        t = compute_derived_metrics(self._trace(steps))
        self.assertAlmostEqual(t.governance_compliance_rate, 1.0)

    def test_retry_pressure_and_total(self):
        steps = [StepTrace(0, "a", "g", retries=3), StepTrace(1, "b", "g", retries=0)]
        t = compute_derived_metrics(self._trace(steps))
        self.assertAlmostEqual(t.retry_pressure, 1.5)
        self.assertEqual(t.total_retries, 3)

    def test_token_totals(self):
        steps = [StepTrace(0, "a", "g", token_input=100, token_output=50),
                 StepTrace(1, "b", "g", token_input=200, token_output=80)]
        t = compute_derived_metrics(self._trace(steps))
        self.assertEqual(t.total_token_input, 300)
        self.assertEqual(t.total_token_output, 130)

    def test_provider_switched_raises_pfi(self):
        steps = [StepTrace(0, "a", "g", provider_switched=True),
                 StepTrace(1, "b", "g", provider_switched=False)]
        t = compute_derived_metrics(self._trace(steps))
        self.assertAlmostEqual(t.provider_fragility_index, 0.5)

    def test_error_distribution(self):
        steps = [StepTrace(0, "a", "g", error_class="INFRA_FAILURE"),
                 StepTrace(1, "b", "g", error_class="INFRA_FAILURE"),
                 StepTrace(2, "c", "g", error_class="MODEL_FAILURE")]
        t = compute_derived_metrics(self._trace(steps))
        self.assertEqual(t.error_distribution.get("INFRA_FAILURE"), 2)
        self.assertEqual(t.error_distribution.get("MODEL_FAILURE"), 1)

    def test_provider_reliability_rate(self):
        steps = [StepTrace(0, "a", "groq", status="completed"),
                 StepTrace(1, "b", "groq", status="failed")]
        t = compute_derived_metrics(self._trace(steps))
        self.assertAlmostEqual(t.provider_reliability["groq"]["rate"], 0.5)


class TestExportDashboard(unittest.TestCase):

    def _trace(self):
        t = RunTrace(run_id="x", session_id="s", crew_name="c", mode="m",
                     timestamp_start="", start_epoch=time.time(), deterministic=False,
                     input_text="", input_hash="")
        t.steps = [
            StepTrace(0, "a", "groq", status="completed", error_class=""),
            StepTrace(1, "b", "groq", status="failed", error_class="INFRA_FAILURE"),
            StepTrace(2, "c", "cerebras", status="completed", error_class="",
                      causal_chain=[{"event": "retry"}]),
        ]
        return t

    def test_required_keys(self):
        d = self._trace().export_dashboard()
        for k in ("error_class_distribution", "provider_reliability_over_time", "causal_chains"):
            self.assertIn(k, d)

    def test_error_distribution_count(self):
        self.assertEqual(self._trace().export_dashboard()["error_class_distribution"].get("INFRA_FAILURE"), 1)

    def test_provider_reliability_present(self):
        d = self._trace().export_dashboard()["provider_reliability_over_time"]
        self.assertIn("groq", d)
        self.assertIn("cerebras", d)

    def test_causal_chains_populated(self):
        chains = self._trace().export_dashboard()["causal_chains"]
        self.assertEqual(len(chains), 1)
        self.assertEqual(chains[0]["agent"], "c")

    def test_empty_steps(self):
        t = RunTrace(run_id="x", session_id="s", crew_name="c", mode="m",
                     timestamp_start="", start_epoch=time.time(), deterministic=False,
                     input_text="", input_hash="")
        d = t.export_dashboard()
        self.assertEqual(d["error_class_distribution"], {})
        self.assertEqual(d["causal_chains"], [])


if __name__ == "__main__":
    unittest.main()
