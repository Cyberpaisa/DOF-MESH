"""Tests for WriteAheadLog."""
import os
import tempfile
import threading
import unittest
from core.dof_wal import WriteAheadLog, WALEntry


class TestWALEntry(unittest.TestCase):

    def test_checksum_valid(self):
        cs = WALEntry.compute_checksum(1, "enqueue", "t1", {"x": 1})
        entry = WALEntry(1, 0.0, "enqueue", "t1", {"x": 1}, cs)
        self.assertTrue(entry.is_valid())

    def test_checksum_invalid(self):
        entry = WALEntry(1, 0.0, "enqueue", "t1", {"x": 1}, "bad")
        self.assertFalse(entry.is_valid())

    def test_to_from_dict(self):
        cs = WALEntry.compute_checksum(5, "complete", "k", {})
        e = WALEntry(5, 1.0, "complete", "k", {}, cs, confirmed=True)
        d = e.to_dict()
        e2 = WALEntry.from_dict(d)
        self.assertEqual(e2.seq, 5)
        self.assertTrue(e2.confirmed)


class TestWriteAheadLog(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.wal = WriteAheadLog(os.path.join(self.tmpdir, "wal"))

    def tearDown(self):
        self.wal.close()
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_append_returns_seq(self):
        seq = self.wal.append("enqueue", "t1", {"prompt": "hello"})
        self.assertEqual(seq, 1)
        seq2 = self.wal.append("enqueue", "t2", {})
        self.assertEqual(seq2, 2)

    def test_recover_returns_unconfirmed(self):
        self.wal.append("enqueue", "t1", {})
        self.wal.append("enqueue", "t2", {})
        entries = self.wal.recover()
        self.assertEqual(len(entries), 2)

    def test_confirm_removes_from_recover(self):
        seq = self.wal.append("enqueue", "t1", {})
        self.wal.append("enqueue", "t2", {})
        self.wal.confirm(seq)
        entries = self.wal.recover()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].key, "t2")

    def test_compact_removes_confirmed(self):
        s1 = self.wal.append("enqueue", "t1", {})
        self.wal.append("enqueue", "t2", {})
        self.wal.confirm(s1)
        removed = self.wal.compact()
        self.assertEqual(removed, 1)
        self.assertEqual(self.wal.size(), 1)

    def test_recover_after_reopen(self):
        self.wal.append("enqueue", "t1", {"data": "important"})
        self.wal.close()

        # Reopen — simula crash recovery
        wal2 = WriteAheadLog(os.path.join(self.tmpdir, "wal"))
        entries = wal2.recover()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].key, "t1")
        self.assertEqual(entries[0].data["data"], "important")

    def test_seq_continues_after_reopen(self):
        self.wal.append("enqueue", "t1", {})
        self.wal.close()
        wal2 = WriteAheadLog(os.path.join(self.tmpdir, "wal"))
        seq = wal2.append("enqueue", "t2", {})
        self.assertEqual(seq, 2)

    def test_checksum_validates(self):
        self.wal.append("enqueue", "t1", {"x": 1})
        entries = self.wal.recover()
        self.assertTrue(entries[0].is_valid())

    def test_concurrent_appends(self):
        results = []
        def worker():
            for _ in range(10):
                seq = self.wal.append("enqueue", "t", {})
                results.append(seq)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(results), 50)
        self.assertEqual(len(set(results)), 50)  # all seqs unique

    def test_size(self):
        self.wal.append("enqueue", "t1", {})
        self.wal.append("enqueue", "t2", {})
        self.assertEqual(self.wal.size(), 2)


if __name__ == "__main__":
    unittest.main()
