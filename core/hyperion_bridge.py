"""
hyperion_bridge.py — Integración de DistributedMeshQueue con el supervisor existente.

Patrón: Facade sobre el mesh actual.
- Compatible 100% con NodeMesh/supervisor existente.
- Agrega routing Hyperion sin romper nada.
- Drop-in replacement: import HyperionBridge as NodeMesh

Uso en supervisor.py (0 cambios necesarios):
    # Antes:
    from core.node_mesh import NodeMesh
    mesh = NodeMesh()

    # Después (una línea):
    from core.hyperion_bridge import HyperionBridge as NodeMesh
    mesh = NodeMesh()
"""
import logging
import time
from pathlib import Path
from typing import Any, Optional

from core.dof_sharding import DOFShardManager
from core.dof_distributed_queue import DistributedMeshQueue, DistributedTask

logger = logging.getLogger("core.hyperion_bridge")

REPO_ROOT = Path(__file__).parent.parent

# Máquinas del cluster (en producción: leer de config)
_DEFAULT_MACHINES = ["machine-a", "machine-b", "machine-c", "machine-d", "machine-e"]


class HyperionBridge:
    """
    Facade que envuelve DistributedMeshQueue con la API de NodeMesh.
    Permite migración gradual sin romper código existente.

    Métodos compatibles con NodeMesh:
        send_message(from_node, to_node, content, msg_type)
        read_inbox(node_id)
        broadcast(from_node, content)
        spawn_node(node_id, task)
    """

    _instance: Optional["HyperionBridge"] = None  # Singleton

    def __new__(cls, machines=None, shard_count=10):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, machines=None, shard_count=10):
        if self._initialized:
            return
        self._initialized = True

        machines = machines or _DEFAULT_MACHINES
        self._sm = DOFShardManager(machines, shard_count=shard_count, replication_factor=3)
        self._queue = DistributedMeshQueue(
            node_id="hyperion-bridge",
            shard_manager=self._sm,
            wal_path=str(REPO_ROOT / "logs" / "wal" / "hyperion"),
        )
        self._dispatched: dict[str, list] = {}  # node → tasks

        # Fallback: NodeMesh para compatibilidad filesystem
        self._node_mesh = None
        try:
            from core.node_mesh import NodeMesh
            self._node_mesh = NodeMesh()
            logger.info("HyperionBridge: NodeMesh fallback activo")
        except Exception:
            logger.warning("HyperionBridge: NodeMesh no disponible — solo Hyperion queue")

        logger.info(
            "HyperionBridge ready: %d máquinas, %d shards",
            len(machines), shard_count,
        )

    # ── API compatible con NodeMesh ───────────────────────────────────────────

    def send_message(
        self,
        from_node: str,
        to_node: str,
        content: Any,
        msg_type: str = "task",
    ) -> str:
        """
        Enviar mensaje/tarea a un nodo.
        Compatible con NodeMesh.send_message().
        """
        task_id = f"{to_node}-{int(time.time_ns() // 1_000_000)}"

        # 1. Enqueue en DistributedMeshQueue (Hyperion)
        prompt = content if isinstance(content, str) else str(content.get("task", content))
        task = DistributedTask(
            task_id=task_id,
            shard_key=to_node,
            prompt=prompt,
            priority=0 if msg_type in ("urgent", "high") else 1,
            metadata={"from": from_node, "to": to_node, "type": msg_type,
                      "content": content},
        )
        self._queue.enqueue(task)

        # Track por nodo
        self._dispatched.setdefault(to_node, []).append(task_id)

        # 2. También enviar vía NodeMesh (filesystem protocol, para compatibilidad)
        if self._node_mesh:
            try:
                self._node_mesh.send_message(from_node, to_node, content, msg_type)
            except Exception as e:
                logger.debug("NodeMesh fallback error: %s", e)

        logger.info("HyperionBridge: %s → %s [%s] task=%s", from_node, to_node, msg_type, task_id)
        return task_id

    def read_inbox(self, node_id: str, timeout: float = 0.1) -> Optional[DistributedTask]:
        """Leer siguiente tarea para un nodo."""
        shard = self._sm.get_shard_for_key(node_id)
        return self._queue.dequeue(shard.id, timeout=timeout)

    def broadcast(self, from_node: str, content: Any, nodes: list[str] = None) -> list[str]:
        """Enviar a múltiples nodos."""
        targets = nodes or ["architect", "researcher", "guardian", "verifier", "narrator", "devops"]
        return [self.send_message(from_node, n, content, "broadcast") for n in targets]

    def spawn_node(self, node_id: str, task: str) -> str:
        """Registrar agente y asignarle tarea inicial."""
        self._sm.assign_agent(node_id)
        return self.send_message("hyperion-bridge", node_id, {"task": task}, "spawn")

    def status(self) -> dict:
        return {
            "queue": self._queue.status(),
            "shards": self._sm.status(),
            "dispatched_by_node": {k: len(v) for k, v in self._dispatched.items()},
            "node_mesh_active": bool(self._node_mesh),
        }

    def queue_size(self) -> int:
        return self._queue.qsize()

    # ── Reset singleton (para tests) ─────────────────────────────────────────

    @classmethod
    def reset(cls):
        cls._instance = None
