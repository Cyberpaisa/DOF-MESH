"""
OpenTelemetry Bridge — optional OTLP tracing for DOF governance layers.

Completely optional: zero overhead when OpenTelemetry is not installed.
Activates only when both conditions are met:
  1. opentelemetry-api + opentelemetry-sdk are installed
  2. OTEL_EXPORTER_OTLP_ENDPOINT is set in environment

Compatible with Jaeger, Grafana Tempo, Datadog, any OTLP collector.

Usage:
    from core.otel_bridge import OTelBridge

    bridge = OTelBridge(service_name="dof-governance")
    with bridge.trace_layer("dof.constitution") as span:
        result = enforcer.check(text)
        span.set_status(result.passed)

    bridge.record_metric("dof.governance.latency", 12.5, {"layer": "constitution"})
    bridge.flush()
"""

import os
import time
import logging
from contextlib import contextmanager
from dataclasses import dataclass

logger = logging.getLogger("core.otel_bridge")

# Valid governance layer span names
LAYER_NAMES = [
    "dof.constitution",
    "dof.ast",
    "dof.supervisor",
    "dof.z3",
    "dof.redblue",
    "dof.memory",
    "dof.signer",
]

# Metric definitions
METRIC_NAMES = {
    "dof.governance.latency": "histogram",
    "dof.governance.pass_rate": "counter",
    "dof.governance.fail_rate": "counter",
    "dof.tokens.total": "counter",
    "dof.tokens.cost": "counter",
}

# Try importing OpenTelemetry
_OTEL_AVAILABLE = False
_trace_api = None
_metrics_api = None

try:
    from opentelemetry import trace as _trace_api
    from opentelemetry import metrics as _metrics_api
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource
    _OTEL_AVAILABLE = True
except ImportError:
    pass


@dataclass
class SpanContext:
    """Lightweight span wrapper — real or no-op."""
    layer_name: str
    start_time: float
    _real_span: object = None

    def set_attribute(self, key: str, value) -> None:
        """Set an attribute on the span."""
        if self._real_span is not None:
            self._real_span.set_attribute(key, value)

    def set_status(self, passed: bool) -> None:
        """Set pass/fail status on the span."""
        self.set_attribute("dof.status", "pass" if passed else "fail")
        if self._real_span is not None and _OTEL_AVAILABLE:
            from opentelemetry.trace import StatusCode
            status = StatusCode.OK if passed else StatusCode.ERROR
            self._real_span.set_status(status)


class OTelBridge:
    """OpenTelemetry bridge for DOF governance layers.

    No-op when OpenTelemetry is not installed or no endpoint is configured.
    """

    def __init__(self, service_name: str = "dof-governance", endpoint: str | None = None):
        self.service_name = service_name
        self.endpoint = endpoint or os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
        self._active = False
        self._tracer = None
        self._meter = None
        self._histograms = {}
        self._counters = {}
        self._tracer_provider = None
        self._meter_provider = None

        if not _OTEL_AVAILABLE:
            logger.info("OpenTelemetry not installed — OTelBridge in no-op mode")
            return

        if not self.endpoint:
            logger.info("OTEL_EXPORTER_OTLP_ENDPOINT not set — OTelBridge in offline mode")
            return

        try:
            self._setup_otel()
            self._active = True
            logger.info(f"OTelBridge active: {self.service_name} → {self.endpoint}")
        except Exception as e:
            logger.warning(f"OTelBridge setup failed: {e} — falling back to no-op")

    def _setup_otel(self) -> None:
        """Initialize OpenTelemetry tracer and meter."""
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter

        resource = Resource.create({"service.name": self.service_name})

        # Tracer
        self._tracer_provider = TracerProvider(resource=resource)
        span_exporter = OTLPSpanExporter(endpoint=self.endpoint)
        self._tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
        self._tracer = self._tracer_provider.get_tracer("dof")

        # Meter
        metric_exporter = OTLPMetricExporter(endpoint=self.endpoint)
        reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=5000)
        self._meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
        self._meter = self._meter_provider.get_meter("dof")

        # Create instruments
        self._histograms["dof.governance.latency"] = self._meter.create_histogram(
            "dof.governance.latency",
            unit="ms",
            description="Governance layer latency in milliseconds",
        )
        for counter_name in ["dof.governance.pass_rate", "dof.governance.fail_rate",
                             "dof.tokens.total", "dof.tokens.cost"]:
            self._counters[counter_name] = self._meter.create_counter(
                counter_name,
                description=f"DOF metric: {counter_name}",
            )

    @property
    def is_active(self) -> bool:
        """Whether OTel is fully configured and active."""
        return self._active

    @contextmanager
    def trace_layer(self, layer_name: str):
        """Context manager that creates a span for a governance layer.

        Args:
            layer_name: One of LAYER_NAMES (e.g., "dof.constitution")

        Yields:
            SpanContext with set_attribute() and set_status() methods.
        """
        start = time.time()

        if self._active and self._tracer is not None:
            with self._tracer.start_as_current_span(layer_name) as real_span:
                real_span.set_attribute("dof.layer", layer_name)
                ctx = SpanContext(
                    layer_name=layer_name,
                    start_time=start,
                    _real_span=real_span,
                )
                try:
                    yield ctx
                finally:
                    duration_ms = (time.time() - start) * 1000
                    real_span.set_attribute("dof.duration_ms", round(duration_ms, 2))
        else:
            ctx = SpanContext(layer_name=layer_name, start_time=start)
            yield ctx

    def record_metric(self, name: str, value: float, attributes: dict | None = None) -> None:
        """Record a metric value.

        Args:
            name: Metric name (one of METRIC_NAMES keys)
            value: Metric value
            attributes: Optional dict of attributes
        """
        if not self._active:
            return

        attrs = attributes or {}
        metric_type = METRIC_NAMES.get(name)

        if metric_type == "histogram" and name in self._histograms:
            self._histograms[name].record(value, attrs)
        elif metric_type == "counter" and name in self._counters:
            self._counters[name].add(value, attrs)

    def flush(self) -> None:
        """Force export of all pending spans and metrics."""
        if not self._active:
            return

        try:
            if self._tracer_provider is not None:
                self._tracer_provider.force_flush()
            if self._meter_provider is not None:
                self._meter_provider.force_flush()
        except Exception as e:
            logger.warning(f"OTelBridge flush error: {e}")


# Module-level singleton (lazy)
_bridge_instance: OTelBridge | None = None


def get_bridge(service_name: str = "dof-governance") -> OTelBridge:
    """Get or create the module-level OTelBridge singleton."""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = OTelBridge(service_name=service_name)
    return _bridge_instance


def reset_bridge() -> None:
    """Reset the singleton (for testing)."""
    global _bridge_instance
    if _bridge_instance is not None:
        _bridge_instance.flush()
    _bridge_instance = None
