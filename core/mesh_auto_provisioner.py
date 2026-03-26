"""
Mesh Auto Provisioner — DOF Mesh.

Tracks active tasks per node and selects the cheapest available node
for new work by delegating to CostOptimizer.

API:
    prov = AutoProvisioner()
    node = prov.provision("code", 1000)   # task_type, context_tokens
    prov.deprovision("cerebras-llama")
    active = prov.get_active_provisions() # {node_id: active_task_count}
"""

import json
import logging
import threading
import time
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger("core.mesh_auto_provisioner")

# ── Paths (patchable in tests) ─────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
NODES_JSON_PATH = REPO_ROOT / "logs" / "mesh" / "nodes.json"
PROVISIONER_LOG_PATH = REPO_ROOT / "logs" / "mesh" / "provisioner.jsonl"


class AutoProvisioner:
    """
    Singleton provisioner that assigns tasks to nodes and tracks load.

    Uses CostOptimizer to pick the cheapest node for each task_type +
    context_token combination. Updates active_tasks count in nodes.json.
    """

    _instance = None
    _class_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._class_lock:
            if cls._instance is None:
                cls._instance = super(AutoProvisioner, cls).__new__(cls)
                cls._instance._initialized = False
                cls._instance._lock = threading.Lock() # Initialize instance lock here
        return cls._instance

    def __init__(self, bridge=None):
        if self._initialized:
            return
        from core.hyperion_bridge import HyperionBridge
        self._bridge = bridge or HyperionBridge()
        self._initialized = True

    # ── Public API ─────────────────────────────────────────────────────────────

    def provision(self, task_type: str, context_tokens: int) -> str:
        """
        Reserve a node for a task using Hyperion routing.
        """
        from core.mesh_cost_optimizer import CostOptimizer
        node_id = CostOptimizer().get_cheapest_node(context_tokens, task_type)

        # Notify bridge of new task (Hyperion handles queueing)
        # The provisioner tracks 'active_tasks' for the autoscaler to see in nodes.json
        with self._lock:
            current = self._read_active_tasks_from_disk(node_id)
            new_val = current + 1
            self._persist_active_tasks(node_id, new_val)

        logger.info("Hyperion Provisioned [%s] for %s (%d tokens)", node_id, task_type, context_tokens)
        return node_id

    def deprovision(self, node_id: str) -> None:
        """Release one task slot."""
        with self._lock:
            current = self._read_active_tasks_from_disk(node_id)
            new_val = max(0, current - 1)
            self._persist_active_tasks(node_id, new_val)

        logger.info("Hyperion Deprovisioned [%s] — active now %d", node_id, new_val)

    def handle_scale_event(self, event) -> bool:
        """
        Act on a ScaleEvent (scale_up/scale_down).
        Implementation for Phase 9: spawn siblings or mark for retirement.
        """
        if event.event_type == "scale_up":
            sibling_id = f"{event.node_id}-clone-{int(time.time())}"
            logger.warning("Hyperion SCALE_UP: Spawning sibling %s", sibling_id)
            # In a real provisioner, this would trigger a container/process
            # For now, we register it in the bridge
            self._bridge.spawn_node(sibling_id, f"Scaling relief for {event.node_id}")
            return True
        return False

    def get_active_provisions(self) -> Dict[str, int]:
        """Return task counts from the Hyperion status if possible."""
        status = self._bridge.status()
        return status.get("dispatched_by_node", {})

    # ── Persistence ────────────────────────────────────────────────────────────

    def _read_active_tasks_from_disk(self, node_id: str) -> int:
        """Read from nodes.json (legacy compatibility)."""
        try:
            if not NODES_JSON_PATH.exists():
                return 0
            with open(NODES_JSON_PATH, "r", encoding="utf-8") as f:
                nodes = json.load(f)
            return nodes.get(node_id, {}).get("active_tasks", 0)
        except Exception:
            return 0

    def _persist_active_tasks(self, node_id: str, count: int) -> None:
        """Sync active_tasks to nodes.json for the AutoScaler to read."""
        try:
            if not NODES_JSON_PATH.exists():
                return
            with open(NODES_JSON_PATH, "r", encoding="utf-8") as f:
                nodes = json.load(f)
            if node_id in nodes:
                nodes[node_id]["active_tasks"] = count
                with open(NODES_JSON_PATH, "w", encoding="utf-8") as f:
                    json.dump(nodes, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning("Sync failed for %s: %s", node_id, e)
