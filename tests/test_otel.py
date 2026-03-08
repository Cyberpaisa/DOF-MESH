"""
Tests for core/otel_bridge.py — OpenTelemetry integration.

All tests run in no-op mode (no OTel endpoint configured).
Verifies zero-crash behavior and correct API surface.
"""

import os
import sys
import unittest

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.otel_bridge import (
    OTelBridge,
    SpanContext,
    LAYER_NAMES,
    METRIC_NAMES,
    get_bridge,
    reset_bridge,
)


class TestOTelBridgeOffline(unittest.TestCase):
    """Test OTelBridge creation without endpoint."""

    def test_otel_bridge_offline(self):
        """Bridge creates without crash when no endpoint is set."""
        env_backup = os.environ.pop("OTEL_EXPORTER_OTLP_ENDPOINT", None)
        try:
            bridge = OTelBridge(service_name="test-service")
            self.assertFalse(bridge.is_active)
        finally:
            if env_backup is not None:
                os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = env_backup

    def test_otel_bridge_noop(self):
        """All operations work as no-op when not active."""
        bridge = OTelBridge(service_name="test-noop")
        self.assertFalse(bridge.is_active)
        # These should not raise
        bridge.record_metric("dof.governance.latency", 12.5)
        bridge.flush()


class TestTraceLayer(unittest.TestCase):
    """Test trace_layer context manager."""

    def test_trace_layer_context_manager(self):
        """Context manager works as no-op without active OTel."""
        bridge = OTelBridge(service_name="test-trace")
        with bridge.trace_layer("dof.constitution") as span:
            self.assertIsInstance(span, SpanContext)
            self.assertEqual(span.layer_name, "dof.constitution")
            span.set_attribute("test_key", "test_value")
            span.set_status(True)

    def test_trace_layer_all_layers(self):
        """All 7 layer names work with trace_layer."""
        bridge = OTelBridge(service_name="test-layers")
        for layer_name in LAYER_NAMES:
            with bridge.trace_layer(layer_name) as span:
                self.assertEqual(span.layer_name, layer_name)
                span.set_status(True)


class TestRecordMetric(unittest.TestCase):
    """Test record_metric in no-op mode."""

    def test_record_metric_noop(self):
        """record_metric does not crash in no-op mode."""
        bridge = OTelBridge(service_name="test-metrics")
        for metric_name in METRIC_NAMES:
            bridge.record_metric(metric_name, 1.0, {"layer": "test"})

    def test_record_metric_with_attributes(self):
        """record_metric accepts attributes dict."""
        bridge = OTelBridge(service_name="test-attrs")
        bridge.record_metric("dof.governance.latency", 15.3, {
            "layer": "constitution",
            "status": "pass",
        })
        bridge.record_metric("dof.tokens.total", 500, {
            "provider": "groq",
            "model": "llama-3.3-70b",
        })


class TestFlush(unittest.TestCase):
    """Test flush in no-op mode."""

    def test_flush_noop(self):
        """flush does not crash in no-op mode."""
        bridge = OTelBridge(service_name="test-flush")
        bridge.flush()


class TestLayerNames(unittest.TestCase):
    """Test layer name constants."""

    def test_layer_names_correct(self):
        """All 7 governance layer names are present."""
        self.assertEqual(len(LAYER_NAMES), 7)
        expected = [
            "dof.constitution", "dof.ast", "dof.supervisor",
            "dof.z3", "dof.redblue", "dof.memory", "dof.signer",
        ]
        self.assertEqual(LAYER_NAMES, expected)

    def test_metric_names_correct(self):
        """All 5 metric names are present with correct types."""
        self.assertEqual(len(METRIC_NAMES), 5)
        self.assertEqual(METRIC_NAMES["dof.governance.latency"], "histogram")
        self.assertEqual(METRIC_NAMES["dof.governance.pass_rate"], "counter")
        self.assertEqual(METRIC_NAMES["dof.governance.fail_rate"], "counter")
        self.assertEqual(METRIC_NAMES["dof.tokens.total"], "counter")
        self.assertEqual(METRIC_NAMES["dof.tokens.cost"], "counter")


class TestSpanContext(unittest.TestCase):
    """Test SpanContext attributes."""

    def test_attributes_format(self):
        """SpanContext has correct fields."""
        ctx = SpanContext(layer_name="dof.ast", start_time=1000.0)
        self.assertEqual(ctx.layer_name, "dof.ast")
        self.assertEqual(ctx.start_time, 1000.0)
        self.assertIsNone(ctx._real_span)
        # set_attribute and set_status should not raise on no-op
        ctx.set_attribute("key", "value")
        ctx.set_status(True)
        ctx.set_status(False)


class TestSingleton(unittest.TestCase):
    """Test module-level singleton."""

    def test_get_bridge_returns_same_instance(self):
        """get_bridge returns singleton."""
        reset_bridge()
        b1 = get_bridge("test-singleton")
        b2 = get_bridge("test-singleton")
        self.assertIs(b1, b2)
        reset_bridge()

    def test_reset_bridge(self):
        """reset_bridge clears singleton."""
        b1 = get_bridge("test-reset")
        reset_bridge()
        b2 = get_bridge("test-reset")
        self.assertIsNot(b1, b2)
        reset_bridge()


class TestDOFIntegrationImport(unittest.TestCase):
    """Test imports from dof package."""

    def test_import_from_dof(self):
        """OTelBridge importable from dof package."""
        from dof import OTelBridge, LAYER_NAMES, METRIC_NAMES
        self.assertIsNotNone(OTelBridge)
        self.assertEqual(len(LAYER_NAMES), 7)
        self.assertEqual(len(METRIC_NAMES), 5)

    def test_import_from_dof_integrations(self):
        """OTelBridge importable from dof.integrations.otel."""
        from dof.integrations.otel import OTelBridge, get_bridge, reset_bridge
        self.assertIsNotNone(OTelBridge)
        self.assertIsNotNone(get_bridge)


class TestTokenTrackerIntegration(unittest.TestCase):
    """Test OTelBridge works alongside TokenTracker."""

    def test_integration_with_token_tracker(self):
        """TokenTracker and OTelBridge can coexist."""
        from core.observability import TokenTracker

        tracker = TokenTracker()
        bridge = OTelBridge(service_name="test-integration")

        # Simulate a call logged to both systems
        tracker.log_call("groq", "llama-3.3-70b", 500, 200, 1200.0, 0.001)

        # Bridge records metrics (no-op in test)
        bridge.record_metric("dof.tokens.total", 700, {"provider": "groq"})
        bridge.record_metric("dof.tokens.cost", 0.001, {"provider": "groq"})

        self.assertEqual(tracker.total_tokens(), 700)
        self.assertFalse(bridge.is_active)


if __name__ == "__main__":
    unittest.main()
