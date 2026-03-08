"""
DOF Integrations — optional bridges to external observability systems.

Available integrations:
  - otel: OpenTelemetry (OTLP) tracing and metrics
"""

from core.otel_bridge import OTelBridge, LAYER_NAMES, METRIC_NAMES

__all__ = ["OTelBridge", "LAYER_NAMES", "METRIC_NAMES"]
