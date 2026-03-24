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

    def __new__(cls):
        if cls._instance is None:
            with cls._class_lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    inst._lock = threading.Lock()
                    inst._active_tasks: Dict[str, int] = {}
                    cls._instance = inst
        return cls._instance

    def __init__(self):
        pass  # init handled in __new__

    # ── Public API ─────────────────────────────────────────────────────────────

    def provision(self, task_type: str, context_tokens: int) -> str:
        """
        Reserve a node for a task. Returns the selected node_id.

        Args:
            task_type:      Kind of task ("code", "research", "docs", …)
            context_tokens: Estimated token count for routing decisions

        Returns:
            node_id string of the selected node
        """
        from core.mesh_cost_optimizer import CostOptimizer
        node_id = CostOptimizer().get_cheapest_node(context_tokens, task_type)

        with self._lock:
            if node_id not in self._active_tasks:
                self._active_tasks[node_id] = self._read_active_tasks_from_disk(node_id)
            self._active_tasks[node_id] += 1
            self._persist_active_tasks(node_id, self._active_tasks[node_id])

        logger.info("Provisioned [%s] for task_type=%s tokens=%d", node_id, task_type, context_tokens)
        return node_id

    def deprovision(self, node_id: str) -> None:
        """
        Release one active task slot on node_id.
        """
        with self._lock:
            if node_id not in self._active_tasks:
                self._active_tasks[node_id] = self._read_active_tasks_from_disk(node_id)
            new_val = max(0, self._active_tasks[node_id] - 1)
            self._active_tasks[node_id] = new_val
            self._persist_active_tasks(node_id, new_val)

        logger.info("Deprovisioned [%s] — active_tasks now %d", node_id, new_val)

    def get_active_provisions(self) -> Dict[str, int]:
        """Return a copy of the current active task counts per node."""
        with self._lock:
            return dict(self._active_tasks)

    # ── Persistence ────────────────────────────────────────────────────────────

    def _read_active_tasks_from_disk(self, node_id: str) -> int:
        """Read current active_tasks for node_id from nodes.json (0 if not found)."""
        try:
            path = NODES_JSON_PATH
            if not path.exists():
                return 0
            with open(path, "r", encoding="utf-8") as f:
                nodes = json.load(f)
            return nodes.get(node_id, {}).get("active_tasks", 0)
        except Exception:
            return 0

    def _persist_active_tasks(self, node_id: str, count: int) -> None:
        """Write updated active_tasks count to nodes.json (if it exists)."""
        try:
            path = NODES_JSON_PATH  # may be patched in tests
            if not path.exists():
                return
            with open(path, "r", encoding="utf-8") as f:
                nodes = json.load(f)
            if node_id in nodes:
                nodes[node_id]["active_tasks"] = count
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(nodes, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning("Could not persist active_tasks for %s: %s", node_id, e)
