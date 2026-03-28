"""Tests para CRDT Memory Layer."""
import unittest
from datetime import datetime, timezone, timedelta

from core.crdt_memory import (
    CRDTMemoryStore,
    GCounter,
    LWWRegister,
)


class TestGCounter(unittest.TestCase):
    def setUp(self):
        self.counter = GCounter()

    def test_empty_counter_zero(self):
        self.assertEqual(self.counter.value(), 0)

    def test_increment_single_node(self):
        self.counter.increment("node-1")
        self.assertEqual(self.counter.value(), 1)

    def test_increment_multiple_nodes(self):
        self.counter.increment("node-1")
        self.counter.increment("node-2")
        self.assertEqual(self.counter.value(), 2)

    def test_increment_amount(self):
        self.counter.increment("node-1", amount=5)
        self.assertEqual(self.counter.node_value("node-1"), 5)

    def test_negative_increment_raises(self):
        with self.assertRaises(ValueError):
            self.counter.increment("node-1", amount=-1)

    def test_merge_takes_max(self):
        other = GCounter()
        self.counter.increment("node-1", amount=3)
        other.increment("node-1", amount=5)
        self.counter.merge(other)
        self.assertEqual(self.counter.node_value("node-1"), 5)

    def test_merge_adds_new_nodes(self):
        other = GCounter()
        self.counter.increment("node-1")
        other.increment("node-2", amount=3)
        self.counter.merge(other)
        self.assertEqual(self.counter.node_value("node-2"), 3)
        self.assertEqual(self.counter.value(), 4)


class TestLWWRegister(unittest.TestCase):
    def setUp(self):
        self.register = LWWRegister()

    def test_empty_read_none(self):
        self.assertIsNone(self.register.read())

    def test_write_and_read(self):
        self.register.write("active", "node-1")
        self.assertEqual(self.register.read(), "active")

    def test_latest_write_wins(self):
        ts1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
        ts2 = datetime(2026, 1, 2, tzinfo=timezone.utc)
        self.register.write("a", "node-1", timestamp=ts1)
        self.register.write("b", "node-2", timestamp=ts2)
        self.assertEqual(self.register.read(), "b")

    def test_older_write_ignored(self):
        ts1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
        ts2 = datetime(2026, 1, 2, tzinfo=timezone.utc)
        self.register.write("b", "node-2", timestamp=ts2)
        self.register.write("a", "node-1", timestamp=ts1)
        self.assertEqual(self.register.read(), "b")

    def test_merge_takes_latest(self):
        other = LWWRegister()
        ts1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
        ts2 = datetime(2026, 1, 2, tzinfo=timezone.utc)
        self.register.write("old", "node-1", timestamp=ts1)
        other.write("new", "node-2", timestamp=ts2)
        self.register.merge(other)
        self.assertEqual(self.register.read(), "new")

    def test_last_writer_tracked(self):
        self.register.write("value", "node-3")
        self.assertEqual(self.register.last_writer, "node-3")


class TestCRDTStore(unittest.TestCase):
    def setUp(self):
        self.store = CRDTMemoryStore()

    def test_counter_and_register_independent(self):
        self.store.increment_counter("hits", "node-1")
        self.store.set_register("status", "active", "node-1")
        self.assertEqual(self.store.counter_value("hits"), 1)
        self.assertEqual(self.store.get_register("status"), "active")

    def test_store_merge(self):
        other = CRDTMemoryStore()
        self.store.increment_counter("hits", "node-1", amount=3)
        other.increment_counter("hits", "node-1", amount=5)
        other.increment_counter("hits", "node-2", amount=2)
        ts1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
        ts2 = datetime(2026, 1, 2, tzinfo=timezone.utc)
        self.store.set_register("status", "old", "node-1", timestamp=ts1)
        other.set_register("status", "new", "node-2", timestamp=ts2)
        self.store.merge_store(other)
        self.assertEqual(self.store.counter_value("hits"), 7)  # max(3,5) + 2
        self.assertEqual(self.store.get_register("status"), "new")

    def test_counter_names(self):
        self.store.increment_counter("a", "node-1")
        self.store.increment_counter("b", "node-1")
        self.assertIn("a", self.store.counter_names)
        self.assertIn("b", self.store.counter_names)

    def test_register_keys(self):
        self.store.set_register("key1", "val1", "node-1")
        self.store.set_register("key2", "val2", "node-1")
        self.assertIn("key1", self.store.register_keys)
        self.assertIn("key2", self.store.register_keys)

    def test_nonexistent_counter_zero(self):
        self.assertEqual(self.store.counter_value("nope"), 0)

    def test_nonexistent_register_none(self):
        self.assertIsNone(self.store.get_register("nope"))


if __name__ == "__main__":
    unittest.main()
