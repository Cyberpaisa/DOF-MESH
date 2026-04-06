"""Tests for core/knowledge_notifier.py"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))


SAMPLE_REPORT = {
    "id_aprobacion": "abc12345",
    "score_dof": 85,
    "relevancia_dof": "alta",
    "resumen_corto": "Google lanzó Gemma 4",
    "ideas_clave": ["Modelos abiertos", "Apache 2.0", "Dispositivos móviles"],
    "tecnologias": ["Gemma 4", "Qwen", "MLX"],
    "tags": ["IA", "Google"],
    "url_video": "https://youtu.be/test",
    "titulo": "Test Video",
    "fecha": "2026-04-05",
    "source_json": "test.json",
    "created_at": "2026-04-05T10:00:00",
    "status": "pending",
}


class TestKnowledgeNotifier(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.report_path = self.tmp / "abc12345.json"
        self.report_path.write_text(json.dumps(SAMPLE_REPORT))

    @patch("core.knowledge_notifier.TELEGRAM_TOKEN", "fake_token")
    @patch("core.knowledge_notifier.TELEGRAM_CHAT_ID", "12345")
    @patch("core.knowledge_notifier._tg_api")
    def test_telegram_success(self, mock_tg):
        from core.knowledge_notifier import _send_telegram
        mock_tg.return_value = {"ok": True}
        self.assertTrue(_send_telegram(SAMPLE_REPORT))
        mock_tg.assert_called_once()

    @patch("core.knowledge_notifier.TELEGRAM_TOKEN", "fake")
    @patch("core.knowledge_notifier.TELEGRAM_CHAT_ID", "12345")
    @patch("core.knowledge_notifier._tg_api", side_effect=Exception("network error"))
    def test_telegram_failure_continues(self, mock_tg):
        from core.knowledge_notifier import _send_telegram
        self.assertFalse(_send_telegram(SAMPLE_REPORT))

    @patch("core.knowledge_notifier.FRONTEND_URL", "http://localhost:19999")
    def test_frontend_failure_continues(self):
        from core.knowledge_notifier import _send_frontend
        self.assertFalse(_send_frontend(SAMPLE_REPORT))

    def test_write_latest(self):
        import core.knowledge_notifier as kn
        original = kn.PENDING_DIR
        kn.PENDING_DIR = self.tmp
        try:
            self.assertTrue(kn._write_latest(SAMPLE_REPORT))
            data = json.loads((self.tmp / "latest.json").read_text())
            self.assertEqual(data["id_aprobacion"], "abc12345")
        finally:
            kn.PENDING_DIR = original

    @patch("core.knowledge_notifier._send_telegram", return_value=True)
    @patch("core.knowledge_notifier._send_frontend", return_value=False)
    @patch("core.knowledge_notifier._write_latest", return_value=True)
    def test_notify_all_channels(self, mock_cr, mock_fe, mock_tg):
        from core.knowledge_notifier import notify
        result = notify(self.report_path)
        self.assertTrue(result["telegram"])
        self.assertFalse(result["frontend"])
        self.assertTrue(result["chrome"])
        self.assertEqual(result["id_aprobacion"], "abc12345")

    @patch("core.knowledge_notifier.TELEGRAM_TOKEN", None)
    def test_no_token_skips_telegram(self):
        from core.knowledge_notifier import _send_telegram
        self.assertFalse(_send_telegram(SAMPLE_REPORT))


if __name__ == "__main__":
    unittest.main()
