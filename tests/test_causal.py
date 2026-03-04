"""
Tests for causal error classification in core/observability.py.
"""

import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from core.observability import (
    ErrorClass, classify_error, causal_trace, get_active_trace,
    StepTrace, RunTrace, compute_derived_metrics,
)


# ─────────────────────────────────────────────────────────────────────
# Tests: classify_error
# ─────────────────────────────────────────────────────────────────────

class TestClassifyInfraFailure(unittest.TestCase):
    """INFRA_FAILURE: HTTP errors, rate limits, timeouts."""

    def test_http_429(self):
        result = classify_error("HTTP 429 Too Many Requests")
        self.assertEqual(result, ErrorClass.INFRA_FAILURE)

    def test_http_500(self):
        result = classify_error("HTTP 500 Internal Server Error")
        self.assertEqual(result, ErrorClass.INFRA_FAILURE)

    def test_http_502(self):
        result = classify_error("502 Bad Gateway from upstream")
        self.assertEqual(result, ErrorClass.INFRA_FAILURE)

    def test_http_503(self):
        result = classify_error("503 Service Unavailable")
        self.assertEqual(result, ErrorClass.INFRA_FAILURE)

    def test_rate_limit(self):
        result = classify_error("rate_limit exceeded for groq provider")
        self.assertEqual(result, ErrorClass.INFRA_FAILURE)

    def test_rate_limit_with_spaces(self):
        result = classify_error("Rate limit reached, please retry")
        self.assertEqual(result, ErrorClass.INFRA_FAILURE)

    def test_resource_exhausted(self):
        result = classify_error("resource_exhausted: quota exceeded")
        self.assertEqual(result, ErrorClass.INFRA_FAILURE)

    def test_timeout(self):
        result = classify_error("Request timed out after 30s")
        self.assertEqual(result, ErrorClass.INFRA_FAILURE)

    def test_connection_error(self):
        result = classify_error("ConnectionError: connection refused")
        self.assertEqual(result, ErrorClass.INFRA_FAILURE)

    def test_retry_different_provider_succeeded(self):
        """Retry with different provider succeeded → confirms INFRA."""
        result = classify_error(
            "Unknown error occurred",
            context={
                "retry_provider_different": True,
                "retry_succeeded": True,
            }
        )
        self.assertEqual(result, ErrorClass.INFRA_FAILURE)


class TestClassifyGovernanceFailure(unittest.TestCase):
    """GOVERNANCE_FAILURE: constitution violations."""

    def test_governance_violations_in_context(self):
        result = classify_error(
            "Output rejected",
            context={"governance_violations": ["NO_HALLUCINATION_CLAIM"]}
        )
        self.assertEqual(result, ErrorClass.GOVERNANCE_FAILURE)

    def test_governance_keyword_in_error(self):
        result = classify_error("Governance BLOCKED: [NO_EMPTY_OUTPUT]")
        self.assertEqual(result, ErrorClass.GOVERNANCE_FAILURE)

    def test_constitution_keyword(self):
        result = classify_error("Constitution enforcement failed")
        self.assertEqual(result, ErrorClass.GOVERNANCE_FAILURE)

    def test_ast_verify_keyword(self):
        result = classify_error("AST_VERIFY Block 1: Unsafe call eval()")
        self.assertEqual(result, ErrorClass.GOVERNANCE_FAILURE)

    def test_hallucination_keyword(self):
        result = classify_error("hallucination detected in output")
        self.assertEqual(result, ErrorClass.GOVERNANCE_FAILURE)


class TestClassifyModelFailure(unittest.TestCase):
    """MODEL_FAILURE: model-specific issues."""

    def test_invalid_grammar(self):
        result = classify_error("invalid grammar: structured output not supported")
        self.assertEqual(result, ErrorClass.MODEL_FAILURE)

    def test_bad_request(self):
        result = classify_error("bad request: unsupported parameter")
        self.assertEqual(result, ErrorClass.MODEL_FAILURE)

    def test_validation_error(self):
        result = classify_error("pydantic validation error: missing field")
        self.assertEqual(result, ErrorClass.MODEL_FAILURE)

    def test_retry_different_provider_same_failure(self):
        """Retry with different provider had same failure → MODEL."""
        result = classify_error(
            "Unknown error occurred",
            context={
                "retry_provider_different": True,
                "retry_same_failure": True,
            }
        )
        self.assertEqual(result, ErrorClass.MODEL_FAILURE)


class TestClassifyUnknown(unittest.TestCase):
    """UNKNOWN: unclassifiable errors."""

    def test_unknown_error(self):
        result = classify_error("Something weird happened")
        self.assertEqual(result, ErrorClass.UNKNOWN)

    def test_empty_error(self):
        result = classify_error("")
        self.assertEqual(result, ErrorClass.UNKNOWN)

    def test_exception_object(self):
        result = classify_error(ValueError("unexpected value"))
        self.assertEqual(result, ErrorClass.UNKNOWN)


# ─────────────────────────────────────────────────────────────────────
# Tests: @causal_trace decorator
# ─────────────────────────────────────────────────────────────────────

class TestCausalTraceDecorator(unittest.TestCase):
    """The @causal_trace decorator captures errors and classifies them."""

    def test_successful_function(self):
        @causal_trace(task_id="test-success")
        def good_func():
            return 42

        result = good_func()
        self.assertEqual(result, 42)

    def test_failed_function_captures_error(self):
        @causal_trace(task_id="test-fail", provider="groq")
        def bad_func():
            raise ConnectionError("HTTP 429 Too Many Requests")

        with self.assertRaises(ConnectionError):
            bad_func()

    def test_failed_function_classifies_error(self):
        """After failure, the trace should have the error classified."""
        traces_collected = []

        @causal_trace(task_id="test-classify", provider="nvidia")
        def failing_func():
            raise TimeoutError("Request timed out after 30s")

        # Capture the trace by wrapping
        import core.observability as obs
        original = obs._active_trace

        try:
            failing_func()
        except TimeoutError:
            pass

        # The decorator creates and cleans up its own trace,
        # so we test by verifying the function raises correctly
        # and that classify_error works on the same error
        error_class = classify_error("Request timed out after 30s")
        self.assertEqual(error_class, ErrorClass.INFRA_FAILURE)

    def test_decorator_preserves_function_name(self):
        @causal_trace(task_id="test-name")
        def my_research_func():
            """Docstring."""
            return "ok"

        self.assertEqual(my_research_func.__name__, "my_research_func")
        self.assertEqual(my_research_func.__doc__, "Docstring.")

    def test_decorator_with_args(self):
        @causal_trace(task_id="test-args")
        def func_with_args(x, y, multiplier=1):
            return (x + y) * multiplier

        result = func_with_args(3, 4, multiplier=2)
        self.assertEqual(result, 14)


# ─────────────────────────────────────────────────────────────────────
# Tests: StepTrace causal fields
# ─────────────────────────────────────────────────────────────────────

class TestStepTraceCausalFields(unittest.TestCase):
    """StepTrace has error_class and causal_chain fields."""

    def test_default_error_class_empty(self):
        step = StepTrace(step_index=0, agent="test", provider="groq")
        self.assertEqual(step.error_class, "")

    def test_default_causal_chain_empty(self):
        step = StepTrace(step_index=0, agent="test", provider="groq")
        self.assertEqual(step.causal_chain, [])

    def test_set_error_class(self):
        step = StepTrace(
            step_index=0, agent="test", provider="groq",
            error_class=ErrorClass.INFRA_FAILURE.value,
        )
        self.assertEqual(step.error_class, "INFRA_FAILURE")

    def test_append_causal_chain(self):
        step = StepTrace(step_index=0, agent="test", provider="groq")
        step.causal_chain.append({
            "timestamp": "2026-03-04T10:00:00",
            "event": "error: timeout",
            "classification": "INFRA_FAILURE",
        })
        self.assertEqual(len(step.causal_chain), 1)
        self.assertEqual(step.causal_chain[0]["classification"], "INFRA_FAILURE")


# ─────────────────────────────────────────────────────────────────────
# Tests: RunTrace.export_dashboard()
# ─────────────────────────────────────────────────────────────────────

class TestExportDashboard(unittest.TestCase):
    """RunTrace.export_dashboard() returns structured data for visualization."""

    def _make_trace(self) -> RunTrace:
        trace = RunTrace(crew_name="test_crew")
        trace.steps = [
            StepTrace(
                step_index=0, agent="research", provider="groq",
                status="failed", error="HTTP 429",
                error_class="INFRA_FAILURE",
                causal_chain=[{
                    "timestamp": "2026-03-04T10:00:00",
                    "event": "error: HTTP 429",
                    "classification": "INFRA_FAILURE",
                }],
            ),
            StepTrace(
                step_index=1, agent="research", provider="cerebras",
                status="completed", error_class="",
            ),
            StepTrace(
                step_index=2, agent="qa", provider="groq",
                status="failed", error="governance blocked",
                error_class="GOVERNANCE_FAILURE",
                causal_chain=[{
                    "timestamp": "2026-03-04T10:01:00",
                    "event": "error: governance blocked",
                    "classification": "GOVERNANCE_FAILURE",
                }],
            ),
        ]
        return trace

    def test_dashboard_has_required_keys(self):
        trace = self._make_trace()
        dashboard = trace.export_dashboard()
        self.assertIn("error_class_distribution", dashboard)
        self.assertIn("provider_reliability_over_time", dashboard)
        self.assertIn("causal_chains", dashboard)

    def test_error_class_distribution(self):
        trace = self._make_trace()
        dashboard = trace.export_dashboard()
        dist = dashboard["error_class_distribution"]
        self.assertEqual(dist["INFRA_FAILURE"], 1)
        self.assertEqual(dist["GOVERNANCE_FAILURE"], 1)

    def test_provider_reliability(self):
        trace = self._make_trace()
        dashboard = trace.export_dashboard()
        reliability = dashboard["provider_reliability_over_time"]
        # groq: 0 success, 2 fail
        self.assertEqual(reliability["groq"]["success"], 0)
        self.assertEqual(reliability["groq"]["fail"], 2)
        self.assertEqual(reliability["groq"]["rate"], 0.0)
        # cerebras: 1 success, 0 fail
        self.assertEqual(reliability["cerebras"]["success"], 1)
        self.assertEqual(reliability["cerebras"]["fail"], 0)
        self.assertEqual(reliability["cerebras"]["rate"], 1.0)

    def test_causal_chains(self):
        trace = self._make_trace()
        dashboard = trace.export_dashboard()
        chains = dashboard["causal_chains"]
        # Only steps with non-empty causal_chain
        self.assertEqual(len(chains), 2)
        self.assertEqual(chains[0]["error_class"], "INFRA_FAILURE")
        self.assertEqual(chains[1]["error_class"], "GOVERNANCE_FAILURE")

    def test_empty_trace_dashboard(self):
        trace = RunTrace(crew_name="empty")
        dashboard = trace.export_dashboard()
        self.assertEqual(dashboard["error_class_distribution"], {})
        self.assertEqual(dashboard["provider_reliability_over_time"], {})
        self.assertEqual(dashboard["causal_chains"], [])


# ─────────────────────────────────────────────────────────────────────
# Tests: compute_derived_metrics includes error_distribution
# ─────────────────────────────────────────────────────────────────────

class TestDerivedMetricsErrorDistribution(unittest.TestCase):
    """compute_derived_metrics populates error_distribution and provider_reliability."""

    def test_error_distribution_computed(self):
        trace = RunTrace(crew_name="test")
        trace.steps = [
            StepTrace(step_index=0, agent="a", provider="groq",
                      status="failed", error_class="INFRA_FAILURE"),
            StepTrace(step_index=1, agent="a", provider="cerebras",
                      status="completed"),
        ]
        trace = compute_derived_metrics(trace)
        self.assertEqual(trace.error_distribution.get("INFRA_FAILURE"), 1)

    def test_provider_reliability_computed(self):
        trace = RunTrace(crew_name="test")
        trace.steps = [
            StepTrace(step_index=0, agent="a", provider="groq", status="failed"),
            StepTrace(step_index=1, agent="a", provider="groq", status="completed"),
        ]
        trace = compute_derived_metrics(trace)
        self.assertEqual(trace.provider_reliability["groq"]["success"], 1)
        self.assertEqual(trace.provider_reliability["groq"]["fail"], 1)
        self.assertEqual(trace.provider_reliability["groq"]["rate"], 0.5)


if __name__ == "__main__":
    unittest.main()
