from __future__ import annotations
"""
Mesh Orchestrator — Sistema nervioso central del DOF Mesh Phase 9.

Coordina routing, circuit breaking, optimización de costos y auto-escalado
en un loop autónomo determinista. Todas las decisiones son observables via
JSONL — cero dependencia de LLM.

Arquitectura:
    MeshOrchestrator (singleton)
        ├── orchestrate(task)       — router + circuit breaker + cost optimizer
        ├── evaluate_scaling()      — metrics + auto_scaler → scale up/down
        ├── get_status()            — estado completo del sistema
        └── run(interval)           — loop autónomo que orquesta y escala

Dependencias internas:
    core.mesh_router_v2         → MeshRouterV2        (routing inteligente)
    core.mesh_circuit_breaker   → MeshCircuitBreaker   (fault tolerance)
    core.mesh_cost_optimizer    → CostOptimizer        (auditor financiero)
    core.mesh_metrics_collector → MeshMetricsCollector  (telemetría)
    core.mesh_auto_scaler       → MeshAutoScaler        (scaling decisions)

Logs: logs/mesh/orchestrator.jsonl
"""

import json
import logging
import threading
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from core.mesh_router_v2 import MeshRouterV2
from core.mesh_circuit_breaker import MeshCircuitBreaker, CircuitOpenError
from core.mesh_cost_optimizer import CostOptimizer
from core.mesh_metrics_collector import MeshMetricsCollector, MeshMetrics
from core.mesh_auto_scaler import MeshAutoScaler, ScaleEvent
from core.hyperion_bridge import HyperionBridge
from core.mesh_auto_provisioner import AutoProvisioner

logger = logging.getLogger("core.mesh_orchestrator")

# ═══════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════

BASE_DIR = Path(__file__).resolve().parent.parent
MESH_DIR = BASE_DIR / "logs" / "mesh"
ORCHESTRATOR_LOG = MESH_DIR / "orchestrator.jsonl"
INBOX_DIR = MESH_DIR / "inbox"

# Health thresholds for scaling decisions
HEALTH_CRITICAL = 0.4
HEALTH_DEGRADED = 0.8

# Queue depth thresholds (from Phase 9 spec)
QUEUE_DEPTH_HIGH = 50   # scale up beyond this
QUEUE_DEPTH_LOW = 5     # scale down below this

# Default SLA latency target (ms)
DEFAULT_SLA_MS = 5000.0

# Hysteresis weights (Phase 9 multivectorial)
W_QUEUE = 0.6
W_LATENCY = 0.4


# ═══════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════

@dataclass
class OrchestrationResult:
    """Result of a single task orchestration."""
    task_id: str
    task_type: str
    routed_node: str
    cost_node: str              # cheapest node per CostOptimizer
    selected_node: str          # final decision (router wins unless circuit open)
    circuit_state: str          # CLOSED | OPEN | HALF_OPEN
    success: bool
    error: str = ""
    latency_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class ScalingDecision:
    """Result of a scaling evaluation cycle."""
    queue_depth: int
    health_score: float
    avg_latency_ms: float
    demand_score: float         # D_net from Phase 9 spec
    action: str                 # scale_up | scale_down | hold
    scale_events: int           # number of ScaleEvents generated
    active_nodes: int
    total_nodes: int
    timestamp: float = field(default_factory=time.time)


# ═══════════════════════════════════════════════════════
# SINGLETON ORCHESTRATOR
# ═══════════════════════════════════════════════════════

class MeshOrchestrator:
    """
    Sistema nervioso central del DOF Mesh.

    Singleton — one instance per process, thread-safe.
    Integra router, circuit breaker, cost optimizer, metrics y auto-scaler
    en un pipeline unificado de orquestación.
    """

    _instance: Optional["MeshOrchestrator"] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(
        cls,
        mesh_dir: Optional[Path] = None,
        sla_ms: float = DEFAULT_SLA_MS,
    ) -> "MeshOrchestrator":
        with cls._lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                inst._initialized = False
                cls._instance = inst
        return cls._instance

    def __init__(
        self,
        mesh_dir: Optional[Path] = None,
        sla_ms: float = DEFAULT_SLA_MS,
    ) -> None:
        if self._initialized:  # type: ignore[has-type]
            return

        self._mesh_dir = Path(mesh_dir) if mesh_dir else MESH_DIR
        self._mesh_dir.mkdir(parents=True, exist_ok=True)
        self._log_file = self._mesh_dir / "orchestrator.jsonl"
        self._inbox_dir = self._mesh_dir / "inbox"
        (self._inbox_dir / "commander").mkdir(parents=True, exist_ok=True)
        self._sla_ms = sla_ms
        self._running = False
        self._io_lock = threading.Lock()

        # Counters
        self._total_orchestrated: int = 0
        self._total_successes: int = 0
        self._total_failures: int = 0
        self._total_scaling_cycles: int = 0

        # Initialize subsystems (singletons — safe to call repeatedly)
        self._router = MeshRouterV2(mesh_dir=self._mesh_dir)
        self._circuit_breaker = MeshCircuitBreaker()
        self._cost_optimizer = CostOptimizer()
        self._metrics_collector = MeshMetricsCollector(mesh_dir=self._mesh_dir)
        self._auto_scaler = MeshAutoScaler(mesh_dir=self._mesh_dir)

        # Hyperion Integration
        self._bridge = HyperionBridge()
        self._provisioner = AutoProvisioner(bridge=self._bridge)

        self._initialized = True
        logger.info(
            "MeshOrchestrator initialized — mesh_dir=%s sla=%.0fms",
            self._mesh_dir, self._sla_ms,
        )

    # ── Singleton management ─────────────────────────────

    @classmethod
    def reset(cls) -> None:
        """Reset singleton for testing."""
        with cls._lock:
            if cls._instance is not None:
                cls._instance._running = False
            cls._instance = None

    # ── Public counter properties (test-friendly aliases) ──

    @property
    def work_orders_processed(self) -> int:
        return self._total_orchestrated

    @work_orders_processed.setter
    def work_orders_processed(self, value: int) -> None:
        self._total_orchestrated = value

    @property
    def work_orders_completed(self) -> int:
        return self._total_successes

    @work_orders_completed.setter
    def work_orders_completed(self, value: int) -> None:
        self._total_successes = value

    @property
    def cycle_count(self) -> int:
        return self._total_scaling_cycles

    @cycle_count.setter
    def cycle_count(self, value: int) -> None:
        self._total_scaling_cycles = value

    # ── Inbox helpers ─────────────────────────────────────

    def _discover_work_orders(self) -> list:
        """Return list of (Path, dict) tuples for pending work orders in inbox."""
        results = []
        if not self._inbox_dir.exists():
            return results
        for json_file in sorted(self._inbox_dir.glob("**/*.json")):
            if json_file.stem.endswith("-RESPONSE") or json_file.stem.endswith("-FAILED"):
                continue
            try:
                data = json.loads(json_file.read_text(encoding="utf-8"))
                results.append((json_file, data))
            except (OSError, json.JSONDecodeError):
                pass
        return results

    def _save_response(self, order_file: Path, result) -> None:
        """Persist a completed response next to its work order file."""
        response_file = order_file.parent / f"{order_file.stem}-RESPONSE.json"
        payload = {
            "from_node": result.node_id,
            "msg_id": result.msg_id,
            "status": result.status,
            "response_text": result.response_text,
            "timestamp": time.time(),
        }
        if hasattr(result, "code") and result.code:
            payload["code"] = result.code
        try:
            response_file.write_text(
                json.dumps(payload, ensure_ascii=False), encoding="utf-8"
            )
        except OSError as exc:
            logger.error("Failed to write response file: %s", exc)

    def _save_failure(self, order_file: Path, result) -> None:
        """Persist a failure record next to its work order file."""
        failed_file = order_file.parent / f"{order_file.stem}-FAILED.json"
        payload = {
            "from_node": result.node_id,
            "msg_id": result.msg_id,
            "status": result.status,
            "error": getattr(result, "error", ""),
            "timestamp": time.time(),
        }
        try:
            failed_file.write_text(
                json.dumps(payload, ensure_ascii=False), encoding="utf-8"
            )
        except OSError as exc:
            logger.error("Failed to write failure file: %s", exc)

    # ── JSONL logging ────────────────────────────────────

    def _log(self, event_type: str, data: dict) -> None:
        """Append a structured event to orchestrator.jsonl."""
        record = {
            "event": event_type,
            "timestamp": time.time(),
            **data,
        }
        line = json.dumps(record, ensure_ascii=False)
        with self._io_lock:
            try:
                with self._log_file.open("a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
            except OSError as exc:
                logger.error("Failed to write orchestrator log: %s", exc)

    # ── Core orchestration ───────────────────────────────

    def orchestrate(self, task: dict) -> OrchestrationResult:
        """
        Orchestrate a single task through the mesh pipeline.

        Pipeline:
            1. Extract task_type and context_length from task dict
            2. Router selects best node by specialty + load + latency
            3. CostOptimizer suggests cheapest viable node
            4. Circuit breaker guards the selected node
            5. If circuit open → fallback to cost optimizer's choice
            6. Log everything to orchestrator.jsonl

        Args:
            task: dict with at least 'task_type'. Optional: 'task_id',
                  'context_length', 'payload'.

        Returns:
            OrchestrationResult with routing decision and outcome.
        """
        task_id = task.get("task_id", f"task-{int(time.time() * 1000)}")
        task_type = task.get("task_type") or task.get("type", "general")
        context_length = int(task.get("context_length", 4096))

        # Step 1: Router decision (specialty + load + latency)
        routed_node = "unknown"
        try:
            routed_node = self._router.route(task_type)
        except (ValueError, RuntimeError) as exc:
            logger.warning("Router failed for task_type=%s: %s", task_type, exc)

        # Step 2: Cost optimizer decision
        cost_node = self._cost_optimizer.get_cheapest_node(context_length, task_type)

        # Step 3: Select node — prefer router, fallback to cost optimizer
        selected_node = routed_node if routed_node != "unknown" else cost_node

        # Emergency Override: Token Conservation Protocol
        emergency_file = MESH_DIR / "EMERGENCY_MODE_v1.json"
        if emergency_file.exists():
            try:
                with open(emergency_file, "r") as f:
                    emergency = json.load(f)
                if emergency.get("status") == "ACTIVE":
                    # Force cheapest node to conserve tokens
                    if selected_node != cost_node:
                        logger.warning("EMERGENCY_MODE active: Overriding %s with cheapest node %s", selected_node, cost_node)
                        selected_node = cost_node
            except Exception:
                pass

        # Step 4: Check circuit breaker state
        circuit_state = self._circuit_breaker.get_state(selected_node)

        # Step 5: If primary circuit is open, fallback to cost optimizer's choice
        if circuit_state == "OPEN" and cost_node != selected_node:
            fallback_state = self._circuit_breaker.get_state(cost_node)
            if fallback_state != "OPEN":
                logger.info(
                    "Circuit OPEN for '%s', falling back to cost-optimal '%s'",
                    selected_node, cost_node,
                )
                selected_node = cost_node
                circuit_state = fallback_state

        # Step 6: Execute through circuit breaker (simulate dispatch)
        t0 = time.monotonic()
        success = True
        error_msg = ""

        try:
            self._circuit_breaker.call(
                selected_node,
                self._dispatch_task,
                task, selected_node,
            )
        except CircuitOpenError as exc:
            success = False
            error_msg = f"CircuitOpen: {exc}"
            logger.warning("Orchestration blocked by circuit breaker: %s", exc)
        except Exception as exc:
            success = False
            error_msg = str(exc)
            logger.error("Task dispatch failed: %s", exc)

        latency_ms = (time.monotonic() - t0) * 1000

        # Update router latency estimate
        if success:
            self._router.update_latency(selected_node, latency_ms)

        # Build result
        result = OrchestrationResult(
            task_id=task_id,
            task_type=task_type,
            routed_node=routed_node,
            cost_node=cost_node,
            selected_node=selected_node,
            circuit_state=circuit_state,
            success=success,
            error=error_msg,
            latency_ms=round(latency_ms, 2),
        )

        # Update counters
        self._total_orchestrated += 1
        if success:
            self._total_successes += 1
        else:
            self._total_failures += 1

        # Log
        self._log("orchestration", asdict(result))

        logger.debug(
            "orchestrate(%s) → node=%s success=%s latency=%.1fms",
            task_type, selected_node, success, latency_ms,
        )
        return result

    def _dispatch_task(self, task: dict, node_id: str) -> None:
        """
        Dispatch task to a mesh node via Hyperion (Distributed Sharded Queue).
        """
        task_id = task.get("task_id", "unknown")
        self._bridge.send_message(
            from_node="orchestrator",
            to_node=node_id,
            content=task,
            msg_type=task.get("msg_type", "task")
        )

        logger.debug("Dispatched task %s to node %s via Hyperion", task_id, node_id)

    # ── Scaling evaluation ───────────────────────────────

    def evaluate_scaling(self) -> ScalingDecision:
        """
        Evaluate whether the mesh needs to scale up or down.

        Uses the Phase 9 Hysteresis Multivectorial algorithm:
            D_net = W_QUEUE * (queue_depth / QUEUE_DEPTH_HIGH)
                  + W_LATENCY * (avg_latency / SLA)

            D_net > 1.0 → scale_up
            D_net < 0.2 → scale_down
            else        → hold

        Also delegates to MeshAutoScaler for per-node granular events.

        Returns:
            ScalingDecision with the action taken.
        """
        # Collect current metrics
        metrics: MeshMetrics = self._metrics_collector.collect()

        # Compute queue depth from inbox
        queue_depth = self._count_queue_depth()

        # Compute demand score (D_net)
        q_ratio = queue_depth / max(QUEUE_DEPTH_HIGH, 1)
        l_ratio = metrics.avg_latency_ms / max(self._sla_ms, 1)
        demand_score = round(W_QUEUE * q_ratio + W_LATENCY * l_ratio, 4)

        # Determine action
        if demand_score > 1.0 or metrics.health_score < HEALTH_CRITICAL:
            action = "scale_up"
        elif demand_score < 0.2 and metrics.health_score >= HEALTH_DEGRADED:
            action = "scale_down"
        else:
            action = "hold"

        # Delegate to auto-scaler for per-node events
        scale_events: list[ScaleEvent] = self._auto_scaler.check_load()

        # Act on recommendations via Provisioner
        for evt in scale_events:
            self._provisioner.handle_scale_event(evt)

        decision = ScalingDecision(
            queue_depth=queue_depth,
            health_score=metrics.health_score,
            avg_latency_ms=round(metrics.avg_latency_ms, 2),
            demand_score=demand_score,
            action=action,
            scale_events=len(scale_events),
            active_nodes=metrics.active_nodes,
            total_nodes=metrics.node_count,
        )

        self._total_scaling_cycles += 1

        # Log
        self._log("scaling_evaluation", asdict(decision))

        if action != "hold":
            logger.info(
                "Scaling decision: %s (D_net=%.4f health=%.4f queue=%d)",
                action, demand_score, metrics.health_score, queue_depth,
            )
        else:
            logger.debug(
                "Scaling hold (D_net=%.4f health=%.4f queue=%d)",
                demand_score, metrics.health_score, queue_depth,
            )

        return decision

    def _count_queue_depth(self) -> int:
        """Count pending tasks via HyperionBridge."""
        return self._bridge.queue_size()

    # ── Status ───────────────────────────────────────────

    def get_status(self) -> dict:
        """
        Return complete system status.

        Aggregates data from all subsystems into a single dict.
        """
        metrics_summary = self._metrics_collector.get_summary()
        router_stats = self._router.get_stats()
        scale_recs = self._auto_scaler.get_recommendations()
        queue_depth = self._count_queue_depth()

        processed = self._total_orchestrated
        completed = self._total_successes
        completion_rate = round(completed / max(processed, 1), 4)

        return {
            # Flat keys for test compatibility
            "work_orders_processed": processed,
            "work_orders_completed": completed,
            "completion_rate": completion_rate,
            # Full nested structure
            "orchestrator": {
                "total_orchestrated": processed,
                "total_successes": completed,
                "total_failures": self._total_failures,
                "success_rate": completion_rate,
                "scaling_cycles": self._total_scaling_cycles,
                "running": self._running,
                "sla_ms": self._sla_ms,
            },
            "mesh": metrics_summary,
            "routing": router_stats,
            "scaling": {
                "queue_depth": queue_depth,
                "active_recommendations": scale_recs,
                "recommendation_count": len(scale_recs),
            },
            "timestamp": time.time(),
        }

    # ── Autonomous loop ──────────────────────────────────

    def run(self, interval: int = 30, max_cycles: int = 0) -> None:
        """
        Autonomous orchestration loop.

        Every `interval` seconds:
            1. Evaluate scaling needs
            2. Process any pending tasks in the inbox
            3. Log cycle summary

        Args:
            interval: seconds between cycles (default 30).
            max_cycles: stop after N cycles (0 = infinite).
        """
        self._running = True
        cycle = 0

        logger.info(
            "MeshOrchestrator loop started — interval=%ds max_cycles=%s",
            interval, max_cycles or "∞",
        )

        self._log("loop_start", {
            "interval": interval,
            "max_cycles": max_cycles,
        })

        try:
            while self._running:
                cycle += 1
                t0 = time.monotonic()

                # Step 1: Evaluate scaling
                decision = self.evaluate_scaling()

                # Step 2: Process pending inbox tasks
                tasks_processed = self._process_pending_tasks()

                elapsed_ms = (time.monotonic() - t0) * 1000

                self._log("cycle_complete", {
                    "cycle": cycle,
                    "scaling_action": decision.action,
                    "tasks_processed": tasks_processed,
                    "elapsed_ms": round(elapsed_ms, 2),
                })

                logger.debug(
                    "Cycle %d complete — action=%s processed=%d elapsed=%.1fms",
                    cycle, decision.action, tasks_processed, elapsed_ms,
                )

                # Check max_cycles
                if max_cycles > 0 and cycle >= max_cycles:
                    logger.info("Reached max_cycles=%d, stopping.", max_cycles)
                    break

                # Sleep until next cycle
                time.sleep(interval)

        except KeyboardInterrupt:
            logger.info("MeshOrchestrator loop interrupted by user.")
        finally:
            self._running = False
            self._log("loop_stop", {"cycles_completed": cycle})
            logger.info("MeshOrchestrator loop stopped after %d cycles.", cycle)

    def stop(self) -> None:
        """Signal the run loop to stop after the current cycle."""
        self._running = False
        logger.info("MeshOrchestrator stop requested.")

    def _process_pending_tasks(self) -> int:
        """
        Scan inbox directories for queued tasks and orchestrate them.

        Returns the number of tasks processed this cycle.
        """
        if not self._inbox_dir.exists():
            return 0

        processed = 0
        for task_file in self._inbox_dir.glob("**/task-*.json"):
            try:
                with task_file.open("r", encoding="utf-8") as fh:
                    task_data = json.load(fh)

                # Only process tasks with status=queued
                if task_data.get("status") != "queued":
                    continue

                # Mark as processing to avoid re-processing
                task_data["status"] = "processing"
                with task_file.open("w", encoding="utf-8") as fh:
                    json.dump(task_data, fh, indent=2, ensure_ascii=False)

                self.orchestrate(task_data)
                processed += 1

            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Skipping malformed task file %s: %s", task_file, exc)

        return processed


# ═══════════════════════════════════════════════════════
# DEMO
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    import tempfile

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s — %(message)s",
    )

    with tempfile.TemporaryDirectory() as tmp:
        mesh_dir = Path(tmp)

        # Create synthetic nodes.json
        nodes = {
            "architect":  {"role": "architect",  "status": "active", "active_tasks": 3, "context_window": 128000},
            "researcher": {"role": "researcher", "status": "active", "active_tasks": 1, "context_window": 32000},
            "guardian":   {"role": "security",   "status": "active", "active_tasks": 0, "context_window": 32000},
            "narrator":   {"role": "narrator",   "status": "idle",   "active_tasks": 0, "context_window": 16000},
            "local-agi-m4max": {"role": "coder", "status": "active", "active_tasks": 2, "context_window": 32000, "provider": "ollama"},
        }
        nodes_file = mesh_dir / "nodes.json"
        nodes_file.write_text(json.dumps(nodes), encoding="utf-8")

        # Reset singletons for clean demo
        MeshOrchestrator.reset()
        MeshRouterV2._instance = None
        MeshCircuitBreaker._instance = None
        CostOptimizer._instance = None
        MeshMetricsCollector._instance = None
        MeshAutoScaler._instance = None

        orch = MeshOrchestrator(mesh_dir=mesh_dir, sla_ms=3000.0)

        # ── Orchestrate several tasks ──
        print("\n── orchestrate() ────────────────────────────")
        for task_type in ["code", "security", "research", "docs"]:
            result = orch.orchestrate({
                "task_type": task_type,
                "context_length": 8000,
                "payload": f"Demo {task_type} task",
            })
            print(
                f"  {task_type:12s} → node={result.selected_node:12s} "
                f"circuit={result.circuit_state:9s} "
                f"ok={result.success}  {result.latency_ms:.1f}ms"
            )

        # ── Evaluate scaling ──
        print("\n── evaluate_scaling() ───────────────────────")
        decision = orch.evaluate_scaling()
        print(f"  action       : {decision.action}")
        print(f"  demand_score : {decision.demand_score}")
        print(f"  health_score : {decision.health_score}")
        print(f"  queue_depth  : {decision.queue_depth}")
        print(f"  active_nodes : {decision.active_nodes}/{decision.total_nodes}")

        # ── Full status ──
        print("\n── get_status() ─────────────────────────────")
        status = orch.get_status()
        print(f"  orchestrated : {status['orchestrator']['total_orchestrated']}")
        print(f"  success_rate : {status['orchestrator']['success_rate']}")
        print(f"  mesh health  : {status['mesh'].get('health_score', 'N/A')}")
        print(f"  total_routes : {status['routing']['total_routes']}")

        # ── Run loop (2 cycles) ──
        print("\n── run(interval=1, max_cycles=2) ────────────")
        orch.run(interval=1, max_cycles=2)

        # Show log
        log_file = mesh_dir / "orchestrator.jsonl"
        if log_file.exists():
            lines = log_file.read_text(encoding="utf-8").strip().splitlines()
            print(f"\n── orchestrator.jsonl ({len(lines)} entries) ──")
            for line in lines[:5]:
                entry = json.loads(line)
                print(f"  [{entry['event']:22s}] ts={entry['timestamp']:.2f}")
            if len(lines) > 5:
                print(f"  ... and {len(lines) - 5} more entries")
