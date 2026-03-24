"""
Mesh Circuit Breaker — Fault tolerance for DOF Mesh nodes.

Implements the classic circuit breaker pattern per node:

    CLOSED   — normal operation; failures counted.
               After failure_threshold consecutive failures → OPEN.

    OPEN     — calls rejected immediately (CircuitOpenError).
               After recovery_timeout seconds → HALF_OPEN.

    HALF_OPEN — trial mode; up to half_open_max_calls allowed.
               Success → CLOSED. Failure → back to OPEN.

Architecture:
    MeshCircuitBreaker (singleton)
        ├── one BreakerState per node_id, created on first access
        └── logs every state transition to logs/mesh/circuit_breaker.jsonl

Usage:
    from core.mesh_circuit_breaker import MeshCircuitBreaker, CircuitOpenError

    cb = MeshCircuitBreaker()

    # Wrap any callable
    result = cb.call("guardian", my_function, arg1, key=val)

    # Inspect state
    state = cb.get_state("guardian")   # "CLOSED" | "OPEN" | "HALF_OPEN"

    # Manual reset
    cb.reset("guardian")
"""

import json
import logging
import threading
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger("core.mesh_circuit_breaker")

# ═══════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════

BASE_DIR   = Path(__file__).resolve().parent.parent
BREAKER_LOG = BASE_DIR / "logs" / "mesh" / "circuit_breaker.jsonl"


# ═══════════════════════════════════════════════════════
# EXCEPTIONS
# ═══════════════════════════════════════════════════════

class CircuitOpenError(Exception):
    """Raised when a call is blocked because the circuit is OPEN."""

    def __init__(self, node_id: str, retry_after: float) -> None:
        self.node_id     = node_id
        self.retry_after = retry_after
        super().__init__(
            f"Circuit OPEN for node '{node_id}'. "
            f"Retry after {retry_after:.1f}s."
        )


# ═══════════════════════════════════════════════════════
# STATE ENUM
# ═══════════════════════════════════════════════════════

class BreakerStateEnum(str, Enum):
    CLOSED    = "CLOSED"
    OPEN      = "OPEN"
    HALF_OPEN = "HALF_OPEN"


# ═══════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════

@dataclass
class BreakerState:
    """Mutable state for a single node's circuit breaker."""
    node_id:              str
    state:                BreakerStateEnum = BreakerStateEnum.CLOSED
    consecutive_failures: int              = 0
    total_failures:       int              = 0
    total_successes:      int              = 0
    last_failure_time:    float            = 0.0
    opened_at:            float            = 0.0      # when circuit last opened
    half_open_calls:      int              = 0        # calls tried in HALF_OPEN
    lock:                 threading.Lock  = field(
        default_factory=threading.Lock, repr=False, compare=False
    )

    def to_dict(self) -> dict:
        d = asdict(self)
        d["state"] = self.state.value
        d.pop("lock", None)
        return d


# ═══════════════════════════════════════════════════════
# SINGLETON CIRCUIT BREAKER
# ═══════════════════════════════════════════════════════

class MeshCircuitBreaker:
    """
    Per-node circuit breaker for the DOF Mesh.

    Singleton — one instance per process, thread-safe per node.

    Args:
        failure_threshold:    consecutive failures before opening  (default 5)
        recovery_timeout:     seconds in OPEN before going HALF_OPEN (default 60.0)
        half_open_max_calls:  trial calls allowed in HALF_OPEN     (default 3)
    """

    _instance: Optional["MeshCircuitBreaker"] = None
    _class_lock: threading.Lock = threading.Lock()

    def __new__(
        cls,
        failure_threshold:   int   = 5,
        recovery_timeout:    float = 60.0,
        half_open_max_calls: int   = 3,
    ) -> "MeshCircuitBreaker":
        with cls._class_lock:
            if cls._instance is None:
                instance = super().__new__(cls)
                instance._init(failure_threshold, recovery_timeout, half_open_max_calls)
                cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(
        cls,
        failure_threshold:   int   = 5,
        recovery_timeout:    float = 60.0,
        half_open_max_calls: int   = 3,
    ) -> "MeshCircuitBreaker":
        """Factory method — returns singleton (params honoured on first call)."""
        return cls(failure_threshold, recovery_timeout, half_open_max_calls)

    @property
    def state(self):
        """Return the BreakerStateEnum for inspection (uses first known node or CLOSED)."""
        if not self._breakers:
            return BreakerStateEnum.CLOSED
        return list(self._breakers.values())[0].state

    @property
    def failure_count(self) -> int:
        """Return failure_count for the first known node (0 if none)."""
        if not self._breakers:
            return 0
        return list(self._breakers.values())[0].consecutive_failures

    def _init(
        self,
        failure_threshold:   int,
        recovery_timeout:    float,
        half_open_max_calls: int,
    ) -> None:
        """Internal initializer (called once)."""
        self.failure_threshold   = failure_threshold
        self.recovery_timeout    = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self._breakers: dict[str, BreakerState] = {}
        self._registry_lock = threading.Lock()
        self._io_lock       = threading.Lock()
        self._global_open   = False
        BREAKER_LOG.parent.mkdir(parents=True, exist_ok=True)
        logger.info(
            "MeshCircuitBreaker initialized — "
            "threshold=%d  timeout=%.1fs  half_open=%d",
            failure_threshold, recovery_timeout, half_open_max_calls,
        )

    # ── Public API ──────────────────────────────────────

    def call(self, fn_or_node: Any, fn: Optional[Callable] = None, *args: Any, node_id: Optional[str] = None, **kwargs: Any) -> Any:
        """
        Execute fn through the circuit breaker.

        Supports two call styles:
          cb.call("node_id", fn, *args, **kwargs)      # original style
          cb.call(fn, node_id="node_id", **kwargs)     # test-friendly style
        """
        # Resolve fn and node_id from flexible call style
        if callable(fn_or_node):
            actual_fn = fn_or_node
            actual_node = node_id or "default"
            actual_args = args
        else:
            actual_node = str(fn_or_node)
            actual_fn = fn  # type: ignore[assignment]
            actual_args = args

        breaker = self._get_breaker(actual_node)

        with breaker.lock:
            self._maybe_transition(breaker)

            if breaker.state == BreakerStateEnum.OPEN:
                retry_after = max(
                    0.0,
                    (breaker.opened_at + self.recovery_timeout) - time.monotonic(),
                )
                raise CircuitOpenError(actual_node, retry_after)

            if breaker.state == BreakerStateEnum.HALF_OPEN:
                if breaker.half_open_calls >= self.half_open_max_calls:
                    # Exhausted trial budget — reopen
                    self._transition(breaker, BreakerStateEnum.OPEN)
                    raise CircuitOpenError(actual_node, self.recovery_timeout)
                breaker.half_open_calls += 1

        # Execute outside the lock to avoid holding it during I/O
        try:
            result = actual_fn(*actual_args, **kwargs)
        except Exception:
            with breaker.lock:
                self._record_failure(breaker)
            raise

        with breaker.lock:
            self._record_success(breaker)

        return result

    def get_state(self, node_id: str) -> str:
        """Return the current state string for *node_id* (creates entry if absent)."""
        breaker = self._get_breaker(node_id)
        with breaker.lock:
            self._maybe_transition(breaker)
            return breaker.state.value

    def reset(self, node_id: str = "") -> None:
        """Reset circuit. With no args, resets global state. With node_id, resets that node."""
        if not node_id:
            self._global_open = False
            return
        breaker = self._get_breaker(node_id)
        with breaker.lock:
            if breaker.state != BreakerStateEnum.CLOSED:
                self._transition(breaker, BreakerStateEnum.CLOSED)
                breaker.consecutive_failures = 0
                breaker.half_open_calls      = 0
            logger.info("Circuit manually reset for node '%s'", node_id)

    _SENTINEL = object()

    def open(self, reason=_SENTINEL) -> None:
        """Open the global circuit. No args = open. Raises TypeError/ValueError for invalid reason."""
        if reason is not MeshCircuitBreaker._SENTINEL:
            if reason is None or not isinstance(reason, str):
                raise TypeError(f"reason must be a str, got {type(reason).__name__}")
            if reason == "":
                raise ValueError("reason cannot be empty")
        self._global_open = True

    def is_open(self) -> bool:
        """Return True if global circuit is open."""
        return self._global_open

    def is_closed(self) -> bool:
        """Return True if global circuit is closed."""
        return not self._global_open

    # ── Internal state machine ──────────────────────────

    def _get_breaker(self, node_id: str) -> BreakerState:
        """Return (or create) the BreakerState for *node_id*."""
        with self._registry_lock:
            if node_id not in self._breakers:
                self._breakers[node_id] = BreakerState(node_id=node_id)
        return self._breakers[node_id]

    def _maybe_transition(self, breaker: BreakerState) -> None:
        """Check time-based OPEN → HALF_OPEN transition (call inside breaker.lock)."""
        if breaker.state == BreakerStateEnum.OPEN:
            elapsed = time.monotonic() - breaker.opened_at
            if elapsed >= self.recovery_timeout:
                self._transition(breaker, BreakerStateEnum.HALF_OPEN)

    def _record_failure(self, breaker: BreakerState) -> None:
        """Register a failure and potentially open the circuit (call inside breaker.lock)."""
        breaker.consecutive_failures += 1
        breaker.total_failures       += 1
        breaker.last_failure_time     = time.time()

        if breaker.state == BreakerStateEnum.HALF_OPEN:
            # Any failure in HALF_OPEN → reopen immediately
            self._transition(breaker, BreakerStateEnum.OPEN)
        elif (
            breaker.state == BreakerStateEnum.CLOSED
            and breaker.consecutive_failures >= self.failure_threshold
        ):
            self._transition(breaker, BreakerStateEnum.OPEN)

    def _record_success(self, breaker: BreakerState) -> None:
        """Register a success; HALF_OPEN → CLOSED on success (call inside breaker.lock)."""
        breaker.total_successes      += 1
        breaker.consecutive_failures  = 0

        if breaker.state == BreakerStateEnum.HALF_OPEN:
            self._transition(breaker, BreakerStateEnum.CLOSED)
            breaker.half_open_calls = 0

    def _transition(self, breaker: BreakerState, new_state: BreakerStateEnum) -> None:
        """Perform a state transition and log it (call inside breaker.lock)."""
        old_state = breaker.state
        breaker.state = new_state

        if new_state == BreakerStateEnum.OPEN:
            breaker.opened_at            = time.monotonic()
            breaker.half_open_calls      = 0

        event = {
            "event":     "state_transition",
            "node_id":   breaker.node_id,
            "from_state": old_state.value,
            "to_state":   new_state.value,
            "timestamp":  time.time(),
            "consecutive_failures": breaker.consecutive_failures,
            "total_failures":       breaker.total_failures,
            "total_successes":      breaker.total_successes,
        }
        self._log_event(event)
        logger.info(
            "Circuit [%s] %s → %s",
            breaker.node_id, old_state.value, new_state.value,
        )

    def _log_event(self, event: dict) -> None:
        """Append *event* to circuit_breaker.jsonl (thread-safe)."""
        line = json.dumps(event, ensure_ascii=False)
        with self._io_lock:
            try:
                with open(BREAKER_LOG, "a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
            except OSError as exc:
                logger.error("Failed to write circuit breaker log: %s", exc)


# ═══════════════════════════════════════════════════════
# DEMO
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")

    cb = MeshCircuitBreaker(failure_threshold=3, recovery_timeout=2.0, half_open_max_calls=2)

    # Verify singleton
    cb2 = MeshCircuitBreaker()
    assert cb is cb2, "Singleton violated"
    print("Singleton OK")

    # ── Scenario 1: normal calls ──
    def ok_fn(x: int) -> int:
        return x * 2

    print("\n[Scenario 1] Normal calls through CLOSED circuit:")
    for i in range(4):
        result = cb.call("node_a", ok_fn, i)
        print(f"  call({i}) → {result}  state={cb.get_state('node_a')}")

    # ── Scenario 2: failures open the circuit ──
    def fail_fn() -> None:
        raise RuntimeError("simulated failure")

    print("\n[Scenario 2] Inducing failures on node_b (threshold=3):")
    for attempt in range(5):
        try:
            cb.call("node_b", fail_fn)
        except CircuitOpenError as e:
            print(f"  attempt {attempt}: CircuitOpenError — {e}")
        except RuntimeError as e:
            print(f"  attempt {attempt}: RuntimeError({e})  state={cb.get_state('node_b')}")

    # ── Scenario 3: manual reset ──
    print("\n[Scenario 3] Manual reset of node_b:")
    print(f"  before reset: state={cb.get_state('node_b')}")
    cb.reset("node_b")
    print(f"  after  reset: state={cb.get_state('node_b')}")

    # ── Scenario 4: OPEN → HALF_OPEN after recovery_timeout ──
    print("\n[Scenario 4] OPEN → HALF_OPEN after 2 s recovery timeout:")
    for _ in range(3):
        try:
            cb.call("node_c", fail_fn)
        except (CircuitOpenError, RuntimeError):
            pass

    print(f"  state immediately after threshold: {cb.get_state('node_c')}")
    print("  waiting 2.1 s for recovery...")
    time.sleep(2.1)
    print(f"  state after recovery_timeout:      {cb.get_state('node_c')}")

    # One successful call closes it
    cb.call("node_c", ok_fn, 99)
    print(f"  state after successful HALF_OPEN call: {cb.get_state('node_c')}")

    print(f"\nLog written to: {BREAKER_LOG}", file=sys.stderr if not BREAKER_LOG.exists() else sys.stdout)

# Alias for backwards-compat
CircuitState = BreakerStateEnum
