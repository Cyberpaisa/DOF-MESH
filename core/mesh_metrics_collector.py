"""
Mesh Metrics Collector — Recolector de Métricas para DOF Mesh.

Hace snapshot del estado actual de la red y expone las métricas en
tres formatos: dict legible, Prometheus text y JSONL histórico.

Arquitectura:
    MeshMetricsCollector (singleton)
        ├── collect()            — snapshot instantáneo (nodes + messages + events)
        ├── get_summary()        — dict human-readable
        ├── export_prometheus()  — texto Prometheus exposition format
        └── get_history(minutes) — snapshots filtrados de metrics_history.jsonl

Persistencia: logs/mesh/metrics_history.jsonl (un registro por collect()).
"""

import json
import logging
import threading
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

logger = logging.getLogger("core.mesh_metrics_collector")

# ═══════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════


@dataclass
class MeshMetrics:
    """Snapshot of DOF Mesh state at a given instant."""
    timestamp: float
    node_count: int
    active_nodes: int
    total_messages: int
    events_per_minute: float
    health_score: float          # 0.0 – 1.0 (ratio active/total, 1.0 if no nodes)
    avg_latency_ms: float = 0.0  # average latency across nodes


# ═══════════════════════════════════════════════════════
# METRICS COLLECTOR
# ═══════════════════════════════════════════════════════


class MeshMetricsCollector:
    """
    Singleton metrics collector for DOF Mesh.

    Sources:
        logs/mesh/nodes.json        — node count, active count, health proxy
        logs/mesh/messages.jsonl    — total messages, messages/min rate
        logs/mesh/mesh_events.jsonl — event type distribution
    """

    _instance: Optional["MeshMetricsCollector"] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(
        cls,
        log_dir: Optional[Path] = None,
        history_window: int = 1440,
        mesh_dir: Optional[Path] = None,  # alias for log_dir
    ) -> "MeshMetricsCollector":
        with cls._lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                inst._initialized = False
                cls._instance = inst
        return cls._instance

    def __init__(
        self,
        log_dir: Optional[Path] = None,
        history_window: int = 1440,
        mesh_dir: Optional[Path] = None,  # alias for log_dir
    ) -> None:
        if self._initialized:  # type: ignore[has-type]
            return
        self._log_dir: Path = Path(log_dir or mesh_dir or "logs/mesh")
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._nodes_file: Path = self._log_dir / "nodes.json"
        self._messages_file: Path = self._log_dir / "messages.jsonl"
        self._events_file: Path = self._log_dir / "mesh_events.jsonl"
        self._history_file: Path = self._log_dir / "metrics_history.jsonl"
        self._history_window = history_window
        self._initialized = True
        logger.info("MeshMetricsCollector initialized — log_dir=%s", self._log_dir)

    # ── internal helpers ──────────────────────────────────────────────────

    def _load_nodes(self) -> dict:
        """Return nodes dict or {} on error."""
        if not self._nodes_file.exists():
            return {}
        try:
            with self._nodes_file.open("r", encoding="utf-8") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("nodes.json read error: %s", exc)
            return {}

    def _read_jsonl_lines(self, path: Path) -> list[dict]:
        """Read all valid JSONL lines from path; skip malformed lines."""
        if not path.exists():
            return []
        records: list[dict] = []
        try:
            with path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        except OSError as exc:
            logger.warning("JSONL read error (%s): %s", path.name, exc)
        return records

    def _compute_events_per_minute(self, events: list[dict], window_seconds: int = 60) -> float:
        """Count events in the last window_seconds and normalise to per-minute."""
        if not events:
            return 0.0
        cutoff = time.time() - window_seconds
        def _ts(e):
            try:
                return float(e.get("timestamp", 0))
            except (TypeError, ValueError):
                return 0.0
        recent = sum(1 for e in events if _ts(e) >= cutoff)
        return round(recent * (60 / window_seconds), 3)

    def _compute_health_score(self, nodes: dict) -> float:
        """Ratio of active nodes to total; nodes in error reduce score."""
        if not nodes:
            return 1.0
        active = sum(
            1 for n in nodes.values()
            if str(n.get("status", "")) == "active"
        )
        error = sum(
            1 for n in nodes.values()
            if str(n.get("status", "")) == "error"
        )
        total = len(nodes)
        # Each error node penalises twice
        raw = (active - error) / total
        return round(max(0.0, min(1.0, raw)), 4)

    def _append_history(self, metrics: MeshMetrics) -> None:
        """Append snapshot to metrics_history.jsonl."""
        record = asdict(metrics)
        try:
            with self._history_file.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record) + "\n")
        except OSError as exc:
            logger.error("Failed to write metrics history: %s", exc)

    # ── public API ────────────────────────────────────────────────────────

    def collect(self) -> MeshMetrics:
        """
        Snapshot the current mesh state.

        Reads nodes.json, messages.jsonl and mesh_events.jsonl, builds a
        MeshMetrics dataclass and persists it to metrics_history.jsonl.
        """
        nodes = self._load_nodes()
        messages = self._read_jsonl_lines(self._messages_file)
        events = self._read_jsonl_lines(self._events_file)

        node_count = len(nodes)
        active_nodes = sum(
            1 for n in nodes.values()
            if str(n.get("status", "")) == "active"
        )
        total_messages = len(messages)
        events_per_minute = self._compute_events_per_minute(events)
        health_score = self._compute_health_score(nodes)
        latencies = [float(n.get("avg_latency_ms", 0)) for n in nodes.values() if n.get("avg_latency_ms")]
        avg_latency_ms = sum(latencies) / len(latencies) if latencies else 0.0

        metrics = MeshMetrics(
            timestamp=time.time(),
            node_count=node_count,
            active_nodes=active_nodes,
            total_messages=total_messages,
            events_per_minute=events_per_minute,
            health_score=health_score,
            avg_latency_ms=avg_latency_ms,
        )

        self._append_history(metrics)
        logger.debug(
            "collect: nodes=%d active=%d msgs=%d epm=%.2f health=%.4f",
            node_count, active_nodes, total_messages, events_per_minute, health_score,
        )
        return metrics

    def get_summary(self) -> dict:
        """
        Return a human-readable summary dict of the latest collected metrics.

        Always calls collect() internally so the data is fresh.
        """
        m = self.collect()
        return {
            "timestamp_iso": time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime(m.timestamp)
            ),
            "nodes": {
                "total": m.node_count,
                "active": m.active_nodes,
                "inactive": m.node_count - m.active_nodes,
            },
            "messages": {
                "total": m.total_messages,
                "events_per_minute": m.events_per_minute,
            },
            "health_score": m.health_score,
            "status": "healthy" if m.health_score >= 0.8 else (
                "degraded" if m.health_score >= 0.4 else "critical"
            ),
        }

    def export_prometheus(self) -> str:
        """
        Export the latest metrics in Prometheus exposition text format.

        Calls collect() so the data is always fresh.

        Example output:
            # HELP dof_mesh_node_count Total nodes registered in the mesh
            # TYPE dof_mesh_node_count gauge
            dof_mesh_node_count 5
            ...
        """
        m = self.collect()
        lines: list[str] = []

        def _metric(name: str, help_text: str, mtype: str, value: float) -> None:
            lines.append(f"# HELP {name} {help_text}")
            lines.append(f"# TYPE {name} {mtype}")
            lines.append(f"{name} {value}")

        _metric(
            "dof_mesh_node_count",
            "Total nodes registered in the mesh",
            "gauge",
            m.node_count,
        )
        _metric(
            "dof_mesh_active_nodes",
            "Nodes currently in active status",
            "gauge",
            m.active_nodes,
        )
        _metric(
            "dof_mesh_total_messages",
            "Total messages processed across all nodes",
            "counter",
            m.total_messages,
        )
        _metric(
            "dof_mesh_events_per_minute",
            "Mesh events rate in the last 60 seconds",
            "gauge",
            m.events_per_minute,
        )
        _metric(
            "dof_mesh_health_score",
            "Mesh health score from 0.0 (critical) to 1.0 (perfect)",
            "gauge",
            m.health_score,
        )
        _metric(
            "dof_mesh_collect_timestamp",
            "Unix timestamp of the last metrics collection",
            "gauge",
            m.timestamp,
        )
        return "\n".join(lines) + "\n"

    def get_history(self, minutes: int = 60) -> list[MeshMetrics]:
        """
        Return historical MeshMetrics snapshots from the last `minutes` minutes.

        Reads metrics_history.jsonl and filters by timestamp.
        Returns entries sorted oldest-first.
        """
        cutoff = time.time() - (minutes * 60)
        records = self._read_jsonl_lines(self._history_file)
        result: list[MeshMetrics] = []
        for rec in records:
            try:
                ts = float(rec["timestamp"])
                if ts >= cutoff:
                    result.append(
                        MeshMetrics(
                            timestamp=ts,
                            node_count=int(rec.get("node_count", 0)),
                            active_nodes=int(rec.get("active_nodes", 0)),
                            total_messages=int(rec.get("total_messages", 0)),
                            events_per_minute=float(rec.get("events_per_minute", 0.0)),
                            health_score=float(rec.get("health_score", 1.0)),
                        )
                    )
            except (KeyError, ValueError, TypeError) as exc:
                logger.debug("Skipping malformed history record: %s", exc)
        return result


# ═══════════════════════════════════════════════════════
# DEMO
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s — %(message)s")

    import tempfile

    now = time.time()

    with tempfile.TemporaryDirectory() as tmp:
        log_dir = Path(tmp)

        # Synthetic nodes.json
        (log_dir / "nodes.json").write_text(
            json.dumps({
                "architect":  {"status": "active",   "active_tasks": 3},
                "researcher": {"status": "active",   "active_tasks": 1},
                "guardian":   {"status": "idle",     "active_tasks": 0},
                "narrator":   {"status": "error",    "active_tasks": 0},
                "reviewer":   {"status": "spawning", "active_tasks": 0},
            }),
            encoding="utf-8",
        )

        # Synthetic messages.jsonl (10 messages)
        msgs_file = log_dir / "messages.jsonl"
        for i in range(10):
            msgs_file.open("a").write(
                json.dumps({"id": i, "from": "architect", "to": "researcher", "timestamp": now - i * 5}) + "\n"
            )

        # Synthetic mesh_events.jsonl (5 recent + 3 older than 60s)
        evts_file = log_dir / "mesh_events.jsonl"
        for i in range(5):
            evts_file.open("a").write(
                json.dumps({"event": "node_spawned", "timestamp": now - i * 10}) + "\n"
            )
        for i in range(3):
            evts_file.open("a").write(
                json.dumps({"event": "node_idle", "timestamp": now - 120 - i * 10}) + "\n"
            )

        collector = MeshMetricsCollector(log_dir=log_dir)

        print("\n── collect() ────────────────────────────────")
        m = collector.collect()
        print(f"  node_count        : {m.node_count}")
        print(f"  active_nodes      : {m.active_nodes}")
        print(f"  total_messages    : {m.total_messages}")
        print(f"  events_per_minute : {m.events_per_minute}")
        print(f"  health_score      : {m.health_score}")

        print("\n── get_summary() ────────────────────────────")
        summary = collector.get_summary()
        for k, v in summary.items():
            print(f"  {k}: {v}")

        print("\n── export_prometheus() ──────────────────────")
        print(collector.export_prometheus())

        # Simulate a second collection after a brief pause
        time.sleep(0.05)
        collector.collect()

        print("── get_history(minutes=1) ───────────────────")
        history = collector.get_history(minutes=1)
        print(f"  {len(history)} snapshot(s) in last 60 seconds")
        for snap in history:
            ts_str = time.strftime("%H:%M:%S", time.gmtime(snap.timestamp))
            print(f"  [{ts_str}] nodes={snap.node_count} active={snap.active_nodes} health={snap.health_score}")


# Alias for test compatibility
MeshMetricsCollector.collect_metrics = MeshMetricsCollector.collect
