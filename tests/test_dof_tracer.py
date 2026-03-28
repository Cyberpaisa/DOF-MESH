"""Tests para core.dof_tracer — Sistema de tracing estructurado DOF."""

import json
import os
import tempfile
import time
import unittest

from core.dof_tracer import (
    DOFTracer,
    Span,
    Trace,
    VALID_SPAN_TYPES,
    SPAN_TYPE_METRICS,
)


class TestSpanDataclass(unittest.TestCase):
    """Tests para la dataclass Span."""

    def test_span_defaults(self):
        span = Span()
        self.assertEqual(span.status, "running")
        self.assertIsNone(span.end_time)
        self.assertIsNone(span.duration_ms)
        self.assertIsNone(span.parent_span_id)
        self.assertEqual(span.span_type, "custom")
        self.assertIsInstance(span.events, list)
        self.assertEqual(len(span.span_id), 8)

    def test_span_to_dict(self):
        span = Span(name="test", span_type="llm", trace_id="abc")
        d = span.to_dict()
        self.assertIsInstance(d, dict)
        self.assertEqual(d["name"], "test")
        self.assertEqual(d["span_type"], "llm")
        self.assertEqual(d["trace_id"], "abc")


class TestTraceDataclass(unittest.TestCase):
    """Tests para la dataclass Trace."""

    def test_trace_defaults(self):
        trace = Trace()
        self.assertEqual(trace.status, "running")
        self.assertEqual(trace.total_tokens, 0)
        self.assertEqual(trace.total_cost, 0.0)
        self.assertIsNone(trace.governance_verdict)
        self.assertIsInstance(trace.spans, list)
        self.assertEqual(len(trace.trace_id), 8)

    def test_trace_to_dict(self):
        trace = Trace(name="mi_trace")
        d = trace.to_dict()
        self.assertIsInstance(d, dict)
        self.assertEqual(d["name"], "mi_trace")
        self.assertIsInstance(d["spans"], list)


class TestStartEndTrace(unittest.TestCase):
    """Tests para start_trace y end_trace."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
        self.tmp.close()
        self.tracer = DOFTracer(storage_path=self.tmp.name)

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_start_trace(self):
        trace = self.tracer.start_trace("test_trace")
        self.assertEqual(trace.name, "test_trace")
        self.assertEqual(trace.status, "running")
        self.assertIsNotNone(trace.start_time)

    def test_start_trace_with_metadata(self):
        trace = self.tracer.start_trace("m_trace", metadata={"env": "test"})
        self.assertEqual(trace.metadata["env"], "test")

    def test_end_trace(self):
        trace = self.tracer.start_trace("end_test")
        ended = self.tracer.end_trace(trace.trace_id)
        self.assertEqual(ended.status, "completed")
        self.assertIsNotNone(ended.end_time)
        self.assertIsNotNone(ended.total_duration_ms)
        self.assertGreaterEqual(ended.total_duration_ms, 0)

    def test_end_trace_failed(self):
        trace = self.tracer.start_trace("fail_trace")
        ended = self.tracer.end_trace(trace.trace_id, status="failed")
        self.assertEqual(ended.status, "failed")

    def test_end_trace_nonexistent_raises(self):
        with self.assertRaises(ValueError):
            self.tracer.end_trace("nonexistent")


class TestStartEndSpan(unittest.TestCase):
    """Tests para start_span y end_span."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
        self.tmp.close()
        self.tracer = DOFTracer(storage_path=self.tmp.name)
        self.trace = self.tracer.start_trace("span_test")

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_start_span(self):
        span = self.tracer.start_span(self.trace.trace_id, "my_span", "llm")
        self.assertEqual(span.name, "my_span")
        self.assertEqual(span.span_type, "llm")
        self.assertEqual(span.trace_id, self.trace.trace_id)
        self.assertEqual(span.status, "running")

    def test_end_span_duration(self):
        span = self.tracer.start_span(self.trace.trace_id, "dur_span", "tool")
        time.sleep(0.01)
        ended = self.tracer.end_span(span.span_id)
        self.assertEqual(ended.status, "completed")
        self.assertIsNotNone(ended.duration_ms)
        self.assertGreater(ended.duration_ms, 0)

    def test_end_span_with_output(self):
        span = self.tracer.start_span(self.trace.trace_id, "out_span", "custom")
        ended = self.tracer.end_span(span.span_id, output_data={"result": 42})
        self.assertEqual(ended.output_data["result"], 42)

    def test_end_span_with_metadata(self):
        span = self.tracer.start_span(self.trace.trace_id, "meta_span", "llm")
        ended = self.tracer.end_span(
            span.span_id, metadata={"model": "gpt-4", "tokens_in": 100}
        )
        self.assertEqual(ended.metadata["model"], "gpt-4")

    def test_end_span_failed(self):
        span = self.tracer.start_span(self.trace.trace_id, "fail_span", "z3")
        ended = self.tracer.end_span(span.span_id, status="failed")
        self.assertEqual(ended.status, "failed")

    def test_span_nonexistent_trace_raises(self):
        with self.assertRaises(ValueError):
            self.tracer.start_span("no_trace", "s", "custom")

    def test_end_span_nonexistent_raises(self):
        with self.assertRaises(ValueError):
            self.tracer.end_span("no_span")

    def test_invalid_span_type_raises(self):
        with self.assertRaises(ValueError):
            self.tracer.start_span(self.trace.trace_id, "bad", "invalid_type")


class TestNestedSpans(unittest.TestCase):
    """Tests para spans anidados con parent_span_id."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
        self.tmp.close()
        self.tracer = DOFTracer(storage_path=self.tmp.name)

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_nested_spans(self):
        trace = self.tracer.start_trace("nested")
        parent = self.tracer.start_span(trace.trace_id, "parent", "governance")
        child = self.tracer.start_span(
            trace.trace_id, "child", "z3", parent_span_id=parent.span_id
        )
        self.assertEqual(child.parent_span_id, parent.span_id)
        self.assertIsNone(parent.parent_span_id)

    def test_deep_nesting(self):
        trace = self.tracer.start_trace("deep")
        s1 = self.tracer.start_span(trace.trace_id, "l1", "mesh")
        s2 = self.tracer.start_span(
            trace.trace_id, "l2", "tool", parent_span_id=s1.span_id
        )
        s3 = self.tracer.start_span(
            trace.trace_id, "l3", "llm", parent_span_id=s2.span_id
        )
        self.assertEqual(s3.parent_span_id, s2.span_id)
        self.assertEqual(s2.parent_span_id, s1.span_id)
        self.assertIsNone(s1.parent_span_id)


class TestSpanTypes(unittest.TestCase):
    """Tests para cada tipo de span valido."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
        self.tmp.close()
        self.tracer = DOFTracer(storage_path=self.tmp.name)
        self.trace = self.tracer.start_trace("types_test")

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_all_valid_types(self):
        for st in VALID_SPAN_TYPES:
            span = self.tracer.start_span(self.trace.trace_id, f"span_{st}", st)
            self.assertEqual(span.span_type, st)

    def test_span_type_metrics_keys(self):
        """Verifica que las metricas esperadas estan definidas por tipo."""
        for st in ["llm", "governance", "z3", "sentinel", "mesh", "tool"]:
            self.assertIn(st, SPAN_TYPE_METRICS)
            self.assertIsInstance(SPAN_TYPE_METRICS[st], list)
            self.assertGreater(len(SPAN_TYPE_METRICS[st]), 0)


class TestContextManager(unittest.TestCase):
    """Tests para el context manager de spans."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
        self.tmp.close()
        self.tracer = DOFTracer(storage_path=self.tmp.name)

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_context_manager_success(self):
        trace = self.tracer.start_trace("cm_ok")
        with self.tracer.span(trace.trace_id, "gov_check", "governance") as span:
            span.output_data = {"verdict": "PASS", "score": 0.95}

        self.assertEqual(span.status, "completed")
        self.assertIsNotNone(span.duration_ms)
        self.assertEqual(span.output_data["verdict"], "PASS")

    def test_context_manager_failure(self):
        trace = self.tracer.start_trace("cm_fail")
        with self.assertRaises(RuntimeError):
            with self.tracer.span(trace.trace_id, "bad_op", "tool") as span:
                raise RuntimeError("tool crashed")

        self.assertEqual(span.status, "failed")
        self.assertIsNotNone(span.duration_ms)

    def test_context_manager_with_input(self):
        trace = self.tracer.start_trace("cm_input")
        with self.tracer.span(
            trace.trace_id, "llm_call", "llm", input_data={"prompt": "hola"}
        ) as span:
            span.output_data = {"response": "mundo"}

        self.assertEqual(span.input_data["prompt"], "hola")
        self.assertEqual(span.output_data["response"], "mundo")


class TestAddEvents(unittest.TestCase):
    """Tests para add_event."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
        self.tmp.close()
        self.tracer = DOFTracer(storage_path=self.tmp.name)

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_add_event(self):
        trace = self.tracer.start_trace("events")
        span = self.tracer.start_span(trace.trace_id, "ev_span", "llm")
        self.tracer.add_event(span.span_id, "token_stream_start")
        self.tracer.add_event(span.span_id, "token_stream_end", {"tokens": 150})

        self.assertEqual(len(span.events), 2)
        self.assertEqual(span.events[0]["name"], "token_stream_start")
        self.assertEqual(span.events[1]["data"]["tokens"], 150)
        self.assertIn("timestamp", span.events[0])

    def test_add_event_nonexistent_raises(self):
        with self.assertRaises(ValueError):
            self.tracer.add_event("no_span", "ev")


class TestTraceSummary(unittest.TestCase):
    """Tests para get_trace_summary."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
        self.tmp.close()
        self.tracer = DOFTracer(storage_path=self.tmp.name)

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_summary_structure(self):
        trace = self.tracer.start_trace("summary")
        self.tracer.start_span(trace.trace_id, "s1", "llm")
        self.tracer.start_span(trace.trace_id, "s2", "governance")
        self.tracer.start_span(trace.trace_id, "s3", "llm")
        self.tracer.end_trace(trace.trace_id)

        summary = self.tracer.get_trace_summary(trace.trace_id)
        self.assertEqual(summary["total_spans"], 3)
        self.assertEqual(summary["spans_by_type"]["llm"], 2)
        self.assertEqual(summary["spans_by_type"]["governance"], 1)
        self.assertIn("total_duration_ms", summary)
        self.assertIn("total_tokens", summary)
        self.assertIn("total_cost", summary)
        self.assertIn("governance_verdict", summary)

    def test_summary_with_failed_spans(self):
        trace = self.tracer.start_trace("fail_summary")
        s1 = self.tracer.start_span(trace.trace_id, "ok", "tool")
        self.tracer.end_span(s1.span_id, status="completed")
        s2 = self.tracer.start_span(trace.trace_id, "bad", "tool")
        self.tracer.end_span(s2.span_id, status="failed")
        self.tracer.end_trace(trace.trace_id)

        summary = self.tracer.get_trace_summary(trace.trace_id)
        self.assertEqual(summary["completed_spans"], 1)
        self.assertEqual(summary["failed_spans"], 1)


class TestTokenCostAggregation(unittest.TestCase):
    """Tests para agregacion de tokens y costo."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
        self.tmp.close()
        self.tracer = DOFTracer(storage_path=self.tmp.name)

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_total_tokens_and_cost(self):
        trace = self.tracer.start_trace("tokens")
        s1 = self.tracer.start_span(trace.trace_id, "llm1", "llm")
        self.tracer.end_span(
            s1.span_id, metadata={"tokens_in": 100, "tokens_out": 200, "cost": 0.01}
        )
        s2 = self.tracer.start_span(trace.trace_id, "llm2", "llm")
        self.tracer.end_span(
            s2.span_id, metadata={"tokens_in": 50, "tokens_out": 150, "cost": 0.005}
        )
        ended = self.tracer.end_trace(trace.trace_id)

        self.assertEqual(ended.total_tokens, 500)  # 100+200+50+150
        self.assertAlmostEqual(ended.total_cost, 0.015, places=4)

    def test_non_llm_spans_no_tokens(self):
        trace = self.tracer.start_trace("no_tokens")
        s1 = self.tracer.start_span(trace.trace_id, "gov", "governance")
        self.tracer.end_span(s1.span_id, metadata={"score": 0.9})
        ended = self.tracer.end_trace(trace.trace_id)
        self.assertEqual(ended.total_tokens, 0)
        self.assertEqual(ended.total_cost, 0.0)


class TestGovernanceVerdict(unittest.TestCase):
    """Tests para governance_verdict en trace."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
        self.tmp.close()
        self.tracer = DOFTracer(storage_path=self.tmp.name)

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_governance_verdict_from_output(self):
        trace = self.tracer.start_trace("gov_v")
        s = self.tracer.start_span(trace.trace_id, "gov", "governance")
        self.tracer.end_span(s.span_id, output_data={"verdict": "APPROVED"})
        ended = self.tracer.end_trace(trace.trace_id)
        self.assertEqual(ended.governance_verdict, "APPROVED")

    def test_governance_verdict_from_metadata(self):
        trace = self.tracer.start_trace("gov_m")
        s = self.tracer.start_span(trace.trace_id, "gov", "governance")
        self.tracer.end_span(s.span_id, metadata={"verdict": "REJECTED"})
        ended = self.tracer.end_trace(trace.trace_id)
        self.assertEqual(ended.governance_verdict, "REJECTED")


class TestPersistence(unittest.TestCase):
    """Tests para persistencia JSONL."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
        self.tmp.close()
        self.tracer = DOFTracer(storage_path=self.tmp.name)

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_persist_on_end_trace(self):
        trace = self.tracer.start_trace("persist_test")
        self.tracer.start_span(trace.trace_id, "s1", "custom")
        self.tracer.end_trace(trace.trace_id)

        with open(self.tmp.name) as f:
            lines = [l.strip() for l in f if l.strip()]
        self.assertEqual(len(lines), 1)
        data = json.loads(lines[0])
        self.assertEqual(data["trace_id"], trace.trace_id)
        self.assertEqual(data["name"], "persist_test")
        self.assertEqual(len(data["spans"]), 1)

    def test_multiple_traces_persist(self):
        for i in range(3):
            trace = self.tracer.start_trace(f"trace_{i}")
            self.tracer.end_trace(trace.trace_id)

        with open(self.tmp.name) as f:
            lines = [l.strip() for l in f if l.strip()]
        self.assertEqual(len(lines), 3)


class TestGetTraceAndSpan(unittest.TestCase):
    """Tests para get_trace y get_span."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
        self.tmp.close()
        self.tracer = DOFTracer(storage_path=self.tmp.name)

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_get_trace(self):
        trace = self.tracer.start_trace("get_me")
        got = self.tracer.get_trace(trace.trace_id)
        self.assertEqual(got.name, "get_me")

    def test_get_trace_nonexistent_raises(self):
        with self.assertRaises(ValueError):
            self.tracer.get_trace("nope")

    def test_get_span(self):
        trace = self.tracer.start_trace("gs")
        span = self.tracer.start_span(trace.trace_id, "my_span", "sentinel")
        got = self.tracer.get_span(span.span_id)
        self.assertEqual(got.name, "my_span")
        self.assertEqual(got.span_type, "sentinel")

    def test_get_span_nonexistent_raises(self):
        with self.assertRaises(ValueError):
            self.tracer.get_span("nope")


class TestListTraces(unittest.TestCase):
    """Tests para list_traces."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
        self.tmp.close()
        self.tracer = DOFTracer(storage_path=self.tmp.name)

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_list_traces_order(self):
        t1 = self.tracer.start_trace("first")
        t2 = self.tracer.start_trace("second")
        traces = self.tracer.list_traces()
        # Mas reciente primero
        self.assertEqual(traces[0].trace_id, t2.trace_id)
        self.assertEqual(traces[1].trace_id, t1.trace_id)

    def test_list_traces_limit(self):
        for i in range(10):
            self.tracer.start_trace(f"t{i}")
        traces = self.tracer.list_traces(limit=3)
        self.assertEqual(len(traces), 3)


class TestDurationCalculation(unittest.TestCase):
    """Tests para calculo de duracion."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
        self.tmp.close()
        self.tracer = DOFTracer(storage_path=self.tmp.name)

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_span_duration_positive(self):
        trace = self.tracer.start_trace("dur")
        span = self.tracer.start_span(trace.trace_id, "s", "custom")
        time.sleep(0.02)
        self.tracer.end_span(span.span_id)
        self.assertGreater(span.duration_ms, 10)

    def test_trace_duration_positive(self):
        trace = self.tracer.start_trace("dur_t")
        time.sleep(0.02)
        self.tracer.end_trace(trace.trace_id)
        self.assertGreater(trace.total_duration_ms, 10)


class TestMultipleSpanTypes(unittest.TestCase):
    """Test trace con multiples tipos de span."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
        self.tmp.close()
        self.tracer = DOFTracer(storage_path=self.tmp.name)

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_mixed_span_types(self):
        trace = self.tracer.start_trace("mixed")

        # LLM span
        s1 = self.tracer.start_span(trace.trace_id, "llm_call", "llm")
        self.tracer.end_span(
            s1.span_id,
            output_data={"response": "ok"},
            metadata={"tokens_in": 50, "tokens_out": 100, "cost": 0.002},
        )

        # Governance span
        s2 = self.tracer.start_span(trace.trace_id, "gov", "governance")
        self.tracer.end_span(
            s2.span_id, output_data={"verdict": "PASS", "score": 0.95}
        )

        # Z3 span
        s3 = self.tracer.start_span(trace.trace_id, "z3_check", "z3")
        self.tracer.end_span(
            s3.span_id,
            output_data={"verdict": "PROVEN"},
            metadata={"theorems_checked": 4},
        )

        # Sentinel span
        s4 = self.tracer.start_span(trace.trace_id, "sentinel", "sentinel")
        self.tracer.end_span(
            s4.span_id,
            metadata={"checks_run": 27, "overall_score": 85, "verdict": "PASS"},
        )

        # Mesh span
        s5 = self.tracer.start_span(trace.trace_id, "mesh_op", "mesh")
        self.tracer.end_span(
            s5.span_id,
            metadata={"node_id": "node-1", "latency_ms": 12.5, "circuit_state": "closed"},
        )

        # Tool span
        s6 = self.tracer.start_span(trace.trace_id, "tool_exec", "tool")
        self.tracer.end_span(
            s6.span_id,
            metadata={"tool_name": "web_search", "success": True, "duration": 450},
        )

        ended = self.tracer.end_trace(trace.trace_id)

        self.assertEqual(len(ended.spans), 6)
        self.assertEqual(ended.total_tokens, 150)  # 50+100
        self.assertAlmostEqual(ended.total_cost, 0.002, places=4)
        self.assertEqual(ended.governance_verdict, "PASS")

        summary = self.tracer.get_trace_summary(trace.trace_id)
        self.assertEqual(summary["total_spans"], 6)
        self.assertEqual(summary["spans_by_type"]["llm"], 1)
        self.assertEqual(summary["spans_by_type"]["governance"], 1)
        self.assertEqual(summary["spans_by_type"]["z3"], 1)
        self.assertEqual(summary["spans_by_type"]["sentinel"], 1)
        self.assertEqual(summary["spans_by_type"]["mesh"], 1)
        self.assertEqual(summary["spans_by_type"]["tool"], 1)


class TestAutoCloseRunningSpans(unittest.TestCase):
    """Test que end_trace auto-cierra spans running."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
        self.tmp.close()
        self.tracer = DOFTracer(storage_path=self.tmp.name)

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_auto_close_running_spans(self):
        trace = self.tracer.start_trace("auto_close")
        s1 = self.tracer.start_span(trace.trace_id, "unclosed", "custom")
        # No cerramos s1 manualmente
        self.assertEqual(s1.status, "running")
        self.tracer.end_trace(trace.trace_id)
        # Ahora debe estar cerrado
        self.assertEqual(s1.status, "completed")
        self.assertIsNotNone(s1.duration_ms)


class TestStatusTransitions(unittest.TestCase):
    """Tests para transiciones de status."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
        self.tmp.close()
        self.tracer = DOFTracer(storage_path=self.tmp.name)

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_span_running_to_completed(self):
        trace = self.tracer.start_trace("st")
        span = self.tracer.start_span(trace.trace_id, "s", "custom")
        self.assertEqual(span.status, "running")
        self.tracer.end_span(span.span_id)
        self.assertEqual(span.status, "completed")

    def test_span_running_to_failed(self):
        trace = self.tracer.start_trace("st2")
        span = self.tracer.start_span(trace.trace_id, "s", "custom")
        self.assertEqual(span.status, "running")
        self.tracer.end_span(span.span_id, status="failed")
        self.assertEqual(span.status, "failed")

    def test_trace_running_to_completed(self):
        trace = self.tracer.start_trace("st3")
        self.assertEqual(trace.status, "running")
        self.tracer.end_trace(trace.trace_id)
        self.assertEqual(trace.status, "completed")

    def test_trace_running_to_failed(self):
        trace = self.tracer.start_trace("st4")
        self.tracer.end_trace(trace.trace_id, status="failed")
        self.assertEqual(trace.status, "failed")


if __name__ == "__main__":
    unittest.main()
