from __future__ import annotations
"""
dof_distributed_queue.py — DistributedMeshQueue para DOF Mesh Hyperion.

Extiende MeshQueue (604K tasks/sec) con sharding via ConsistentHashRing.
Cada shard tiene su propia cola en memoria. WAL opcional para crash recovery.

Uso:
    sm = DOFShardManager(["machine-a", "machine-b", "machine-c"])
    q = DistributedMeshQueue("node-a", sm)
    task = DistributedTask(task_id="t1", shard_key="agent-42", prompt="hola")
    q.enqueue(task)
    task = q.dequeue(shard_id=0)
"""
import logging
import queue
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from core.dof_sharding import DOFShardManager
from core.dof_wal import WriteAheadLog

logger = logging.getLogger("core.dof_distributed_queue")

REPO_ROOT = Path(__file__).parent.parent


# ── DistributedTask ───────────────────────────────────────────────────────────

@dataclass(order=True)
class DistributedTask:
    priority: int = 1                           # 0=HIGH, 1=NORMAL, 2=LOW (order key)
    task_id: str = field(compare=False, default="")
    shard_key: str = field(compare=False, default="")
    prompt: str = field(compare=False, default="")
    created_at: float = field(compare=False, default_factory=time.time)
    retry_count: int = field(compare=False, default=0)
    vector_clock: dict = field(compare=False, default_factory=dict)
    metadata: dict = field(compare=False, default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> "DistributedTask":
        priority_map = {"high": 0, "normal": 1, "low": 2}
        return cls(
            priority=priority_map.get(str(d.get("priority", "normal")).lower(), 1),
            task_id=d.get("task_id") or d.get("msg_id", ""),
            shard_key=d.get("shard_key") or d.get("to") or d.get("node", ""),
            prompt=d.get("prompt") or d.get("task") or str(d),
            created_at=d.get("created_at", time.time()),
            retry_count=d.get("retry_count", 0),
            vector_clock=d.get("vector_clock", {}),
            metadata=d,
        )

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "shard_key": self.shard_key,
            "prompt": self.prompt,
            "priority": self.priority,
            "created_at": self.created_at,
            "retry_count": self.retry_count,
            "vector_clock": self.vector_clock,
            **self.metadata,
        }


# ── DistributedMeshQueue ──────────────────────────────────────────────────────

class DistributedMeshQueue:
    """
    Cola distribuida con sharding via ConsistentHashRing.

    - Cada shard tiene un queue.PriorityQueue en memoria.
    - WAL opcional para crash recovery.
    - Compatible con MeshQueue existente (drain_from_mesh_queue).
    - Thread-safe.
    """

    def __init__(
        self,
        node_id: str,
        shard_manager: DOFShardManager,
        wal_path: Optional[str] = None,
        flush_to_disk: bool = False,
    ) -> None:
        self.node_id = node_id
        self.shard_manager = shard_manager
        self.flush_to_disk = flush_to_disk

        # Una cola por shard
        self._queues: dict[int, queue.PriorityQueue] = {
            shard_id: queue.PriorityQueue()
            for shard_id in shard_manager.shards
        }
        self._processed: set[str] = set()
        self._lock = threading.Lock()
        self._enqueued = 0
        self._dequeued = 0

        # WAL opcional
        self._wal: Optional[WriteAheadLog] = None
        if wal_path:
            self._wal = WriteAheadLog(wal_path)
            self._recover_from_wal()

        logger.info(
            "DistributedMeshQueue[%s] ready: %d shards, WAL=%s",
            node_id, len(self._queues), bool(wal_path),
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def enqueue(self, task: DistributedTask) -> str:
        """Enqueue task al shard correcto. Retorna task_id."""
        with self._lock:
            if task.task_id in self._processed:
                return task.task_id  # dedup

        shard = self.shard_manager.get_shard_for_key(task.shard_key or task.task_id)

        if self._wal:
            self._wal.append("enqueue", task.task_id, task.to_dict())

        self._queues[shard.id].put(task)

        with self._lock:
            self._enqueued += 1

        logger.debug("Enqueued %s → shard %d (%s)", task.task_id, shard.id, shard.primary_node)
        return task.task_id

    def dequeue(self, shard_id: int, timeout: float = 0.1) -> Optional[DistributedTask]:
        """Dequeue del shard indicado. Bloquea hasta timeout segundos."""
        q = self._queues.get(shard_id)
        if q is None:
            return None
        try:
            task = q.get(timeout=timeout)
            with self._lock:
                self._dequeued += 1
            return task
        except queue.Empty:
            return None

    def dequeue_any(self, timeout: float = 0.1) -> Optional[DistributedTask]:
        """Dequeue del primer shard con tareas disponibles."""
        for shard_id, q in self._queues.items():
            if not q.empty():
                try:
                    task = q.get_nowait()
                    with self._lock:
                        self._dequeued += 1
                    return task
                except queue.Empty:
                    pass
        time.sleep(timeout)
        return None

    def task_done(self, task: DistributedTask) -> None:
        """Marcar tarea como completada."""
        with self._lock:
            self._processed.add(task.task_id)
        shard = self.shard_manager.get_shard_for_key(task.shard_key or task.task_id)
        try:
            self._queues[shard.id].task_done()
        except Exception:
            pass
        if self._wal:
            # Buscar seq del WAL para confirmar (simplificado)
            pass

    def qsize(self) -> int:
        return sum(q.qsize() for q in self._queues.values())

    def qsize_for_shard(self, shard_id: int) -> int:
        q = self._queues.get(shard_id)
        return q.qsize() if q else 0

    def drain_from_mesh_queue(self, mesh_queue) -> int:
        """
        Migra tareas desde MeshQueue (filesystem) a DistributedMeshQueue (memoria).
        Compatibilidad con el protocolo legacy.
        """
        from core.mesh_queue import MeshTask
        count = 0
        while mesh_queue.qsize() > 0:
            mesh_task = mesh_queue.dequeue(timeout=0.01)
            if mesh_task:
                dtask = DistributedTask(
                    priority=mesh_task.priority,
                    task_id=mesh_task.task_id,
                    shard_key=mesh_task.node,
                    prompt=mesh_task.prompt,
                    created_at=mesh_task.created_at,
                    metadata=mesh_task.metadata,
                )
                self.enqueue(dtask)
                count += 1
        if count:
            logger.info("Drained %d tasks from MeshQueue → DistributedMeshQueue", count)
        return count

    def status(self) -> dict:
        with self._lock:
            enqueued = self._enqueued
            dequeued = self._dequeued
            processed = len(self._processed)
        return {
            "node_id": self.node_id,
            "shards": len(self._queues),
            "total_queued": self.qsize(),
            "enqueued_total": enqueued,
            "dequeued_total": dequeued,
            "processed": processed,
            "wal": bool(self._wal),
            "per_shard": {sid: q.qsize() for sid, q in self._queues.items()},
        }

    # ── Internal ──────────────────────────────────────────────────────────────

    def _recover_from_wal(self) -> None:
        if not self._wal:
            return
        entries = self._wal.recover()
        for entry in entries:
            try:
                task = DistributedTask.from_dict(entry.data)
                shard = self.shard_manager.get_shard_for_key(task.shard_key or task.task_id)
                self._queues[shard.id].put(task)
            except Exception as e:
                logger.error("WAL recovery error for seq %d: %s", entry.seq, e)
        if entries:
            logger.info("WAL: recovered %d pending tasks", len(entries))


# ── Benchmark ─────────────────────────────────────────────────────────────────

def benchmark(n: int = 10_000) -> None:
    from core.dof_sharding import DOFShardManager
    import time

    sm = DOFShardManager(["m-a", "m-b", "m-c", "m-d", "m-e"], shard_count=10)
    q = DistributedMeshQueue("bench", sm)

    t0 = time.perf_counter()
    for i in range(n):
        task = DistributedTask(
            task_id=f"t{i}",
            shard_key=f"agent-{i % 80}",
            prompt=f"task {i}",
        )
        q.enqueue(task)
    enqueue_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    count = 0
    while q.qsize() > 0:
        t = q.dequeue_any(timeout=0.001)
        if t:
            count += 1
    dequeue_ms = (time.perf_counter() - t0) * 1000

    print(f"DistributedMeshQueue benchmark ({n:,} tasks, 10 shards, 5 machines):")
    print(f"  Enqueue: {enqueue_ms:.1f}ms — {enqueue_ms/n*1000:.1f}µs/task")
    print(f"  Dequeue: {dequeue_ms:.1f}ms — {dequeue_ms/n*1000:.1f}µs/task")
    print(f"  Throughput: {n/(dequeue_ms/1000):,.0f} tasks/sec")
    print(f"  Status: {q.status()}")


if __name__ == "__main__":
    benchmark()
