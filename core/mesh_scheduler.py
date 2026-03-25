"""
mesh_scheduler.py — Smart task scheduler for the DOF mesh.
Manages concurrency slots, RAM-aware recommendations, and a priority queue.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import List, Optional

import psutil

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
