"""
AdaptiveCircuitBreaker — per-agent block-rate monitor for the Supervisor.

Tracks the ratio of blocked actions per agent over a 60-second sliding window.
Enters HALF_OPEN at 9% block rate and OPEN (degraded) at 15% — catching
runaway agents before they reach total failure or trigger a governance cascade.

States:
  CLOSED    — nominal operation, block rate below threshold
  HALF_OPEN — elevated risk, block rate between 9-15%; supervisor may add latency
  OPEN      — agent quarantined, all actions rejected until rate recovers

Usage:
    breaker = AdaptiveCircuitBreaker(agent_id="apex-1687")
    breaker.record(blocked=True)   # called by Supervisor after each governance check
    if breaker.state() == CircuitState.OPEN:
        raise AgentQuarantinedException(agent_id)
"""

import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

logger = logging.getLogger("core.adaptive_circuit_breaker")


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    HALF_OPEN = "HALF_OPEN"
    OPEN = "OPEN"


@dataclass(frozen=True)
class CircuitSnapshot:
    agent_id: str
    state: CircuitState
    block_rate: float
    total_events: int
    blocked_events: int
    window_seconds: int


class AdaptiveCircuitBreaker:
    """Sliding-window block-rate circuit breaker per agent.

    Args:
        agent_id: Identifier for the agent being monitored.
        threshold_rate: Block rate that triggers OPEN state. Default 15%.
        window_seconds: Sliding window duration. Default 60s.
    """

    def __init__(
        self,
        agent_id: str,
        threshold_rate: float = 0.15,
        window_seconds: int = 60,
    ):
        self.agent_id = agent_id
        self.threshold = threshold_rate
        self.window = timedelta(seconds=window_seconds)
        self._events: deque[tuple[datetime, bool]] = deque()

    # ─── Public API ───────────────────────────────────────────────────────────

    def record(self, blocked: bool) -> None:
        """Record one governance check result.

        Args:
            blocked: True if the agent action was blocked by governance.
        """
        now = datetime.now(timezone.utc)
        self._events.append((now, blocked))
        self._purge_old(now)
        state = self.state()
        if state == CircuitState.OPEN:
            logger.error(
                f"[CircuitBreaker] Agent {self.agent_id} OPEN — "
                f"block rate {self._block_rate():.1%} >= {self.threshold:.1%} "
                f"over {self.window.seconds}s window. Agent quarantined."
            )
        elif state == CircuitState.HALF_OPEN:
            logger.warning(
                f"[CircuitBreaker] Agent {self.agent_id} HALF_OPEN — "
                f"block rate {self._block_rate():.1%} (threshold {self.threshold:.1%})"
            )

    def state(self) -> CircuitState:
        """Return current circuit state based on recent block rate."""
        self._purge_old(datetime.now(timezone.utc))
        rate = self._block_rate()
        if rate >= self.threshold:
            return CircuitState.OPEN
        elif rate >= self.threshold * 0.6:
            return CircuitState.HALF_OPEN
        return CircuitState.CLOSED

    def snapshot(self) -> CircuitSnapshot:
        """Return a read-only snapshot of current circuit state."""
        self._purge_old(datetime.now(timezone.utc))
        blocked = sum(1 for _, b in self._events if b)
        return CircuitSnapshot(
            agent_id=self.agent_id,
            state=self.state(),
            block_rate=round(self._block_rate(), 4),
            total_events=len(self._events),
            blocked_events=blocked,
            window_seconds=self.window.seconds,
        )

    def reset(self) -> None:
        """Clear all events (use after deliberate agent restart or manual review)."""
        self._events.clear()
        logger.info(f"[CircuitBreaker] Agent {self.agent_id} manually reset to CLOSED.")

    # ─── Internal ─────────────────────────────────────────────────────────────

    def _purge_old(self, now: datetime) -> None:
        while self._events and (now - self._events[0][0]) > self.window:
            self._events.popleft()

    def _block_rate(self) -> float:
        if not self._events:
            return 0.0
        blocked = sum(1 for _, b in self._events if b)
        return blocked / len(self._events)
