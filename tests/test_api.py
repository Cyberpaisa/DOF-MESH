"""Tests for DOF REST API — FastAPI endpoints."""

import json
import os
import sys
import tempfile
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

try:
    from fastapi.testclient import TestClient
    from api.server import app
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False


@unittest.skipUnless(HAS_FASTAPI, "fastapi not installed")
class TestHealthEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health(self):
        r = self.client.get("/api/v1/health")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["version"], "0.5.0")
        self.assertIn("tests", data)
        self.assertIn("modules", data)


@unittest.skipUnless(HAS_FASTAPI, "fastapi not installed")
class TestGovernanceEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_governance_pass(self):
        r = self.client.post("/api/v1/governance/verify", json={
            "output_text": "The analysis shows Python grew 15% in 2024. Sources: Stack Overflow Survey."
        })
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["status"], "pass")
        self.assertIn("score", data)

    def test_governance_fail_empty(self):
        r = self.client.post("/api/v1/governance/verify", json={"output_text": ""})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["status"], "fail")
        self.assertTrue(len(data["hard_violations"]) > 0)

    def test_governance_schema(self):
        r = self.client.post("/api/v1/governance/verify", json={"output_text": "test"})
        data = r.json()
        for key in ("status", "hard_violations", "soft_violations", "score"):
            self.assertIn(key, data)


@unittest.skipUnless(HAS_FASTAPI, "fastapi not installed")
class TestASTEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_ast_clean_code(self):
        r = self.client.post("/api/v1/ast/verify", json={
            "code": "def add(a, b):\n    return a + b\n"
        })
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["score"], 1.0)
        self.assertTrue(data["passed"])

    def test_ast_unsafe_code(self):
        r = self.client.post("/api/v1/ast/verify", json={
            "code": "import subprocess\nsubprocess.call('rm -rf /')\n"
        })
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertFalse(data["passed"])
        self.assertTrue(len(data["violations"]) > 0)


@unittest.skipUnless(HAS_FASTAPI, "fastapi not installed")
class TestZ3Endpoint(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_z3_verify(self):
        r = self.client.get("/api/v1/z3/verify")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data["all_verified"])
        self.assertGreaterEqual(data["count"], 4)
        for t in data["theorems"]:
            self.assertEqual(t["result"], "VERIFIED")


@unittest.skipUnless(HAS_FASTAPI, "fastapi not installed")
class TestMemoryEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self._tmpdir = tempfile.mkdtemp()
        import core.memory_governance as mg
        self._orig_store = mg.STORE_FILE
        self._orig_log = mg.LOG_FILE
        self._orig_decay = mg.DECAY_LOG_FILE
        mg.STORE_FILE = os.path.join(self._tmpdir, "store.jsonl")
        mg.LOG_FILE = os.path.join(self._tmpdir, "log.jsonl")
        mg.DECAY_LOG_FILE = os.path.join(self._tmpdir, "decay.jsonl")

    def tearDown(self):
        import core.memory_governance as mg
        mg.STORE_FILE = self._orig_store
        mg.LOG_FILE = self._orig_log
        mg.DECAY_LOG_FILE = self._orig_decay
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_memory_add(self):
        r = self.client.post("/api/v1/memory", json={
            "content": "DOF governance compliance is high",
            "category": "knowledge",
        })
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("memory_id", data)
        self.assertIn("category", data)

    def test_memory_query(self):
        self.client.post("/api/v1/memory", json={
            "content": "Test entry for API query",
            "category": "context",
        })
        r = self.client.get("/api/v1/memory?query=test&category=context")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("results", data)
        self.assertIn("count", data)

    def test_memory_snapshot(self):
        r = self.client.get("/api/v1/memory/snapshot")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("memories", data)
        self.assertIn("as_of", data)

    def test_memory_stats(self):
        r = self.client.get("/api/v1/memory/stats")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("total_memories", data)


@unittest.skipUnless(HAS_FASTAPI, "fastapi not installed")
class TestMetricsEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_metrics(self):
        r = self.client.get("/api/v1/metrics")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        for key in ("SS", "GCR", "PFI", "RP", "SSR"):
            self.assertIn(key, data)


@unittest.skipUnless(HAS_FASTAPI, "fastapi not installed")
class TestAttestationEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_attestation_create(self):
        r = self.client.post("/api/v1/attestation", json={
            "task_id": "api-test-001",
            "metrics": {"SS": 0.95, "GCR": 1.0, "PFI": 0.02, "RP": 0.85, "SSR": 0.92},
        })
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("certificate_hash", data)
        self.assertIn("governance_status", data)

    def test_attestation_history(self):
        r = self.client.get("/api/v1/attestation/history")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("attestations", data)
        self.assertIn("compliance_rate", data)


@unittest.skipUnless(HAS_FASTAPI, "fastapi not installed")
class TestOAGSEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_oags_identity(self):
        r = self.client.get("/api/v1/oags/identity?model=test-model&tools=tool1,tool2")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("identity_hash", data)
        self.assertIn("agent_card", data)

    def test_oags_conformance(self):
        r = self.client.get("/api/v1/oags/conformance")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("level_1", data)
        self.assertIn("max_level", data)
        self.assertGreaterEqual(data["max_level"], 3)


@unittest.skipUnless(HAS_FASTAPI, "fastapi not installed")
class TestConstitutionEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_constitution(self):
        r = self.client.get("/api/v1/constitution")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        # Should have rules or some constitution structure
        self.assertIsInstance(data, dict)


if __name__ == "__main__":
    unittest.main()
