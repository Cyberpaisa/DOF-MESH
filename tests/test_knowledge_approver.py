"""Tests for core/knowledge_approver.py"""
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

SAMPLE_REPORT = {
    "id_aprobacion": "def56789",
    "score_dof": 78,
    "relevancia_dof": "alta",
    "resumen_corto": "Gemma 4 lanzado por Google",
    "ideas_clave": ["Modelos abiertos", "Apache 2.0", "On-device"],
    "tecnologias": ["Gemma 4", "Qwen", "MLX"],
    "tags": ["IA", "Google"],
    "url_video": "https://youtu.be/test",
    "titulo": "Google Gemma 4 Launch",
    "fecha": "2026-04-05",
    "source_json": "test.json",
    "created_at": "2026-04-05T10:00:00",
    "status": "pending",
}


class TestApprove(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.pending = self.tmp / "pending"
        self.pending.mkdir()
        self.approved = self.tmp / "approved"
        self.rejected = self.tmp / "rejected"
        self.queue = self.tmp / "queue"
        self.rid = SAMPLE_REPORT["id_aprobacion"]
        (self.pending / f"{self.rid}.json").write_text(
            json.dumps(SAMPLE_REPORT), encoding="utf-8"
        )

    def _patch_dirs(self):
        import core.knowledge_approver as ka
        ka.PENDING_DIR = self.pending
        ka.REJECTED_DIR = self.rejected
        ka.QUEUE_DIR = self.queue
        return ka

    @patch("core.memory_manager.MemoryManager")
    def test_approve_moves_to_approved(self, mock_mm):
        import core.knowledge_approver as ka
        ka.PENDING_DIR = self.pending
        ka.REJECTED_DIR = self.rejected
        ka.QUEUE_DIR = self.queue

        orig_base = ka.BASE_DIR
        ka.BASE_DIR = self.tmp
        try:
            ok = ka.approve(self.rid)
        finally:
            ka.BASE_DIR = orig_base

        self.assertTrue(ok)
        approved_file = self.tmp / "docs" / "knowledge" / "approved" / f"{self.rid}.json"
        self.assertTrue(approved_file.exists())
        data = json.loads(approved_file.read_text())
        self.assertEqual(data["status"], "approved")
        self.assertIn("approved_at", data)
        self.assertFalse((self.pending / f"{self.rid}.json").exists())

    @patch("core.memory_manager.MemoryManager")
    def test_approve_writes_queue_entry(self, mock_mm):
        import core.knowledge_approver as ka
        ka.PENDING_DIR = self.pending
        ka.QUEUE_DIR = self.queue

        orig_base = ka.BASE_DIR
        ka.BASE_DIR = self.tmp
        try:
            ka.approve(self.rid)
        finally:
            ka.BASE_DIR = orig_base

        entries = list(self.queue.glob("*.json"))
        self.assertEqual(len(entries), 1)
        entry = json.loads(entries[0].read_text())
        self.assertIn("approved", entry["id"])
        self.assertEqual(entry["status"], "pending")
        self.assertEqual(entry["from"], "knowledge_approver")

    @patch("core.memory_manager.MemoryManager")
    def test_approve_calls_memory_manager(self, mock_mm_cls):
        import core.knowledge_approver as ka
        ka.PENDING_DIR = self.pending
        ka.QUEUE_DIR = self.queue

        orig_base = ka.BASE_DIR
        ka.BASE_DIR = self.tmp
        try:
            ka.approve(self.rid)
        finally:
            ka.BASE_DIR = orig_base

        mock_mm_cls.return_value.store_long_term.assert_called_once()
        call_kwargs = mock_mm_cls.return_value.store_long_term.call_args
        self.assertIn(f"knowledge:{self.rid}", str(call_kwargs))

    def test_approve_missing_report(self):
        import core.knowledge_approver as ka
        ka.PENDING_DIR = self.pending
        result = ka.approve("nonexistent")
        self.assertFalse(result)

    def test_reject_moves_to_rejected(self):
        import core.knowledge_approver as ka
        ka.PENDING_DIR = self.pending
        ka.REJECTED_DIR = self.rejected

        ok = ka.reject(self.rid)

        self.assertTrue(ok)
        rejected_file = self.rejected / f"{self.rid}.json"
        self.assertTrue(rejected_file.exists())
        data = json.loads(rejected_file.read_text())
        self.assertEqual(data["status"], "rejected")
        self.assertIn("rejected_at", data)
        self.assertFalse((self.pending / f"{self.rid}.json").exists())

    def test_reject_missing_report(self):
        import core.knowledge_approver as ka
        ka.PENDING_DIR = self.pending
        result = ka.reject("nonexistent")
        self.assertFalse(result)


class TestProcessUpdate(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.pending = self.tmp / "pending"
        self.pending.mkdir()
        self.rid = "abc00001"
        (self.pending / f"{self.rid}.json").write_text(
            json.dumps({**SAMPLE_REPORT, "id_aprobacion": self.rid})
        )

    @patch("core.knowledge_approver.approve", return_value=True)
    @patch("core.knowledge_approver._answer_callback")
    def test_process_aprobar_callback(self, mock_answer, mock_approve):
        from core.knowledge_approver import _process_update
        update = {
            "update_id": 1,
            "callback_query": {
                "id": "cq123",
                "data": f"aprobar_{self.rid}",
            }
        }
        result = _process_update(update)
        self.assertTrue(result)
        mock_approve.assert_called_once_with(self.rid)
        mock_answer.assert_called_once_with("cq123", "✅ Aprobado")

    @patch("core.knowledge_approver.reject", return_value=True)
    @patch("core.knowledge_approver._answer_callback")
    def test_process_rechazar_callback(self, mock_answer, mock_reject):
        from core.knowledge_approver import _process_update
        update = {
            "update_id": 2,
            "callback_query": {
                "id": "cq456",
                "data": f"rechazar_{self.rid}",
            }
        }
        result = _process_update(update)
        self.assertTrue(result)
        mock_reject.assert_called_once_with(self.rid)
        mock_answer.assert_called_once_with("cq456", "❌ Rechazado")

    def test_process_non_callback_update(self):
        from core.knowledge_approver import _process_update
        update = {"update_id": 3, "message": {"text": "hello"}}
        result = _process_update(update)
        self.assertFalse(result)

    @patch("core.knowledge_approver.approve", return_value=False)
    @patch("core.knowledge_approver._answer_callback")
    def test_process_not_found_answer(self, mock_answer, mock_approve):
        from core.knowledge_approver import _process_update
        update = {
            "update_id": 4,
            "callback_query": {"id": "cq789", "data": "aprobar_missing123"},
        }
        _process_update(update)
        mock_answer.assert_called_once_with("cq789", "⚠ No encontrado")


class TestOffset(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_offset_default_zero(self):
        import core.knowledge_approver as ka
        orig = ka.OFFSET_FILE
        ka.OFFSET_FILE = self.tmp / "offset.txt"
        try:
            self.assertEqual(ka._get_offset(), 0)
        finally:
            ka.OFFSET_FILE = orig

    def test_offset_save_and_load(self):
        import core.knowledge_approver as ka
        orig = ka.OFFSET_FILE
        ka.OFFSET_FILE = self.tmp / "tg_approver_offset.txt"
        try:
            ka._save_offset(42)
            self.assertEqual(ka._get_offset(), 42)
        finally:
            ka.OFFSET_FILE = orig


if __name__ == "__main__":
    unittest.main()
