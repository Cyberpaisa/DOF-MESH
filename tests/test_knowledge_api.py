"""Tests for core/knowledge_api.py"""
import json
import socket as _socket
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

pytestmark = [pytest.mark.integration, pytest.mark.optional]

def _free_port() -> int:
    with _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


TEST_PORT: int | None = None

SAMPLE_REPORT = {
    "id_aprobacion": "api00001",
    "score_dof": 72,
    "relevancia_dof": "media",
    "resumen_corto": "Test video",
    "ideas_clave": ["idea 1", "idea 2"],
    "tecnologias": ["Python", "Ollama"],
    "tags": ["test"],
    "url_video": "https://youtu.be/test",
    "titulo": "Test Video API",
    "fecha": "2026-04-05",
    "source_json": "test.json",
    "created_at": "2026-04-05T10:00:00",
    "status": "pending",
}


def _get(path: str) -> tuple[int, dict]:
    if TEST_PORT is None:
        raise RuntimeError("TEST_PORT not initialized")
    url = f"http://127.0.0.1:{TEST_PORT}{path}"
    try:
        with urllib.request.urlopen(url, timeout=3) as r:
            return r.status, json.loads(r.read())
    except urllib.request.HTTPError as e:
        return e.code, json.loads(e.read())


def _post(path: str) -> tuple[int, dict]:
    if TEST_PORT is None:
        raise RuntimeError("TEST_PORT not initialized")
    url = f"http://127.0.0.1:{TEST_PORT}{path}"
    req = urllib.request.Request(url, data=b"", method="POST")
    try:
        with urllib.request.urlopen(req, timeout=3) as r:
            return r.status, json.loads(r.read())
    except urllib.request.HTTPError as e:
        return e.code, json.loads(e.read())


class TestKnowledgeAPI(unittest.TestCase):
    """Integration tests — starts a real server on TEST_PORT."""

    @classmethod
    def setUpClass(cls):
        global TEST_PORT
        try:
            TEST_PORT = _free_port()
        except PermissionError as exc:
            raise unittest.SkipTest(
                "Integration test requires local port binding permissions"
            ) from exc

        cls.tmp = Path(tempfile.mkdtemp())
        cls.pending_dir = cls.tmp / "docs" / "knowledge" / "pending"
        cls.pending_dir.mkdir(parents=True)

        import core.knowledge_api as api_mod
        api_mod.PENDING_DIR = cls.pending_dir

        from core.knowledge_api import KnowledgeHandler
        from http.server import HTTPServer
        try:
            cls.server = HTTPServer(("127.0.0.1", TEST_PORT), KnowledgeHandler)
        except PermissionError as exc:
            raise unittest.SkipTest(
                "Integration test requires local HTTP server binding permissions"
            ) from exc
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.1)  # give server time to bind

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        # clean pending dir between tests
        for f in self.pending_dir.glob("*.json"):
            f.unlink()

    # ── GET /health ──────────────────────────────────────────────────

    def test_health(self):
        code, body = _get("/health")
        self.assertEqual(code, 200)
        self.assertEqual(body["status"], "ok")

    # ── GET /latest ──────────────────────────────────────────────────

    def test_latest_empty(self):
        code, body = _get("/latest")
        self.assertEqual(code, 404)
        self.assertIn("error", body)

    def test_latest_returns_report(self):
        (self.pending_dir / "latest.json").write_text(
            json.dumps(SAMPLE_REPORT), encoding="utf-8"
        )
        code, body = _get("/latest")
        self.assertEqual(code, 200)
        self.assertEqual(body["id_aprobacion"], "api00001")

    # ── GET /pending ─────────────────────────────────────────────────

    def test_pending_empty(self):
        code, body = _get("/pending")
        self.assertEqual(code, 200)
        self.assertIsInstance(body, list)
        self.assertEqual(len(body), 0)

    def test_pending_lists_reports(self):
        for i in range(3):
            r = {**SAMPLE_REPORT, "id_aprobacion": f"rpt0000{i}"}
            (self.pending_dir / f"rpt0000{i}.json").write_text(json.dumps(r))
        # latest.json should be excluded
        (self.pending_dir / "latest.json").write_text(json.dumps(SAMPLE_REPORT))
        code, body = _get("/pending")
        self.assertEqual(code, 200)
        self.assertEqual(len(body), 3)
        ids = {r["id_aprobacion"] for r in body}
        self.assertNotIn("api00001", ids)  # latest.json excluded

    # ── POST /approve + /reject ──────────────────────────────────────

    def test_approve_not_found(self):
        code, body = _post("/approve/missing1")
        self.assertEqual(code, 404)

    def test_reject_not_found(self):
        code, body = _post("/reject/missing2")
        self.assertEqual(code, 404)

    def test_invalid_rid_rejected(self):
        # rid with special chars should return 400
        code, body = _post("/approve/../../etc")
        # The handler strips the path, leaving "..": not alnum → 400
        self.assertIn(code, [400, 404])

    def test_approve_existing_report(self):
        rid = SAMPLE_REPORT["id_aprobacion"]
        (self.pending_dir / f"{rid}.json").write_text(
            json.dumps(SAMPLE_REPORT), encoding="utf-8"
        )
        from unittest.mock import patch
        with patch("core.knowledge_approver.approve", return_value=True) as mock_ap:
            code, body = _post(f"/approve/{rid}")
        self.assertEqual(code, 200)
        self.assertEqual(body["rid"], rid)

    def test_reject_existing_report(self):
        rid = SAMPLE_REPORT["id_aprobacion"]
        (self.pending_dir / f"{rid}.json").write_text(
            json.dumps(SAMPLE_REPORT), encoding="utf-8"
        )
        from unittest.mock import patch
        with patch("core.knowledge_approver.reject", return_value=True) as mock_rj:
            code, body = _post(f"/reject/{rid}")
        self.assertEqual(code, 200)

    # ── Unknown routes ───────────────────────────────────────────────

    def test_unknown_get(self):
        code, body = _get("/nonexistent")
        self.assertEqual(code, 404)

    def test_unknown_post(self):
        code, body = _post("/nonexistent")
        self.assertEqual(code, 404)


if __name__ == "__main__":
    unittest.main()
