"""
Mesh Router V2 — Intelligent routing for DOF Mesh.

Selects the best node for a given task_type based on:
    - Specialty match (hard preference)
    - Active task count (load balancing)
    - EWMA latency (performance history)

Architecture:
    MeshRouterV2 (singleton)
        ├── reads node data from logs/mesh/nodes.json
        ├── maintains EWMA latency per node in memory
        └── logs every routing decision to logs/mesh/router_v2.jsonl

Usage:
    from core.mesh_router_v2 import MeshRouterV2

    router = MeshRouterV2()

    # Route a task
    node_id = router.route("security")

    # Report observed latency
    router.update_latency("guardian", 42.5)

    # Inspect stats
    stats = router.get_stats()
"""

import json
import logging
import threading
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

logger = logging.getLogger("core.mesh_router_v2")

# ═══════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════

BASE_DIR = Path(__file__).resolve().parent.parent
NODES_FILE = BASE_DIR / "logs" / "mesh" / "nodes.json"
ROUTER_LOG = BASE_DIR / "logs" / "mesh" / "router_v2.jsonl"

# EWMA smoothing factor (α): higher = more weight to recent samples
EWMA_ALPHA = 0.3

# Default assumed latency for nodes with no history (ms)
DEFAULT_LATENCY_MS = 100.0

# Score weights
WEIGHT_SPECIALTY = 1000.0   # strong bonus for specialty match
WEIGHT_LATENCY   = 1.0      # penalty per ms of latency
WEIGHT_ACTIVE    = 50.0     # penalty per active task

# Specialty keywords per task_type
SPECIALTY_MAP: dict[str, list[str]] = {
    "code":      ["code", "coder", "builder", "architect", "dev"],
    "test":      ["test", "qa", "guardian", "cerberus", "verifier"],
    "docs":      ["docs", "narrator", "writer", "documenter"],
    "research":  ["research", "researcher", "analyst", "scout"],
    "security":  ["security", "guardian", "icarus", "cerberus", "shield"],
    "consensus": ["consensus", "reviewer", "arbitrator", "judge"],
}


# ═══════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════

@dataclass
class RouteDecision:
    """Result of a single routing call."""
    task_type:    str
    selected_node: str
    score:        float
    specialty_match: bool
    active_tasks: int
    latency_ms:   float
    candidates:   int
    timestamp:    float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)


# ═══════════════════════════════════════════════════════
# SINGLETON ROUTER
# ═══════════════════════════════════════════════════════

class MeshRouterV2:
    """
    Intelligent router that selects the best mesh node for a given task_type.

    Singleton — one instance per process, thread-safe.
    """

    _instance: Optional["MeshRouterV2"] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls, mesh_dir: Optional[Path] = None) -> "MeshRouterV2":
        with cls._lock:
            if cls._instance is None:
                instance = super().__new__(cls)
                instance._init(mesh_dir)
                cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls, mesh_dir=None) -> "MeshRouterV2":
        """Factory method — returns the singleton (mesh_dir respected on first call)."""
        return cls(mesh_dir=Path(mesh_dir) if mesh_dir else None)

    def _init(self, mesh_dir: Optional[Path] = None) -> None:
        """Internal initializer (called once)."""
        self._latency: dict[str, float] = {}          # node_id → EWMA latency
        self._route_count: dict[str, int] = {}        # node_id → times routed to
        self._total_routes: int = 0
        self._io_lock = threading.Lock()
        # Allow test injection of a custom mesh directory
        self._nodes_file = (Path(mesh_dir) / "nodes.json") if mesh_dir else NODES_FILE
        self._router_log = (Path(mesh_dir) / "router_v2.jsonl") if mesh_dir else ROUTER_LOG
        self._router_log.parent.mkdir(parents=True, exist_ok=True)
        logger.info("MeshRouterV2 initialized — nodes_file=%s", self._nodes_file)

    # ── Public API ──────────────────────────────────────

    def route(self, task_type: str) -> str:
        """
        Return the node_id best suited for *task_type*.

        Selection criteria (lower score = worse; higher = better):
            score = specialty_bonus - latency_penalty - active_penalty

        Raises:
            RuntimeError: if no nodes are available.
        """
        nodes = self._load_nodes()
        if not nodes:
            raise ValueError("No nodes available in nodes.json")

        keywords = SPECIALTY_MAP.get(task_type.lower(), [task_type.lower()])
        best_node: Optional[str] = None
        best_score: float = float("-inf")
        best_meta: dict = {}

        for node_id, node in nodes.items():
            if node.get("status") in ("error", "dead"):
                continue

            specialty: str = str(node.get("role", node.get("specialty", ""))).lower()
            active_tasks: int = int(node.get("active_tasks", 0))
            latency: float = self._latency.get(node_id, DEFAULT_LATENCY_MS)

            specialty_match = any(kw in specialty for kw in keywords)
            specialty_bonus = WEIGHT_SPECIALTY if specialty_match else 0.0

            score = (
                specialty_bonus
                - WEIGHT_LATENCY * latency
                - WEIGHT_ACTIVE  * active_tasks
            )

            if score > best_score:
                best_score = score
                best_node  = node_id
                best_meta  = {
                    "specialty_match": specialty_match,
                    "active_tasks":    active_tasks,
                    "latency_ms":      latency,
                }

        if best_node is None:
            raise RuntimeError("All nodes are in error/dead state")

        decision = RouteDecision(
            task_type=task_type,
            selected_node=best_node,
            score=best_score,
            specialty_match=best_meta["specialty_match"],
            active_tasks=best_meta["active_tasks"],
            latency_ms=best_meta["latency_ms"],
            candidates=len(nodes),
        )
        self._record_decision(decision)

        self._route_count[best_node] = self._route_count.get(best_node, 0) + 1
        self._total_routes += 1

        logger.debug(
            "route(%s) → %s  score=%.1f  specialty=%s",
            task_type, best_node, best_score, best_meta["specialty_match"],
        )
        return best_node

    def update_latency(self, node_id: str, latency_ms: float) -> None:
        """
        Update the EWMA latency estimate for *node_id*.

        EWMA: new = α * sample + (1 - α) * old
        """
        if latency_ms < 0:
            raise ValueError(f"latency_ms must be non-negative, got {latency_ms}")

        old = self._latency.get(node_id, DEFAULT_LATENCY_MS)
        updated = EWMA_ALPHA * latency_ms + (1.0 - EWMA_ALPHA) * old
        self._latency[node_id] = updated
        logger.debug("update_latency(%s): %.1f → %.1f ms", node_id, old, updated)

    def get_stats(self) -> dict:
        """
        Return routing statistics snapshot.

        Returns:
            {
                "total_routes": int,
                "route_distribution": {node_id: count, ...},
                "latency_estimates": {node_id: ms, ...},
            }
        """
        return {
            "total_routes":       self._total_routes,
            "total_routed":       self._total_routes,  # alias
            "route_distribution": dict(self._route_count),
            "latency_estimates":  dict(self._latency),
        }

    # ── Internal helpers ────────────────────────────────

    def _load_nodes(self) -> dict:
        """Load nodes.json; return empty dict on any error."""
        if not self._nodes_file.exists():
            logger.warning("nodes.json not found at %s", self._nodes_file)
            return {}
        try:
            with open(self._nodes_file, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            # Support both {node_id: {...}} and {"nodes": {...}} layouts
            if isinstance(data, dict) and "nodes" in data:
                return data["nodes"]
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to load nodes.json: %s", exc)
            return {}

    def _record_decision(self, decision: RouteDecision) -> None:
        """Append routing decision to router_v2.jsonl (thread-safe)."""
        line = json.dumps(decision.to_dict(), ensure_ascii=False)
        with self._io_lock:
            try:
                with open(self._router_log, "a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
            except OSError as exc:
                logger.error("Failed to write router log: %s", exc)


# ═══════════════════════════════════════════════════════
# DEMO
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s  %(name)s  %(message)s")

    # Ensure a minimal nodes.json exists for the demo
    demo_nodes_path = NODES_FILE
    demo_nodes_path.parent.mkdir(parents=True, exist_ok=True)
    if not demo_nodes_path.exists():
        demo_data = {
            "commander":  {"role": "architect",  "status": "active", "active_tasks": 0},
            "guardian":   {"role": "security",   "status": "active", "active_tasks": 1},
            "researcher": {"role": "researcher", "status": "active", "active_tasks": 2},
            "narrator":   {"role": "narrator",   "status": "active", "active_tasks": 0},
            "tester":     {"role": "test",       "status": "active", "active_tasks": 0},
        }
        with open(demo_nodes_path, "w", encoding="utf-8") as f:
            json.dump(demo_data, f, indent=2)
        print(f"Created demo nodes.json at {demo_nodes_path}")

    router = MeshRouterV2()

    # Demonstrate singleton
    router2 = MeshRouterV2()
    assert router is router2, "Singleton violated"
    print("Singleton OK — both references are the same instance")

    # Route several task types
    task_types = ["code", "security", "test", "docs", "research", "consensus"]
    print("\nRouting decisions:")
    for tt in task_types:
        try:
            node = router.route(tt)
            print(f"  route({tt!r:12}) → {node}")
        except RuntimeError as e:
            print(f"  route({tt!r:12}) → ERROR: {e}", file=sys.stderr)

    # Simulate latency feedback
    router.update_latency("guardian", 15.0)
    router.update_latency("guardian", 12.0)
    router.update_latency("researcher", 200.0)

    print("\nStats after routing:")
    stats = router.get_stats()
    print(f"  total_routes:       {stats['total_routes']}")
    print(f"  route_distribution: {stats['route_distribution']}")
    print(f"  latency_estimates:  {stats['latency_estimates']}")
    print(f"\nLog written to: {ROUTER_LOG}")
