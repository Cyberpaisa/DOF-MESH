"""Tests para Constitution Hash Beacon."""
import unittest
from datetime import datetime, timezone

from constitution.hash_beacon import (
    BeaconEntry,
    ConstitutionHashBeacon,
    NodeSyncStatus,
)


class TestBeaconPublish(unittest.TestCase):
    def setUp(self):
        self.beacon = ConstitutionHashBeacon(beacon_interval=50)
        self.rules = {"no_hallucination": True, "max_length": 50000}

    def test_no_beacon_on_init(self):
        self.assertEqual(self.beacon.beacon_count, 0)

    def test_publish_creates_beacon(self):
        self.beacon.publish(self.rules, block_number=50, publisher="node-1")
        self.assertEqual(self.beacon.beacon_count, 1)

    def test_beacon_has_correct_hash(self):
        entry = self.beacon.publish(self.rules, block_number=50, publisher="node-1")
        expected_hash = self.beacon._compute_hash(self.rules)
        self.assertEqual(entry.state_hash, expected_hash)

    def test_epoch_increments(self):
        for i in range(3):
            self.beacon.publish(self.rules, block_number=(i + 1) * 50, publisher="node-1")
        self.assertEqual(self.beacon.current_epoch, 3)

    def test_latest_beacon(self):
        self.assertIsNone(self.beacon.latest_beacon())
        entry1 = self.beacon.publish(self.rules, block_number=50, publisher="node-1")
        entry2 = self.beacon.publish(self.rules, block_number=100, publisher="node-1")
        self.assertEqual(self.beacon.latest_beacon(), entry2)

    def test_should_publish_at_interval(self):
        self.assertTrue(self.beacon.should_publish(50))
        self.assertTrue(self.beacon.should_publish(100))
        self.assertTrue(self.beacon.should_publish(150))
        self.assertFalse(self.beacon.should_publish(25))
        self.assertFalse(self.beacon.should_publish(73))


class TestNodeSync(unittest.TestCase):
    def setUp(self):
        self.beacon = ConstitutionHashBeacon(beacon_interval=50)
        self.rules = {"no_hallucination": True, "max_length": 50000}

    def test_synced_with_correct_hash(self):
        entry = self.beacon.publish(self.rules, block_number=50, publisher="node-1")
        status = self.beacon.check_sync("node-2", local_hash=entry.state_hash)
        self.assertEqual(status, NodeSyncStatus.SYNCED)

    def test_halted_with_wrong_hash(self):
        self.beacon.publish(self.rules, block_number=50, publisher="node-1")
        status = self.beacon.check_sync("node-2", local_hash="wrong_hash_value")
        self.assertEqual(status, NodeSyncStatus.HALTED)

    def test_pending_without_beacon(self):
        status = self.beacon.check_sync("node-2", local_hash="any_hash")
        self.assertEqual(status, NodeSyncStatus.PENDING)

    def test_acknowledge_sync(self):
        self.beacon.publish(self.rules, block_number=50, publisher="node-1")
        self.beacon.check_sync("node-2", local_hash="wrong_hash")
        self.assertEqual(self.beacon.get_node_status("node-2"), NodeSyncStatus.HALTED)
        self.beacon.acknowledge_sync("node-2")
        self.assertEqual(self.beacon.get_node_status("node-2"), NodeSyncStatus.SYNCED)

    def test_all_synced(self):
        entry = self.beacon.publish(self.rules, block_number=50, publisher="node-1")
        self.beacon.check_sync("node-2", local_hash=entry.state_hash)
        self.beacon.check_sync("node-3", local_hash=entry.state_hash)
        self.assertTrue(self.beacon.all_synced())

    def test_all_synced_false(self):
        entry = self.beacon.publish(self.rules, block_number=50, publisher="node-1")
        self.beacon.check_sync("node-2", local_hash=entry.state_hash)
        self.beacon.check_sync("node-3", local_hash="wrong_hash")
        self.assertFalse(self.beacon.all_synced())

    def test_halted_nodes_list(self):
        entry = self.beacon.publish(self.rules, block_number=50, publisher="node-1")
        self.beacon.check_sync("node-2", local_hash=entry.state_hash)
        self.beacon.check_sync("node-3", local_hash="wrong_hash")
        self.beacon.check_sync("node-4", local_hash="also_wrong")
        halted = self.beacon.halted_nodes()
        self.assertIn("node-3", halted)
        self.assertIn("node-4", halted)
        self.assertNotIn("node-2", halted)


class TestBeaconHistory(unittest.TestCase):
    def setUp(self):
        self.beacon = ConstitutionHashBeacon(beacon_interval=50)
        self.rules = {"no_hallucination": True, "max_length": 50000}

    def test_multiple_beacons_stored(self):
        for i in range(5):
            self.beacon.publish(self.rules, block_number=(i + 1) * 50, publisher="node-1")
        self.assertEqual(self.beacon.beacon_count, 5)

    def test_beacon_entry_fields(self):
        entry = self.beacon.publish(self.rules, block_number=50, publisher="node-1")
        self.assertIsInstance(entry, BeaconEntry)
        self.assertEqual(entry.epoch, 1)
        self.assertIsInstance(entry.state_hash, str)
        self.assertEqual(entry.block_number, 50)
        self.assertIsInstance(entry.timestamp, datetime)
        self.assertEqual(entry.publisher_node, "node-1")


if __name__ == "__main__":
    unittest.main()
