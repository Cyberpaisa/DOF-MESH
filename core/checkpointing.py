from __future__ import annotations
"""
Step-Level Checkpointing — JSONL persistence.

Saves run_id, step_id, agent, provider, latency, status, input_hash, output.
Enables retry of only the failed step, not the entire crew.
"""

import os
import json
import time
import hashlib
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional

logger = logging.getLogger("core.checkpointing")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKPOINT_DIR = os.path.join(BASE_DIR, "logs", "checkpoints")


@dataclass
class StepCheckpoint:
    """A single step execution record."""
    run_id: str
    step_id: str
    agent: str
    task_name: str
    provider: str = ""
    status: str = "pending"  # pending | running | completed | failed
    input_hash: str = ""
    output: str = ""
    error: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    latency_ms: float = 0.0
    attempt: int = 1


class CheckpointManager:
    """Manages step-level checkpoints with JSONL persistence."""

    def __init__(self, run_id: str = ""):
        self.run_id = run_id or f"run_{int(time.time())}"
        self._steps: dict[str, StepCheckpoint] = {}
        os.makedirs(CHECKPOINT_DIR, exist_ok=True)
        self._file = os.path.join(CHECKPOINT_DIR, f"{self.run_id}.jsonl")

    @staticmethod
    def _hash_input(text: str) -> str:
        return hashlib.sha256(text.encode()[:2000]).hexdigest()[:16]

    def start_step(self, step_id: str, agent: str, task_name: str,
                   provider: str = "", input_text: str = "") -> StepCheckpoint:
        """Mark a step as running."""
        cp = StepCheckpoint(
            run_id=self.run_id,
            step_id=step_id,
            agent=agent,
            task_name=task_name,
            provider=provider,
            status="running",
            input_hash=self._hash_input(input_text),
            start_time=time.time(),
        )
        self._steps[step_id] = cp
        self._persist(cp)
        return cp

    def complete_step(self, step_id: str, output: str = "") -> Optional[StepCheckpoint]:
        """Mark a step as completed."""
        cp = self._steps.get(step_id)
        if not cp:
            return None
        cp.status = "completed"
        cp.output = output[:5000]
        cp.end_time = time.time()
        cp.latency_ms = (cp.end_time - cp.start_time) * 1000
        self._persist(cp)
        logger.info(f"Step '{step_id}' completed ({cp.latency_ms:.0f}ms, provider={cp.provider})")
        return cp

    def fail_step(self, step_id: str, error: str = "") -> Optional[StepCheckpoint]:
        """Mark a step as failed."""
        cp = self._steps.get(step_id)
        if not cp:
            return None
        cp.status = "failed"
        cp.error = error[:500]
        cp.end_time = time.time()
        cp.latency_ms = (cp.end_time - cp.start_time) * 1000
        logger.warning(f"Step '{step_id}' failed ({cp.latency_ms:.0f}ms): {error[:100]}")
        self._persist(cp)
        return cp

    def get_failed_steps(self) -> list[StepCheckpoint]:
        """Return all failed steps for retry."""
        return [cp for cp in self._steps.values() if cp.status == "failed"]

    def get_completed_steps(self) -> list[str]:
        """Return IDs of completed steps (to skip on retry)."""
        return [cp.step_id for cp in self._steps.values() if cp.status == "completed"]

    def get_summary(self) -> dict:
        """Return execution summary."""
        steps = list(self._steps.values())
        return {
            "run_id": self.run_id,
            "total_steps": len(steps),
            "completed": sum(1 for s in steps if s.status == "completed"),
            "failed": sum(1 for s in steps if s.status == "failed"),
            "running": sum(1 for s in steps if s.status == "running"),
            "total_latency_ms": sum(s.latency_ms for s in steps),
            "steps": [
                {
                    "step_id": s.step_id,
                    "agent": s.agent,
                    "provider": s.provider,
                    "status": s.status,
                    "latency_ms": round(s.latency_ms, 1),
                    "attempt": s.attempt,
                }
                for s in steps
            ],
        }

    def _persist(self, cp: StepCheckpoint):
        """Append checkpoint to JSONL file."""
        try:
            with open(self._file, "a") as f:
                f.write(json.dumps(asdict(cp), default=str) + "\n")
        except Exception as e:
            logger.error(f"Checkpoint persist error: {e}")

    @classmethod
    def load_run(cls, run_id: str) -> "CheckpointManager":
        """Load a previous run from JSONL file."""
        mgr = cls(run_id=run_id)
        filepath = os.path.join(CHECKPOINT_DIR, f"{run_id}.jsonl")
        if not os.path.exists(filepath):
            return mgr
        try:
            with open(filepath) as f:
                for line in f:
                    data = json.loads(line.strip())
                    cp = StepCheckpoint(**data)
                    mgr._steps[cp.step_id] = cp
        except Exception as e:
            logger.error(f"Checkpoint load error: {e}")
        return mgr
