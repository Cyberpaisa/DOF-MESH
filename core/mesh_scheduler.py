"""
mesh_scheduler.py — Smart task scheduler for the DOF mesh.
Manages concurrency slots, RAM-aware recommendations, and a priority queue.
DiskTaskQueue adds filelock-backed persistence so tasks survive restarts.
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import psutil
from filelock import FileLock

# ---------------------------------------------------------------------------
# Priority levels
# ---------------------------------------------------------------------------
HIGH = 1
NORMAL = 2
LOW = 3


# ---------------------------------------------------------------------------
# Task descriptor
# ---------------------------------------------------------------------------
@dataclass(order=True)
class TaskSlot:
    priority: int          # compared first for ordering
    queued_at: float       # tiebreak: earlier queued tasks win
    task_id: str = field(compare=False)
    prompt: str = field(compare=False)
    node: str = field(compare=False)

    @classmethod
    def create(
        cls,
        task_id: str,
        prompt: str,
        node: str,
        priority: int = NORMAL,
        queued_at: Optional[float] = None,
    ) -> "TaskSlot":
        return cls(
            priority=priority,
            queued_at=queued_at if queued_at is not None else time.time(),
            task_id=task_id,
            prompt=prompt,
            node=node,
        )


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------
class MeshScheduler:
    """
    Smart concurrency scheduler for the DOF mesh.

    Priority queue (min-heap semantics via sorted list):
      HIGH=1 runs before NORMAL=2 before LOW=3.
    """

    def __init__(self, max_concurrent: int = 3) -> None:
        self.max_concurrent: int = max_concurrent
        self._active: int = 0
        self._queue: List[TaskSlot] = []

    # ------------------------------------------------------------------
    # Concurrency control
    # ------------------------------------------------------------------

    def can_accept(self) -> bool:
        """True when a new task can start immediately."""
        return self._active < self.max_concurrent

    def acquire(self) -> None:
        """Mark one slot as in-use."""
        self._active += 1

    def release(self) -> None:
        """Free one slot; never goes below zero."""
        self._active = max(0, self._active - 1)

    # ------------------------------------------------------------------
    # Hardware awareness
    # ------------------------------------------------------------------

    def available_ram_gb(self) -> float:
        """Return available system RAM in GB via psutil."""
        mem = psutil.virtual_memory()
        return mem.available / (1024 ** 3)

    def recommended_slots(self) -> int:
        """
        MiniMax corrected formula:
          per_task_overhead_gb = 2.5  (Python runtime + agent + temp tensors)
          safety_margin_gb     = 2
          usable               = available_ram_gb - 9 - safety_margin_gb
          recommended_slots    = max(1, min(floor(usable / per_task_overhead_gb), max_concurrent))

        On 36 GB M4 Max: usable = 36 - 9 - 2 = 25 → floor(25/2.5) = 10 → capped at max_concurrent.
        Returns at least 1 even when usable RAM is very low.
        """
        per_task_overhead_gb = 2.5
        safety_margin_gb = 2
        usable = self.available_ram_gb() - 9 - safety_margin_gb
        slots = int(usable // per_task_overhead_gb)
        return max(1, min(slots, self.max_concurrent))

    # ------------------------------------------------------------------
    # Queue management
    # ------------------------------------------------------------------

    def enqueue(self, task: TaskSlot) -> None:
        """Add a task to the priority queue (sorted ascending by priority then queued_at)."""
        self._queue.append(task)
        self._queue.sort()

    def dequeue(self) -> Optional[TaskSlot]:
        """Pop and return the highest-priority pending task, or None if empty."""
        return self._queue.pop(0) if self._queue else None

    def queue_size(self) -> int:
        return len(self._queue)

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def status(self) -> dict:
        return {
            "active": self._active,
            "queued": self.queue_size(),
            "max_concurrent": self.max_concurrent,
            "can_accept": self.can_accept(),
            "recommended_slots": self.recommended_slots(),
            "available_ram_gb": round(self.available_ram_gb(), 2),
        }


# ---------------------------------------------------------------------------
# Disk-backed task queue — survives restarts, filelock-protected
# ---------------------------------------------------------------------------

class DiskTaskQueue:
    """
    Persistent JSONL task queue protected by a filelock, with optional TTL.

    Tasks are stored one-per-line as JSON in ``queue_path``.
    A companion lock file (<queue_path>.lock) serialises concurrent writes.
    All mutating operations hold the lock for the minimum time needed.

    TTL (time-to-live):
        When ``ttl_seconds`` is set, tasks older than that value are silently
        dropped on every read. This prevents stale tasks from accumulating
        after crashes or long pauses.

    Usage::
        q = DiskTaskQueue("logs/commander/task_queue.jsonl", ttl_seconds=3600)
        q.push(TaskSlot.create("t1", "do X", "node-a", priority=HIGH))
        task = q.pop()          # highest-priority non-expired item
        count = q.size()        # excludes expired tasks
        all_tasks = q.drain()   # atomically empty queue, returns non-expired tasks
        q.clear()               # discard all pending tasks
        expired = q.evict()     # explicitly remove expired tasks, returns count
    """

    def __init__(
        self,
        queue_path: str | Path,
        timeout: float = 5.0,
        ttl_seconds: Optional[float] = None,
    ) -> None:
        self._path = Path(queue_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = FileLock(str(self._path) + ".lock", timeout=timeout)
        self._ttl = ttl_seconds

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_expired(self, queued_at: float) -> bool:
        """Return True if the task has exceeded the TTL."""
        if self._ttl is None:
            return False
        return (time.time() - queued_at) > self._ttl

    def _read_all(self) -> List[TaskSlot]:
        """Read all non-expired tasks from disk. Caller must hold the lock."""
        if not self._path.exists():
            return []
        tasks: List[TaskSlot] = []
        for line in self._path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                queued_at = d["queued_at"]
                if self._is_expired(queued_at):
                    continue  # silently drop expired tasks
                tasks.append(TaskSlot(
                    priority=d["priority"],
                    queued_at=queued_at,
                    task_id=d["task_id"],
                    prompt=d["prompt"],
                    node=d["node"],
                ))
            except (KeyError, json.JSONDecodeError):
                continue
        return tasks

    def _write_all(self, tasks: List[TaskSlot]) -> None:
        """Overwrite the queue file. Caller must hold the lock."""
        lines = [
            json.dumps({
                "priority": t.priority,
                "queued_at": t.queued_at,
                "task_id": t.task_id,
                "prompt": t.prompt,
                "node": t.node,
            })
            for t in sorted(tasks)  # highest priority first on disk
        ]
        self._path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def push(self, task: TaskSlot) -> None:
        """Append a task to the queue (preserves expired tasks on disk until evict())."""
        with self._lock:
            # Append directly to avoid re-reading and re-sorting the whole file
            entry = json.dumps({
                "priority": task.priority,
                "queued_at": task.queued_at,
                "task_id": task.task_id,
                "prompt": task.prompt,
                "node": task.node,
            })
            with self._path.open("a", encoding="utf-8") as f:
                f.write(entry + "\n")

    def pop(self) -> Optional[TaskSlot]:
        """Remove and return the highest-priority task, or None if empty."""
        with self._lock:
            tasks = self._read_all()
            if not tasks:
                return None
            tasks.sort()
            top = tasks.pop(0)
            self._write_all(tasks)
            return top

    def size(self) -> int:
        """Return the number of pending tasks (reads disk without lock — approximate)."""
        with self._lock:
            return len(self._read_all())

    def drain(self) -> List[TaskSlot]:
        """Atomically empty the queue and return all tasks sorted by priority."""
        with self._lock:
            tasks = sorted(self._read_all())
            self._write_all([])
            return tasks

    def clear(self) -> None:
        """Discard all pending tasks."""
        with self._lock:
            self._write_all([])

    def _read_all_raw(self) -> List[dict]:
        """Read ALL task dicts from disk without TTL filtering. Caller must hold the lock."""
        if not self._path.exists():
            return []
        rows = []
        for line in self._path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return rows

    def evict(self) -> int:
        """Explicitly remove expired tasks. Returns the number of tasks evicted.

        Not needed for normal use — _read_all() already filters expired tasks.
        Useful for reclaiming disk space after a long pause.
        """
        if self._ttl is None:
            return 0
        with self._lock:
            all_rows = self._read_all_raw()
            live = [
                r for r in all_rows
                if not self._is_expired(r.get("queued_at", 0))
            ]
            live_slots = []
            for r in live:
                try:
                    live_slots.append(TaskSlot(
                        priority=r["priority"],
                        queued_at=r["queued_at"],
                        task_id=r["task_id"],
                        prompt=r["prompt"],
                        node=r["node"],
                    ))
                except KeyError:
                    continue
            self._write_all(live_slots)
            return len(all_rows) - len(live)
