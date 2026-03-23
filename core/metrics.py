"""
Structured JSONL Metrics Logger — FASE 0.

Logs execution events with rotation at 10MB.
Format: {timestamp, event, run_id, agent, provider, latency_ms, status, meta}
"""

import os
import json
import time
import logging
from typing import Any

logger = logging.getLogger("core.metrics")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METRICS_DIR = os.path.join(BASE_DIR, "logs", "metrics")
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


class MetricsLogger:
    """Structured JSONL logger with rotation."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        os.makedirs(METRICS_DIR, exist_ok=True)
        self._file = os.path.join(METRICS_DIR, "events.jsonl")

    def log(self, event: str, run_id: str = "", agent: str = "",
            provider: str = "", latency_ms: float = 0.0,
            status: str = "", meta: dict[str, Any] | None = None):
        """Log a structured event."""
        entry = {
            "ts": time.time(),
            "iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "event": event,
            "run_id": run_id,
            "agent": agent,
            "provider": provider,
            "latency_ms": round(latency_ms, 1),
            "status": status,
        }
        if meta:
            entry["meta"] = meta

        self._write(entry)

    def log_crew_start(self, run_id: str, crew_name: str, input_text: str = ""):
        """Log crew execution start."""
        self.log("crew_start", run_id=run_id, meta={
            "crew": crew_name,
            "input_len": len(input_text),
            "input_preview": input_text[:200],
        })

    def log_crew_end(self, run_id: str, crew_name: str, status: str = "ok",
                     total_ms: float = 0.0, output_len: int = 0):
        """Log crew execution end."""
        self.log("crew_end", run_id=run_id, status=status,
                 latency_ms=total_ms, meta={
                     "crew": crew_name,
                     "output_len": output_len,
                 })

    def log_agent_step(self, run_id: str, agent: str, provider: str,
                       latency_ms: float, status: str, attempt: int = 1):
        """Log individual agent step."""
        self.log("agent_step", run_id=run_id, agent=agent,
                 provider=provider, latency_ms=latency_ms, status=status,
                 meta={"attempt": attempt})

    def log_provider_event(self, provider: str, event_type: str,
                           error: str = "", ttl: float = 0.0):
        """Log provider exhaustion/recovery."""
        self.log(f"provider_{event_type}", provider=provider, meta={
            "error": error[:200],
            "ttl_seconds": ttl,
        })

    def log_governance(self, run_id: str, passed: bool, score: float,
                       violations: list[str] | None = None):
        """Log governance check result."""
        self.log("governance_check", run_id=run_id,
                 status="pass" if passed else "fail",
                 meta={"score": score, "violations": violations or []})

    def log_supervisor(self, run_id: str, decision: str, scores: dict):
        """Log supervisor evaluation."""
        self.log("supervisor_eval", run_id=run_id, status=decision, meta=scores)

    def get_recent(self, n: int = 50) -> list[dict]:
        """Return last N events. Returns [] for n <= 0."""
        if n <= 0:
            return []
        if not os.path.exists(self._file):
            return []
        try:
            with open(self._file) as f:
                lines = f.readlines()
            return [json.loads(line) for line in lines[-n:]]
        except Exception:
            return []

    def get_stats(self) -> dict:
        """Return basic stats from logged events."""
        events = self.get_recent(500)
        if not events:
            return {"total_events": 0}

        crews = [e for e in events if e["event"] == "crew_end"]
        steps = [e for e in events if e["event"] == "agent_step"]

        return {
            "total_events": len(events),
            "crews_completed": sum(1 for c in crews if c.get("status") == "ok"),
            "crews_failed": sum(1 for c in crews if c.get("status") != "ok"),
            "avg_crew_latency_ms": (
                sum(c.get("latency_ms", 0) for c in crews) / len(crews)
                if crews else 0
            ),
            "total_agent_steps": len(steps),
            "provider_exhaustions": sum(
                1 for e in events if e["event"] == "provider_exhausted"
            ),
        }

    def _write(self, entry: dict):
        """Write entry with rotation check."""
        self._rotate_if_needed()
        try:
            with open(self._file, "a") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception as e:
            logger.error(f"Metrics write error: {e}")

    def _rotate_if_needed(self):
        """Rotate log file if > 10MB."""
        if not os.path.exists(self._file):
            return
        try:
            size = os.path.getsize(self._file)
            if size > MAX_FILE_SIZE:
                rotated = self._file + f".{int(time.time())}"
                os.rename(self._file, rotated)
                logger.info(f"Metrics rotated: {rotated} ({size / 1024 / 1024:.1f}MB)")
        except Exception as e:
            logger.error(f"Metrics rotation error: {e}")
