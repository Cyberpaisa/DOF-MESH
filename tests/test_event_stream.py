"""
Tests for core/event_stream.py — EventBus pub/sub system.

All tests are deterministic, no network calls.
"""

import os
import sys
import time
import threading
import unittest
from datetime import datetime, timezone, timedelta

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.event_stream import (
    EventBus,
    EventBackend,
    InMemoryBackend,
    EventType,
    Event,
    ALL_EVENT_TYPES,
    get_event_bus,
    reset_event_bus,
)


class TestPublishEvent(unittest.TestCase):
    """Test basic event publishing."""

    def test_publish_event(self):
        bus = EventBus()
        event = bus.publish("GOVERNANCE_CHECK", {"status": "pass", "score": 0.85},
                            source="constitution")
        self.assertEqual(event.event_type, "GOVERNANCE_CHECK")
        self.assertEqual(event.data["status"], "pass")
        self.assertEqual(event.source, "constitution")
        self.assertIsNotNone(event.event_id)
        self.assertIsInstance(event.timestamp, datetime)

    def test_publish_multiple_types(self):
        bus = EventBus()
        bus.publish("GOVERNANCE_CHECK", {"status": "pass"}, source="gov")
        bus.publish("AST_RESULT", {"passed": True}, source="ast")
        bus.publish("Z3_PROOF", {"verified": True}, source="z3")
        stats = bus.stats()
        self.assertEqual(stats["total"], 3)


class TestSubscribeCallback(unittest.TestCase):
    """Test subscriber callbacks."""

    def test_subscribe_callback(self):
        bus = EventBus()
        received = []
        bus.subscribe("GOVERNANCE_CHECK", lambda e: received.append(e))
        bus.publish("GOVERNANCE_CHECK", {"status": "pass"}, source="test")
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].data["status"], "pass")

    def test_multiple_subscribers(self):
        bus = EventBus()
        received_a = []
        received_b = []
        bus.subscribe("AST_RESULT", lambda e: received_a.append(e))
        bus.subscribe("AST_RESULT", lambda e: received_b.append(e))
        bus.publish("AST_RESULT", {"passed": True}, source="ast")
        self.assertEqual(len(received_a), 1)
        self.assertEqual(len(received_b), 1)

    def test_subscribe_different_types(self):
        bus = EventBus()
        gov_events = []
        ast_events = []
        bus.subscribe("GOVERNANCE_CHECK", lambda e: gov_events.append(e))
        bus.subscribe("AST_RESULT", lambda e: ast_events.append(e))
        bus.publish("GOVERNANCE_CHECK", {"x": 1}, source="gov")
        bus.publish("AST_RESULT", {"y": 2}, source="ast")
        self.assertEqual(len(gov_events), 1)
        self.assertEqual(len(ast_events), 1)


class TestUnsubscribe(unittest.TestCase):
    """Test unsubscribe behavior."""

    def test_unsubscribe(self):
        bus = EventBus()
        received = []
        sub_id = bus.subscribe("GOVERNANCE_CHECK", lambda e: received.append(e))
        bus.publish("GOVERNANCE_CHECK", {"before": True}, source="test")
        self.assertEqual(len(received), 1)

        result = bus.unsubscribe(sub_id)
        self.assertTrue(result)

        bus.publish("GOVERNANCE_CHECK", {"after": True}, source="test")
        self.assertEqual(len(received), 1)  # Should NOT have received second event

    def test_unsubscribe_invalid_id(self):
        bus = EventBus()
        result = bus.unsubscribe("nonexistent-id")
        self.assertFalse(result)


class TestBufferLimit(unittest.TestCase):
    """Test circular buffer respects maxlen."""

    def test_buffer_limit(self):
        backend = InMemoryBackend(maxlen=100)
        bus = EventBus(backend=backend)
        for i in range(150):
            bus.publish("GOVERNANCE_CHECK", {"i": i}, source="test")
        stats = bus.stats()
        self.assertEqual(stats["total"], 100)


class TestReplay(unittest.TestCase):
    """Test replay with time and type filtering."""

    def test_replay_time_filter(self):
        bus = EventBus()
        t0 = datetime.now(timezone.utc)
        bus.publish("GOVERNANCE_CHECK", {"seq": 1}, source="test")
        bus.publish("GOVERNANCE_CHECK", {"seq": 2}, source="test")
        t1 = datetime.now(timezone.utc)

        events = bus.replay(t0 - timedelta(seconds=1), t1 + timedelta(seconds=1))
        self.assertEqual(len(events), 2)

        # Filter out by using a future window
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        events = bus.replay(future, future + timedelta(hours=1))
        self.assertEqual(len(events), 0)

    def test_replay_type_filter(self):
        bus = EventBus()
        t0 = datetime.now(timezone.utc) - timedelta(seconds=1)
        bus.publish("GOVERNANCE_CHECK", {"a": 1}, source="test")
        bus.publish("AST_RESULT", {"b": 2}, source="test")
        bus.publish("GOVERNANCE_CHECK", {"c": 3}, source="test")
        t1 = datetime.now(timezone.utc) + timedelta(seconds=1)

        gov = bus.replay(t0, t1, event_type="GOVERNANCE_CHECK")
        self.assertEqual(len(gov), 2)

        ast = bus.replay(t0, t1, event_type="AST_RESULT")
        self.assertEqual(len(ast), 1)


class TestCount(unittest.TestCase):
    """Test count by type."""

    def test_count_by_type(self):
        bus = EventBus()
        bus.publish("GOVERNANCE_CHECK", {}, source="test")
        bus.publish("GOVERNANCE_CHECK", {}, source="test")
        bus.publish("AST_RESULT", {}, source="test")
        bus.publish("Z3_PROOF", {}, source="test")

        stats = bus.stats()
        self.assertEqual(stats["total"], 4)
        self.assertEqual(stats["by_type"]["GOVERNANCE_CHECK"], 2)
        self.assertEqual(stats["by_type"]["AST_RESULT"], 1)
        self.assertEqual(stats["by_type"]["Z3_PROOF"], 1)


class TestClear(unittest.TestCase):
    """Test clear."""

    def test_clear(self):
        bus = EventBus()
        bus.publish("GOVERNANCE_CHECK", {}, source="test")
        bus.publish("AST_RESULT", {}, source="test")
        self.assertEqual(bus.stats()["total"], 2)
        bus.clear()
        self.assertEqual(bus.stats()["total"], 0)


class TestEventSerialization(unittest.TestCase):
    """Test Event.to_dict()."""

    def test_event_serialization(self):
        event = Event(
            event_id="test-123",
            event_type="GOVERNANCE_CHECK",
            timestamp=datetime(2026, 3, 7, 12, 0, 0, tzinfo=timezone.utc),
            data={"status": "pass", "score": 0.85},
            source="constitution",
            duration_ms=12.5,
        )
        d = event.to_dict()
        self.assertEqual(d["event_id"], "test-123")
        self.assertEqual(d["event_type"], "GOVERNANCE_CHECK")
        self.assertEqual(d["data"]["status"], "pass")
        self.assertEqual(d["source"], "constitution")
        self.assertEqual(d["duration_ms"], 12.5)
        self.assertIn("2026-03-07", d["timestamp"])


class TestThreadSafety(unittest.TestCase):
    """Test concurrent publishing."""

    def test_thread_safety(self):
        bus = EventBus()
        errors = []

        def publisher(thread_id):
            try:
                for i in range(100):
                    bus.publish("GOVERNANCE_CHECK", {"thread": thread_id, "i": i},
                                source=f"thread-{thread_id}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=publisher, args=(t,)) for t in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Thread errors: {errors}")
        self.assertEqual(bus.stats()["total"], 500)


class TestNoBusNoCrash(unittest.TestCase):
    """Test that None bus doesn't affect pipeline."""

    def test_no_bus_no_crash(self):
        reset_event_bus()
        env_backup = os.environ.pop("DOF_EVENT_BUS", None)
        try:
            bus = get_event_bus()
            self.assertIsNone(bus)
            # Pipeline pattern — should not crash
            if bus:
                bus.publish("GOVERNANCE_CHECK", {}, source="test")
        finally:
            if env_backup is not None:
                os.environ["DOF_EVENT_BUS"] = env_backup
            reset_event_bus()


class TestEventTypes(unittest.TestCase):
    """Test EventType constants."""

    def test_all_event_types(self):
        self.assertEqual(len(ALL_EVENT_TYPES), 12)
        self.assertIn("GOVERNANCE_CHECK", ALL_EVENT_TYPES)
        self.assertIn("FACT_CHECK", ALL_EVENT_TYPES)

    def test_event_type_class(self):
        self.assertEqual(EventType.GOVERNANCE_CHECK, "GOVERNANCE_CHECK")
        self.assertEqual(EventType.PRIVACY_CHECK, "PRIVACY_CHECK")
        self.assertEqual(len(EventType.all()), 12)


class TestDOFImport(unittest.TestCase):
    """Test imports from dof package."""

    def test_import_from_dof(self):
        from dof import EventBus, EventBackend, InMemoryBackend, EventType, Event
        self.assertIsNotNone(EventBus)
        self.assertIsNotNone(EventBackend)
        self.assertIsNotNone(InMemoryBackend)
        self.assertIsNotNone(EventType)
        self.assertIsNotNone(Event)


if __name__ == "__main__":
    unittest.main()
