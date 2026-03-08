"""
DOF OpenTelemetry Integration — re-export from core.otel_bridge.

Usage:
    from dof.integrations.otel import OTelBridge

    bridge = OTelBridge(service_name="dof-governance")
    with bridge.trace_layer("dof.constitution") as span:
        ...
"""

from core.otel_bridge import (
    OTelBridge,
    SpanContext,
    LAYER_NAMES,
    METRIC_NAMES,
    get_bridge,
    reset_bridge,
)

__all__ = [
    "OTelBridge",
    "SpanContext",
    "LAYER_NAMES",
    "METRIC_NAMES",
    "get_bridge",
    "reset_bridge",
]
