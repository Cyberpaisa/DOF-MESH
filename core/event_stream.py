from __future__ import annotations
"""
Event Stream — in-memory pub/sub with circular buffer (Phase 8 preparation).

Current: InMemoryBackend with threading.Lock and deque(maxlen=10_000).
Future: RedisBackend or KafkaBackend when throughput exceeds 1000+ exec/day.

Usage:
    from core.event_stream import EventBus

    bus = EventBus()
    bus.subscribe("GOVERNANCE_CHECK", lambda e: print(e.data))
    bus.publish("GOVERNANCE_CHECK", {"status": "pass", "score": 0.85}, source="constitution")

    # Replay events
    events = bus.replay(from_ts=start, to_ts=end, event_type="GOVERNANCE_CHECK")

    # Stats
    print(bus.stats())  # {total: 1, by_type: {"GOVERNANCE_CHECK": 1}, ...}
"""

import os
import uuid
import logging
import threading
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Callable

logger = logging.getLogger("core.event_stream")

# ─────────────────────────────────────────────────────────────────────
# Event Types
# ─────────────────────────────────────────────────────────────────────

GOVERNANCE_CHECK = "GOVERNANCE_CHECK"
AST_RESULT = "AST_RESULT"
Z3_PROOF = "Z3_PROOF"
ATTESTATION_CREATED = "ATTESTATION_CREATED"
ATTESTATION_PUBLISHED = "ATTESTATION_PUBLISHED"
PROVIDER_FAILURE = "PROVIDER_FAILURE"
RETRY_TRIGGERED = "RETRY_TRIGGERED"
LOOP_DETECTED = "LOOP_DETECTED"
MEMORY_WRITE = "MEMORY_WRITE"
BENCHMARK_COMPLETE = "BENCHMARK_COMPLETE"
PRIVACY_CHECK = "PRIVACY_CHECK"
FACT_CHECK = "FACT_CHECK"

ALL_EVENT_TYPES = [
    GOVERNANCE_CHECK, AST_RESULT, Z3_PROOF,
    ATTESTATION_CREATED, ATTESTATION_PUBLISHED,
    PROVIDER_FAILURE, RETRY_TRIGGERED, LOOP_DETECTED,
    MEMORY_WRITE, BENCHMARK_COMPLETE, PRIVACY_CHECK, FACT_CHECK,
]


class EventType:
    """Namespace for event type constants."""
    GOVERNANCE_CHECK = GOVERNANCE_CHECK
    AST_RESULT = AST_RESULT
    Z3_PROOF = Z3_PROOF
    ATTESTATION_CREATED = ATTESTATION_CREATED
    ATTESTATION_PUBLISHED = ATTESTATION_PUBLISHED
    PROVIDER_FAILURE = PROVIDER_FAILURE
    RETRY_TRIGGERED = RETRY_TRIGGERED
    LOOP_DETECTED = LOOP_DETECTED
    MEMORY_WRITE = MEMORY_WRITE
    BENCHMARK_COMPLETE = BENCHMARK_COMPLETE
    PRIVACY_CHECK = PRIVACY_CHECK
    FACT_CHECK = FACT_CHECK

    @classmethod
    def all(cls) -> list[str]:
        """Return all event type strings."""
        return list(ALL_EVENT_TYPES)


# ─────────────────────────────────────────────────────────────────────
# Event
# ─────────────────────────────────────────────────────────────────────

@dataclass
class Event:
    """A single event in the stream."""
    event_id: str
    event_type: str
    timestamp: datetime
    data: dict
    source: str
    duration_ms: float = 0.0

    def to_dict(self) -> dict:
        """Serialize to dict for JSONL or API output."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "source": self.source,
            "duration_ms": self.duration_ms,
        }


# ─────────────────────────────────────────────────────────────────────
# Abstract Backend
# ─────────────────────────────────────────────────────────────────────

class EventBackend(ABC):
    """Abstract base class for event backends."""

    @abstractmethod
    def publish(self, event: Event) -> bool:
        """Publish an event. Returns True on success."""
        ...

    @abstractmethod
    def subscribe(self, event_type: str, callback: Callable[[Event], None]) -> str:
        """Subscribe to events of a given type. Returns subscription_id."""
        ...

    @abstractmethod
    def unsubscribe(self, subscription_id: str) -> bool:
        """Remove a subscription. Returns True if found and removed."""
        ...

    @abstractmethod
    def replay(self, from_ts: datetime, to_ts: datetime,
               event_type: str | None = None) -> list[Event]:
        """Replay events within a time range, optionally filtered by type."""
        ...

    @abstractmethod
    def count(self, event_type: str | None = None) -> int:
        """Count events, optionally filtered by type."""
        ...

    @abstractmethod
    def clear(self) -> None:
        """Clear all events from the buffer."""
        ...


# ─────────────────────────────────────────────────────────────────────
# In-Memory Backend
# ─────────────────────────────────────────────────────────────────────

DEFAULT_BUFFER_SIZE = 10_000


class InMemoryBackend(EventBackend):
    """Thread-safe in-memory backend with circular buffer."""

    def __init__(self, maxlen: int = DEFAULT_BUFFER_SIZE):
        self._buffer: deque[Event] = deque(maxlen=maxlen)
        self._subscriptions: dict[str, list[tuple[str, Callable]]] = {}
        self._sub_index: dict[str, tuple[str, Callable]] = {}
        self._lock = threading.Lock()

    def publish(self, event: Event) -> bool:
        if event is None:
            logger.warning("InMemoryBackend.publish() called with None — ignoring")
            return False
        with self._lock:
            self._buffer.append(event)
            callbacks = []
            for sub_id, cb in self._subscriptions.get(event.event_type, []):
                callbacks.append(cb)
        # Call subscribers outside lock to avoid deadlocks
        for cb in callbacks:
            try:
                cb(event)
            except Exception as e:
                logger.warning(f"Subscriber error for {event.event_type}: {e}")
        return True

    def subscribe(self, event_type: str, callback: Callable[[Event], None]) -> str:
        sub_id = str(uuid.uuid4())
        with self._lock:
            if event_type not in self._subscriptions:
                self._subscriptions[event_type] = []
            entry = (sub_id, callback)
            self._subscriptions[event_type].append(entry)
            self._sub_index[sub_id] = (event_type, callback)
        return sub_id

    def unsubscribe(self, subscription_id: str) -> bool:
        with self._lock:
            if subscription_id not in self._sub_index:
                return False
            event_type, callback = self._sub_index.pop(subscription_id)
            subs = self._subscriptions.get(event_type, [])
            self._subscriptions[event_type] = [
                (sid, cb) for sid, cb in subs if sid != subscription_id
            ]
            return True

    def replay(self, from_ts: datetime, to_ts: datetime,
               event_type: str | None = None) -> list[Event]:
        with self._lock:
            results = []
            for event in self._buffer:
                if event.timestamp < from_ts or event.timestamp > to_ts:
                    continue
                if event_type and event.event_type != event_type:
                    continue
                results.append(event)
            return results

    def count(self, event_type: str | None = None) -> int:
        with self._lock:
            if event_type is None:
                return len(self._buffer)
            return sum(1 for e in self._buffer if e.event_type == event_type)

    def clear(self) -> None:
        with self._lock:
            self._buffer.clear()


# ─────────────────────────────────────────────────────────────────────
# Phase 8 Placeholders
# ─────────────────────────────────────────────────────────────────────

# class RedisBackend(EventBackend):
#     """Phase 8: Connect to Redis Streams when 1000+ exec/day."""
#     pass
#
# class KafkaBackend(EventBackend):
#     """Phase 8: Connect to Kafka when 10,000+ exec/day."""
#     pass


# ─────────────────────────────────────────────────────────────────────
# EventBus
# ─────────────────────────────────────────────────────────────────────

class EventBus:
    """High-level pub/sub event bus for DOF governance pipeline.

    Uses InMemoryBackend by default. Swap to RedisBackend or KafkaBackend
    in Phase 8 for distributed deployments.
    """

    def __init__(self, backend: EventBackend | None = None):
        self._backend = backend or InMemoryBackend()

    def publish(self, event_type: str, data: dict,
                source: str = "unknown", duration_ms: float = 0.0) -> Event:
        """Create and publish an event.

        Args:
            event_type: One of EventType constants
            data: Event payload dict
            source: Module/component that emitted the event
            duration_ms: Optional duration in milliseconds

        Returns:
            The created Event.
        """
        event = Event(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            data=data,
            source=source,
            duration_ms=duration_ms,
        )
        self._backend.publish(event)
        return event

    def subscribe(self, event_type: str,
                  callback: Callable[[Event], None]) -> str:
        """Subscribe to events of a given type.

        Returns:
            subscription_id for later unsubscribe.
        """
        return self._backend.subscribe(event_type, callback)

    def unsubscribe(self, subscription_id: str) -> bool:
        """Remove a subscription."""
        return self._backend.unsubscribe(subscription_id)

    def replay(self, from_ts: datetime, to_ts: datetime,
               event_type: str | None = None) -> list[Event]:
        """Replay events within a time range."""
        return self._backend.replay(from_ts, to_ts, event_type)

    def stats(self) -> dict:
        """Return event statistics."""
        by_type = {}
        for et in ALL_EVENT_TYPES:
            c = self._backend.count(et)
            if c > 0:
                by_type[et] = c

        total = self._backend.count()

        return {
            "total": total,
            "by_type": by_type,
        }

    def clear(self) -> None:
        """Clear all events from the buffer."""
        self._backend.clear()


# ─────────────────────────────────────────────────────────────────────
# Module-level singleton (opt-in via DOF_EVENT_BUS=true)
# ─────────────────────────────────────────────────────────────────────

_bus_instance: EventBus | None = None


def get_event_bus() -> EventBus | None:
    """Get the module-level EventBus singleton.

    Returns None if DOF_EVENT_BUS is not set to 'true'.
    Pattern for use in modules:
        bus = get_event_bus()
        if bus:
            bus.publish("GOVERNANCE_CHECK", {"status": "pass"}, source="governance")
    """
    global _bus_instance
    if os.environ.get("DOF_EVENT_BUS", "").lower() == "true":
        if _bus_instance is None:
            _bus_instance = EventBus()
            logger.info("EventBus initialized (DOF_EVENT_BUS=true)")
        return _bus_instance
    return None


def reset_event_bus() -> None:
    """Reset the singleton (for testing)."""
    global _bus_instance
    _bus_instance = None
