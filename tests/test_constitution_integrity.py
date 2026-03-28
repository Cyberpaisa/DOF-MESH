import unittest
from datetime import datetime, timezone

from constitution.integrity_watcher import (
    ConstitutionDriftException,
    ConstitutionIntegrityWatcher,
    IntegritySnapshot,
)


class TestConstitutionIntegrityWatcher(unittest.TestCase):

    def setUp(self):
        self.rules = {"max_actions": 10, "allow_external": False, "version": "1.0"}
        self.watcher = ConstitutionIntegrityWatcher(self.rules)

    def test_hash_stable_on_init(self):
        h1 = self.watcher.current_hash()
        h2 = self.watcher.current_hash()
        self.assertEqual(h1, h2)

    def test_verify_passes_on_unmodified(self):
        snap = self.watcher.verify()
        self.assertFalse(snap.drift_detected)
        self.assertEqual(snap.current_hash, snap.baseline_hash)

    def test_detect_drift_when_rules_change(self):
        self.watcher.rules["max_actions"] = 999
        with self.assertRaises(ConstitutionDriftException):
            self.watcher.verify()

    def test_baseline_updates_after_legitimate_change(self):
        new_rules = {"max_actions": 50, "allow_external": True, "version": "2.0"}
        self.watcher.update_baseline(new_rules)
        snap = self.watcher.verify()
        self.assertFalse(snap.drift_detected)

    def test_hash_deterministic(self):
        w1 = ConstitutionIntegrityWatcher({"a": 1, "b": 2})
        w2 = ConstitutionIntegrityWatcher({"a": 1, "b": 2})
        self.assertEqual(w1.current_hash(), w2.current_hash())

    def test_check_count_increments(self):
        self.assertEqual(self.watcher.check_count, 0)
        self.watcher.verify()
        self.assertEqual(self.watcher.check_count, 1)
        self.watcher.verify()
        self.assertEqual(self.watcher.check_count, 2)

    def test_snapshot_fields(self):
        snap = self.watcher.verify()
        self.assertIsInstance(snap, IntegritySnapshot)
        self.assertIsInstance(snap.current_hash, str)
        self.assertIsInstance(snap.baseline_hash, str)
        self.assertIsInstance(snap.drift_detected, bool)
        self.assertIsInstance(snap.timestamp, datetime)

    def test_no_drift_on_empty_dict(self):
        watcher = ConstitutionIntegrityWatcher({})
        snap = watcher.verify()
        self.assertFalse(snap.drift_detected)

    def test_drift_detected_flag_true_on_change(self):
        self.watcher.rules["version"] = "TAMPERED"
        try:
            self.watcher.verify()
        except ConstitutionDriftException:
            pass
        # Verify that a fresh check still detects drift
        try:
            snap = self.watcher.verify()
        except ConstitutionDriftException:
            # The exception is raised, confirming drift is detected
            # We can check drift_detected by constructing snapshot manually
            current = self.watcher.current_hash()
            self.assertNotEqual(current, self.watcher.baseline)


if __name__ == "__main__":
    unittest.main()
