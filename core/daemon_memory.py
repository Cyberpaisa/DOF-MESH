"""
daemon_memory.py — Historical context layer for AutonomousDaemon.

Indexes cycles.jsonl so the daemon can answer structural questions
about its own history without re-reading the entire log each cycle.

Usage::
    from core.daemon_memory import DaemonMemory

    mem = DaemonMemory("logs/daemon/cycles.jsonl")

    # How many cycles have completed?
    print(mem.total_cycles())          # 553

    # Any repeated failures?
    print(mem.error_patterns(top_n=5))
    # [{"action": "...", "count": 7, "last_seen": "2026-04-12T..."}]

    # What happened in the last N cycles?
    print(mem.recent_summary(n=5))

    # How is a specific module performing?
    print(mem.module_health("governance"))

    # Full snapshot for scan_state()
    print(mem.scan_summary())
"""

from __future__ import annotations

import json
import logging
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger("dof.daemon_memory")


@dataclass
class CycleSummary:
    cycle: int
    iso: str
    mode: str
    action: str
    status: str
    elapsed_ms: float
    agents_spawned: int


@dataclass
class ErrorPattern:
    action: str
    count: int
    last_seen: str
    modes: list[str]


@dataclass
class MemoryScan:
    total_cycles: int
    success_rate: float
    avg_elapsed_ms: float
    top_errors: list[ErrorPattern]
    mode_distribution: dict[str, int]
    recent_cycles: list[CycleSummary]
    last_updated: float = field(default_factory=time.time)


class DaemonMemory:
    """
    Read-only index over cycles.jsonl.

    All public methods are synchronous and O(n) on the log file.
    The index is rebuilt on demand via `refresh()` — call once per cycle
    at the start of `scan_state()` to keep it fresh without re-reading
    on every individual query.
    """

    def __init__(
        self,
        cycles_path: str | Path = "logs/daemon/cycles.jsonl",
        max_cycles: int = 10_000,
    ) -> None:
        self._path = Path(cycles_path)
        self._max_cycles = max_cycles
        self._cycles: list[dict] = []
        self._loaded_at: float = 0.0
        self._load()

    # ── Internal loader ────────────────────────────────────────────────────────

    def _load(self) -> None:
        """Load (or reload) cycles from disk."""
        if not self._path.exists():
            self._cycles = []
            return
        cycles: list[dict] = []
        try:
            for line in self._path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    cycles.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        except OSError as e:
            logger.warning(f"DaemonMemory: cannot read {self._path}: {e}")
        # Keep newest cycles if log is huge
        self._cycles = cycles[-self._max_cycles:]
        self._loaded_at = time.time()
        logger.debug(f"DaemonMemory: loaded {len(self._cycles)} cycles")

    def refresh(self) -> None:
        """Re-read cycles.jsonl from disk. Call at the start of each daemon cycle."""
        self._load()

    # ── Query API ──────────────────────────────────────────────────────────────

    def total_cycles(self) -> int:
        """Total cycle count in the log."""
        return len(self._cycles)

    def success_rate(self) -> float:
        """Fraction of cycles with result_status == 'success'."""
        if not self._cycles:
            return 1.0
        successes = sum(1 for c in self._cycles if c.get("result_status") == "success")
        return round(successes / len(self._cycles), 3)

    def avg_elapsed_ms(self) -> float:
        """Average elapsed time per cycle (ms)."""
        times = [c.get("elapsed_ms", 0) for c in self._cycles if c.get("elapsed_ms")]
        return round(sum(times) / len(times), 1) if times else 0.0

    def error_patterns(self, top_n: int = 5) -> list[ErrorPattern]:
        """
        Return the top-N most repeated error actions.

        An error is any cycle with result_status != 'success'.
        Groups by action text — useful for detecting stuck loops.
        """
        action_counter: Counter = Counter()
        action_last_seen: dict[str, str] = {}
        action_modes: dict[str, list[str]] = defaultdict(list)

        for c in self._cycles:
            if c.get("result_status") == "success":
                continue
            action = c.get("action", "unknown")[:80]
            action_counter[action] += 1
            iso = c.get("iso", "")
            if iso > action_last_seen.get(action, ""):
                action_last_seen[action] = iso
            mode = c.get("mode", "")
            if mode not in action_modes[action]:
                action_modes[action].append(mode)

        return [
            ErrorPattern(
                action=action,
                count=count,
                last_seen=action_last_seen.get(action, ""),
                modes=action_modes[action],
            )
            for action, count in action_counter.most_common(top_n)
        ]

    def mode_distribution(self) -> dict[str, int]:
        """Count how many cycles ran in each mode."""
        counts: Counter = Counter()
        for c in self._cycles:
            counts[c.get("mode", "unknown")] += 1
        return dict(counts)

    def recent_summary(self, n: int = 10) -> list[CycleSummary]:
        """Return the N most recent cycles as structured summaries."""
        recent = self._cycles[-n:] if len(self._cycles) >= n else self._cycles
        result = []
        for c in reversed(recent):
            try:
                result.append(CycleSummary(
                    cycle=c.get("cycle", 0),
                    iso=c.get("iso", ""),
                    mode=c.get("mode", ""),
                    action=c.get("action", "")[:80],
                    status=c.get("result_status", ""),
                    elapsed_ms=float(c.get("elapsed_ms", 0)),
                    agents_spawned=int(c.get("agents_spawned", 0)),
                ))
            except (TypeError, ValueError):
                continue
        return result

    def module_health(self, module_name: str) -> dict:
        """
        Return health metrics for cycles mentioning a specific module name.

        Looks in 'action' and 'output_summary' fields.
        """
        relevant = [
            c for c in self._cycles
            if module_name.lower() in (c.get("action", "") + c.get("output_summary", "")).lower()
        ]
        if not relevant:
            return {"module": module_name, "cycles_found": 0}
        successes = sum(1 for c in relevant if c.get("result_status") == "success")
        return {
            "module": module_name,
            "cycles_found": len(relevant),
            "success_rate": round(successes / len(relevant), 3),
            "last_seen": max((c.get("iso", "") for c in relevant), default=""),
        }

    def last_failure(self) -> Optional[dict]:
        """Return the most recent failed cycle dict, or None."""
        for c in reversed(self._cycles):
            if c.get("result_status") != "success":
                return c
        return None

    def scan_summary(self) -> MemoryScan:
        """
        Full snapshot — designed to be called by AutonomousDaemon.scan_state()
        to enrich the SystemState with historical context.
        """
        return MemoryScan(
            total_cycles=self.total_cycles(),
            success_rate=self.success_rate(),
            avg_elapsed_ms=self.avg_elapsed_ms(),
            top_errors=self.error_patterns(top_n=3),
            mode_distribution=self.mode_distribution(),
            recent_cycles=self.recent_summary(n=5),
        )
