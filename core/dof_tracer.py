"""
DOF Tracer — Sistema de Tracing Estructurado inspirado en Adaline.

Traces y Spans para observabilidad granular de operaciones LLM,
governance, Z3, sentinel, mesh y herramientas.

Persistencia en JSONL. Solo stdlib. Sin dependencias externas.
"""

import json
import os
import time
import uuid
import logging
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from typing import Any

logger = logging.getLogger("core.dof_tracer")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRACES_JSONL = os.path.join(BASE_DIR, "logs", "traces", "traces.jsonl")

# Tipos validos de span
VALID_SPAN_TYPES = {"llm", "governance", "z3", "sentinel", "mesh", "tool", "custom"}

# Metricas esperadas por tipo de span
SPAN_TYPE_METRICS = {
    "llm": ["tokens_in", "tokens_out", "model", "provider", "cost"],
    "governance": ["violations", "warnings", "score", "rules_checked"],
    "z3": ["theorems_checked", "proofs_generated", "verdict"],
    "sentinel": ["checks_run", "overall_score", "verdict"],
    "mesh": ["node_id", "latency_ms", "circuit_state"],
    "tool": ["tool_name", "success", "duration"],
}


def _short_uuid() -> str:
    """UUID corto de 8 caracteres."""
    return uuid.uuid4().hex[:8]


@dataclass
class Span:
    """Un span dentro de un trace."""
    span_id: str = field(default_factory=_short_uuid)
    trace_id: str = ""
    parent_span_id: str | None = None
    name: str = ""
    span_type: str = "custom"
    status: str = "running"
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    duration_ms: float | None = None
    input_data: dict = field(default_factory=dict)
    output_data: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
    events: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Trace:
    """Un trace completo con sus spans."""
    trace_id: str = field(default_factory=_short_uuid)
    name: str = ""
    status: str = "running"
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    total_duration_ms: float | None = None
    spans: list[Span] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    total_tokens: int = 0
    total_cost: float = 0.0
    governance_verdict: str | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["spans"] = [s.to_dict() for s in self.spans]
        return d


class DOFTracer:
    """Sistema de tracing estructurado para el DOF Mesh."""

    def __init__(self, storage_path: str | None = None):
        self._storage_path = storage_path or TRACES_JSONL
        self._traces: dict[str, Trace] = {}
        self._spans: dict[str, Span] = {}
        os.makedirs(os.path.dirname(self._storage_path), exist_ok=True)

    def start_trace(self, name: str, metadata: dict | None = None) -> Trace:
        """Crea un trace nuevo."""
        trace = Trace(
            name=name,
            metadata=metadata or {},
        )
        self._traces[trace.trace_id] = trace
        logger.debug(f"Trace started: {trace.trace_id} ({name})")
        return trace

    def start_span(
        self,
        trace_id: str,
        name: str,
        span_type: str,
        input_data: dict | None = None,
        parent_span_id: str | None = None,
    ) -> Span:
        """Crea un span dentro de un trace."""
        trace = self._traces.get(trace_id)
        if trace is None:
            raise ValueError(f"Trace no encontrado: {trace_id}")

        if span_type not in VALID_SPAN_TYPES:
            raise ValueError(
                f"Tipo de span invalido: {span_type}. "
                f"Validos: {VALID_SPAN_TYPES}"
            )

        span = Span(
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            name=name,
            span_type=span_type,
            input_data=input_data or {},
        )
        self._spans[span.span_id] = span
        trace.spans.append(span)
        logger.debug(f"Span started: {span.span_id} ({name}) in trace {trace_id}")
        return span

    def end_span(
        self,
        span_id: str,
        output_data: dict | None = None,
        status: str = "completed",
        metadata: dict | None = None,
    ) -> Span:
        """Cierra un span y calcula duration_ms."""
        span = self._spans.get(span_id)
        if span is None:
            raise ValueError(f"Span no encontrado: {span_id}")

        span.end_time = time.time()
        span.duration_ms = round((span.end_time - span.start_time) * 1000, 2)
        span.status = status
        if output_data:
            span.output_data = output_data
        if metadata:
            span.metadata.update(metadata)

        logger.debug(
            f"Span ended: {span.span_id} ({span.name}) "
            f"status={status} duration={span.duration_ms}ms"
        )
        return span

    def add_event(self, span_id: str, event_name: str, data: dict | None = None) -> None:
        """Agrega un evento intermedio al span."""
        span = self._spans.get(span_id)
        if span is None:
            raise ValueError(f"Span no encontrado: {span_id}")

        event = {
            "timestamp": time.time(),
            "name": event_name,
            "data": data or {},
        }
        span.events.append(event)
        logger.debug(f"Event added to span {span_id}: {event_name}")

    def end_trace(self, trace_id: str, status: str = "completed") -> Trace:
        """Cierra un trace, calcula totales y persiste en JSONL."""
        trace = self._traces.get(trace_id)
        if trace is None:
            raise ValueError(f"Trace no encontrado: {trace_id}")

        trace.end_time = time.time()
        trace.total_duration_ms = round(
            (trace.end_time - trace.start_time) * 1000, 2
        )
        trace.status = status

        # Agregar totales de tokens y costo desde spans
        total_tokens = 0
        total_cost = 0.0
        governance_verdict = None

        for span in trace.spans:
            # Auto-cerrar spans que quedaron running
            if span.status == "running":
                span.end_time = time.time()
                span.duration_ms = round(
                    (span.end_time - span.start_time) * 1000, 2
                )
                span.status = "completed"

            # Tokens de spans LLM
            if span.span_type == "llm":
                total_tokens += span.metadata.get("tokens_in", 0)
                total_tokens += span.metadata.get("tokens_out", 0)
                total_cost += span.metadata.get("cost", 0.0)

            # Governance verdict del ultimo span de governance
            if span.span_type == "governance":
                v = span.output_data.get("verdict") or span.metadata.get("verdict")
                if v:
                    governance_verdict = v

        trace.total_tokens = total_tokens
        trace.total_cost = round(total_cost, 6)
        trace.governance_verdict = governance_verdict

        # Persistir en JSONL
        self._persist_trace(trace)

        logger.info(
            f"Trace ended: {trace.trace_id} ({trace.name}) "
            f"status={status} duration={trace.total_duration_ms}ms "
            f"spans={len(trace.spans)} tokens={total_tokens}"
        )
        return trace

    def get_trace(self, trace_id: str) -> Trace:
        """Obtiene un trace por ID."""
        trace = self._traces.get(trace_id)
        if trace is None:
            raise ValueError(f"Trace no encontrado: {trace_id}")
        return trace

    def get_span(self, span_id: str) -> Span:
        """Obtiene un span por ID."""
        span = self._spans.get(span_id)
        if span is None:
            raise ValueError(f"Span no encontrado: {span_id}")
        return span

    def get_trace_summary(self, trace_id: str) -> dict:
        """Resumen del trace: spans por tipo, duracion, tokens, costo, governance."""
        trace = self.get_trace(trace_id)

        spans_by_type: dict[str, int] = {}
        for span in trace.spans:
            spans_by_type[span.span_type] = spans_by_type.get(span.span_type, 0) + 1

        failed_spans = sum(1 for s in trace.spans if s.status == "failed")
        completed_spans = sum(1 for s in trace.spans if s.status == "completed")

        return {
            "trace_id": trace.trace_id,
            "name": trace.name,
            "status": trace.status,
            "total_spans": len(trace.spans),
            "spans_by_type": spans_by_type,
            "completed_spans": completed_spans,
            "failed_spans": failed_spans,
            "total_duration_ms": trace.total_duration_ms,
            "total_tokens": trace.total_tokens,
            "total_cost": trace.total_cost,
            "governance_verdict": trace.governance_verdict,
        }

    def list_traces(self, limit: int = 50) -> list[Trace]:
        """Lista los traces mas recientes."""
        traces = list(self._traces.values())
        traces.sort(key=lambda t: t.start_time, reverse=True)
        return traces[:limit]

    @contextmanager
    def span(
        self,
        trace_id: str,
        name: str,
        span_type: str,
        input_data: dict | None = None,
        parent_span_id: str | None = None,
    ):
        """Context manager para spans — auto-cierra al salir."""
        s = self.start_span(
            trace_id=trace_id,
            name=name,
            span_type=span_type,
            input_data=input_data,
            parent_span_id=parent_span_id,
        )
        try:
            yield s
            self.end_span(s.span_id, output_data=s.output_data, status="completed")
        except Exception:
            self.end_span(s.span_id, output_data=s.output_data, status="failed")
            raise

    def _persist_trace(self, trace: Trace) -> None:
        """Persiste el trace en JSONL."""
        try:
            with open(self._storage_path, "a") as f:
                f.write(json.dumps(trace.to_dict(), default=str) + "\n")
        except Exception as e:
            logger.error(f"Error persistiendo trace {trace.trace_id}: {e}")
