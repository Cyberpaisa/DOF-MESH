"""Tests for core/otel_bridge.py — no-op path (OTel not installed)."""

import os
import unittest

import core.otel_bridge as otel_mod
from core.otel_bridge import (
    LAYER_NAMES,
    METRIC_NAMES,
    OTelBridge,
    SpanContext,
    get_bridge,
    reset_bridge,
)


class TestConstants(unittest.TestCase):

    def test_layer_names_non_empty(self):
        self.assertTrue(len(LAYER_NAMES) > 0)

    def test_layer_names_all_strings(self):
        for n in LAYER_NAMES:
            self.assertIsInstance(n, str)

    def test_layer_names_have_dof_prefix(self):
        for n in LAYER_NAMES:
            self.assertTrue(n.startswith("dof."), n)

    def test_metric_names_non_empty(self):
        self.assertTrue(len(METRIC_NAMES) > 0)

    def test_metric_types_valid(self):
        valid = {"histogram", "counter", "gauge"}
        for name, kind in METRIC_NAMES.items():
            self.assertIn(kind, valid, f"{name}: {kind}")

    def test_known_layers_present(self):
        for layer in ("dof.constitution", "dof.ast", "dof.z3"):
            self.assertIn(layer, LAYER_NAMES)

    def test_known_metrics_present(self):
        self.assertIn("dof.governance.latency", METRIC_NAMES)
        self.assertIn("dof.governance.pass_rate", METRIC_NAMES)


class TestSpanContext(unittest.TestCase):

    def _make(self, layer="dof.constitution"):
        import time
        return SpanContext(layer_name=layer, start_time=time.time())

    def test_layer_name_stored(self):
        ctx = self._make("dof.z3")
        self.assertEqual(ctx.layer_name, "dof.z3")

    def test_real_span_none_by_default(self):
        ctx = self._make()
        self.assertIsNone(ctx._real_span)

    def test_set_attribute_noop_without_real_span(self):
        ctx = self._make()
        ctx.set_attribute("key", "value")  # must not raise

    def test_set_status_pass_noop(self):
        ctx = self._make()
        ctx.set_status(True)   # must not raise

    def test_set_status_fail_noop(self):
        ctx = self._make()
        ctx.set_status(False)  # must not raise


class TestOTelBridgeNoOp(unittest.TestCase):
    """All tests run without OTel installed → no-op mode."""

    def setUp(self):
        # Ensure no endpoint var leaks in from environment
        self._orig = os.environ.pop("OTEL_EXPORTER_OTLP_ENDPOINT", None)

    def tearDown(self):
        if self._orig is not None:
            os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = self._orig

    def test_is_active_false_without_otel(self):
        b = OTelBridge()
        self.assertFalse(b.is_active)

    def test_is_active_false_without_endpoint(self):
        b = OTelBridge(endpoint=None)
        self.assertFalse(b.is_active)

    def test_service_name_stored(self):
        b = OTelBridge(service_name="my-service")
        self.assertEqual(b.service_name, "my-service")

    def test_endpoint_from_kwarg(self):
        b = OTelBridge(endpoint="http://localhost:4317")
        self.assertEqual(b.endpoint, "http://localhost:4317")

    def test_endpoint_from_env(self):
        os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://env-host:4317"
        b = OTelBridge()
        self.assertEqual(b.endpoint, "http://env-host:4317")
        del os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"]

    def test_trace_layer_yields_span_context(self):
        b = OTelBridge()
        with b.trace_layer("dof.constitution") as ctx:
            self.assertIsInstance(ctx, SpanContext)

    def test_trace_layer_layer_name_correct(self):
        b = OTelBridge()
        with b.trace_layer("dof.ast") as ctx:
            self.assertEqual(ctx.layer_name, "dof.ast")

    def test_trace_layer_set_attribute_noop(self):
        b = OTelBridge()
        with b.trace_layer("dof.supervisor") as ctx:
            ctx.set_attribute("score", 0.95)   # must not raise

    def test_trace_layer_set_status_noop(self):
        b = OTelBridge()
        with b.trace_layer("dof.z3") as ctx:
            ctx.set_status(True)   # must not raise

    def test_trace_layer_context_manager_complete(self):
        b = OTelBridge()
        ran = []
        with b.trace_layer("dof.memory") as ctx:
            ran.append(True)
        self.assertTrue(ran)

    def test_trace_layer_exception_propagates(self):
        b = OTelBridge()
        with self.assertRaises(ValueError):
            with b.trace_layer("dof.constitution"):
                raise ValueError("test error")

    def test_record_metric_noop_when_inactive(self):
        b = OTelBridge()
        b.record_metric("dof.governance.latency", 12.5, {"layer": "constitution"})
        # Must not raise

    def test_record_metric_unknown_name_noop(self):
        b = OTelBridge()
        b.record_metric("unknown.metric", 99.0)  # must not raise

    def test_flush_noop_when_inactive(self):
        b = OTelBridge()
        b.flush()   # must not raise

    def test_all_layer_names_traceable(self):
        b = OTelBridge()
        for layer in LAYER_NAMES:
            with b.trace_layer(layer) as ctx:
                self.assertEqual(ctx.layer_name, layer)


class TestSingleton(unittest.TestCase):

    def setUp(self):
        reset_bridge()

    def tearDown(self):
        reset_bridge()

    def test_get_bridge_returns_otel_bridge(self):
        b = get_bridge()
        self.assertIsInstance(b, OTelBridge)

    def test_get_bridge_same_instance(self):
        b1 = get_bridge()
        b2 = get_bridge()
        self.assertIs(b1, b2)

    def test_reset_bridge_clears_singleton(self):
        b1 = get_bridge()
        reset_bridge()
        b2 = get_bridge()
        self.assertIsNot(b1, b2)

    def test_reset_bridge_noop_when_none(self):
        reset_bridge()  # already None after setUp
        reset_bridge()  # second call must not raise

    def test_get_bridge_service_name(self):
        b = get_bridge(service_name="dof-test")
        self.assertEqual(b.service_name, "dof-test")

    def test_singleton_inactive_without_otel(self):
        b = get_bridge()
        self.assertFalse(b.is_active)


if __name__ == "__main__":
    unittest.main()
