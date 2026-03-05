"""Tests for DOF Storage Backend — JSONL and PostgreSQL (via SQLite)."""

import json
import os
import shutil
import sys
import tempfile
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core.storage import (
    JSONLBackend,
    PostgreSQLBackend,
    StorageFactory,
    HAS_SQLALCHEMY,
    migrate_jsonl_to_postgres,
)


# ─────────────────────────────────────────────────────────────────────
# JSONL Backend Tests
# ─────────────────────────────────────────────────────────────────────

class TestJSONLBackendMemories(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.backend = JSONLBackend(
            memory_file=os.path.join(self._tmpdir, "store.jsonl"),
            attestation_file=os.path.join(self._tmpdir, "attestations.jsonl"),
            audit_file=os.path.join(self._tmpdir, "audit.jsonl"),
        )
        self.backend.initialize()

    def tearDown(self):
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_save_and_load_memories(self):
        entry = {
            "id": "mem-001",
            "content": "DOF governance ensures compliance",
            "category": "knowledge",
            "metadata": {},
            "valid_from": "2026-03-01T00:00:00",
            "valid_to": None,
            "recorded_at": "2026-03-01T00:00:00",
            "relevance_score": 1.0,
            "governance_status": "approved",
            "version": 1,
            "parent_id": None,
            "root_id": None,
        }
        self.assertTrue(self.backend.save_memory(entry))
        memories = self.backend.load_memories()
        self.assertEqual(len(memories), 1)
        self.assertEqual(memories[0]["id"], "mem-001")
        self.assertEqual(memories[0]["content"], "DOF governance ensures compliance")

    def test_save_multiple_memories(self):
        for i in range(5):
            self.backend.save_memory({
                "id": f"mem-{i:03d}",
                "content": f"Memory entry {i}",
                "category": "knowledge",
                "metadata": {},
                "valid_from": "2026-03-01T00:00:00",
                "valid_to": None,
                "recorded_at": "2026-03-01T00:00:00",
                "relevance_score": 1.0 - i * 0.1,
                "governance_status": "approved",
                "version": 1,
                "parent_id": None,
                "root_id": None,
            })
        memories = self.backend.load_memories()
        self.assertEqual(len(memories), 5)

    def test_query_by_category(self):
        self.backend.save_memory({
            "id": "m1", "content": "error log", "category": "errors",
            "metadata": {}, "valid_from": "2026-01-01", "valid_to": None,
            "recorded_at": "2026-01-01", "relevance_score": 1.0,
            "governance_status": "approved", "version": 1,
            "parent_id": None, "root_id": None,
        })
        self.backend.save_memory({
            "id": "m2", "content": "preference setting", "category": "preferences",
            "metadata": {}, "valid_from": "2026-01-01", "valid_to": None,
            "recorded_at": "2026-01-01", "relevance_score": 1.0,
            "governance_status": "approved", "version": 1,
            "parent_id": None, "root_id": None,
        })
        results = self.backend.query_memories(category="errors")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["category"], "errors")

    def test_query_by_keyword(self):
        self.backend.save_memory({
            "id": "m1", "content": "The Z3 verifier proved invariants",
            "category": "knowledge", "metadata": {},
            "valid_from": "2026-01-01", "valid_to": None,
            "recorded_at": "2026-01-01", "relevance_score": 1.0,
            "governance_status": "approved", "version": 1,
            "parent_id": None, "root_id": None,
        })
        results = self.backend.query_memories(query="Z3")
        self.assertEqual(len(results), 1)
        results_none = self.backend.query_memories(query="nonexistent")
        self.assertEqual(len(results_none), 0)

    def test_query_skips_rejected(self):
        self.backend.save_memory({
            "id": "m1", "content": "rejected entry",
            "category": "knowledge", "metadata": {},
            "valid_from": "2026-01-01", "valid_to": None,
            "recorded_at": "2026-01-01", "relevance_score": 1.0,
            "governance_status": "rejected", "version": 1,
            "parent_id": None, "root_id": None,
        })
        results = self.backend.query_memories()
        self.assertEqual(len(results), 0)


class TestJSONLBackendAttestations(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.backend = JSONLBackend(
            memory_file=os.path.join(self._tmpdir, "store.jsonl"),
            attestation_file=os.path.join(self._tmpdir, "attestations.jsonl"),
            audit_file=os.path.join(self._tmpdir, "audit.jsonl"),
        )
        self.backend.initialize()

    def tearDown(self):
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_save_and_load_attestations(self):
        cert = {
            "agent_identity": "agent-001",
            "task_id": "task-001",
            "timestamp": "2026-03-01T00:00:00",
            "metrics": {"SS": 0.95, "GCR": 1.0},
            "governance_status": "COMPLIANT",
            "z3_verified": True,
            "signature": "sig123",
            "certificate_hash": "hash123",
            "published": False,
        }
        self.assertTrue(self.backend.save_attestation(cert))
        attestations = self.backend.load_attestations()
        self.assertEqual(len(attestations), 1)
        self.assertEqual(attestations[0]["task_id"], "task-001")

    def test_save_audit_event(self):
        event = {
            "id": "evt-001",
            "timestamp": "2026-03-01T00:00:00",
            "event_type": "memory_add",
            "module": "memory_governance",
            "payload": {"memory_id": "m1"},
        }
        self.assertTrue(self.backend.save_audit_event(event))

    def test_get_stats(self):
        self.backend.save_memory({
            "id": "m1", "content": "test", "category": "knowledge",
            "metadata": {}, "valid_from": "2026-01-01", "valid_to": None,
            "recorded_at": "2026-01-01", "relevance_score": 0.9,
            "governance_status": "approved", "version": 1,
            "parent_id": None, "root_id": None,
        })
        stats = self.backend.get_stats()
        self.assertEqual(stats["backend"], "jsonl")
        self.assertEqual(stats["total_memories"], 1)
        self.assertEqual(stats["active_memories"], 1)


# ─────────────────────────────────────────────────────────────────────
# PostgreSQL Backend Tests (via SQLite in-memory)
# ─────────────────────────────────────────────────────────────────────

@unittest.skipUnless(HAS_SQLALCHEMY, "sqlalchemy not installed")
class TestPostgreSQLBackendMemories(unittest.TestCase):
    def setUp(self):
        self.backend = PostgreSQLBackend("sqlite:///:memory:")
        self.backend.initialize()

    def test_save_and_load_memories(self):
        entry = {
            "id": "pg-mem-001",
            "content": "PostgreSQL stored memory",
            "category": "knowledge",
            "metadata": {"source": "test"},
            "valid_from": "2026-03-01T00:00:00",
            "valid_to": None,
            "recorded_at": "2026-03-01T00:00:00",
            "relevance_score": 0.95,
            "governance_status": "approved",
            "version": 1,
            "parent_id": None,
            "root_id": None,
        }
        self.assertTrue(self.backend.save_memory(entry))
        memories = self.backend.load_memories()
        self.assertEqual(len(memories), 1)
        self.assertEqual(memories[0]["id"], "pg-mem-001")
        self.assertEqual(memories[0]["metadata"], {"source": "test"})

    def test_save_multiple_and_query(self):
        for i in range(3):
            self.backend.save_memory({
                "id": f"pg-{i}", "content": f"Entry {i}",
                "category": "errors" if i == 0 else "knowledge",
                "metadata": {}, "valid_from": "2026-01-01",
                "valid_to": None, "recorded_at": "2026-01-01",
                "relevance_score": 1.0, "governance_status": "approved",
                "version": 1, "parent_id": None, "root_id": None,
            })
        results = self.backend.query_memories(category="errors")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["category"], "errors")

    def test_query_skips_rejected(self):
        self.backend.save_memory({
            "id": "rej-1", "content": "rejected",
            "category": "knowledge", "metadata": {},
            "valid_from": "2026-01-01", "valid_to": None,
            "recorded_at": "2026-01-01", "relevance_score": 1.0,
            "governance_status": "rejected", "version": 1,
            "parent_id": None, "root_id": None,
        })
        results = self.backend.query_memories()
        self.assertEqual(len(results), 0)

    def test_query_skips_expired(self):
        self.backend.save_memory({
            "id": "exp-1", "content": "expired entry",
            "category": "knowledge", "metadata": {},
            "valid_from": "2026-01-01", "valid_to": "2026-02-01",
            "recorded_at": "2026-01-01", "relevance_score": 1.0,
            "governance_status": "approved", "version": 1,
            "parent_id": None, "root_id": None,
        })
        results = self.backend.query_memories()
        self.assertEqual(len(results), 0)


@unittest.skipUnless(HAS_SQLALCHEMY, "sqlalchemy not installed")
class TestPostgreSQLBackendAttestations(unittest.TestCase):
    def setUp(self):
        self.backend = PostgreSQLBackend("sqlite:///:memory:")
        self.backend.initialize()

    def test_save_and_load_attestations(self):
        cert = {
            "agent_identity": "agent-001",
            "task_id": "task-001",
            "timestamp": "2026-03-01T00:00:00",
            "metrics": {"SS": 0.95, "GCR": 1.0},
            "governance_status": "COMPLIANT",
            "z3_verified": True,
            "signature": "sig456",
            "certificate_hash": "hash456",
            "published": False,
        }
        self.assertTrue(self.backend.save_attestation(cert))
        attestations = self.backend.load_attestations()
        self.assertEqual(len(attestations), 1)
        self.assertEqual(attestations[0]["certificate_hash"], "hash456")

    def test_save_audit_event(self):
        event = {
            "id": "evt-pg-001",
            "timestamp": "2026-03-01T00:00:00",
            "event_type": "memory_add",
            "module": "memory_governance",
            "payload": {"memory_id": "m1"},
        }
        self.assertTrue(self.backend.save_audit_event(event))


@unittest.skipUnless(HAS_SQLALCHEMY, "sqlalchemy not installed")
class TestPostgreSQLBackendStats(unittest.TestCase):
    def setUp(self):
        self.backend = PostgreSQLBackend("sqlite:///:memory:")
        self.backend.initialize()

    def test_get_stats(self):
        self.backend.save_memory({
            "id": "s1", "content": "test", "category": "knowledge",
            "metadata": {}, "valid_from": "2026-01-01", "valid_to": None,
            "recorded_at": "2026-01-01", "relevance_score": 1.0,
            "governance_status": "approved", "version": 1,
            "parent_id": None, "root_id": None,
        })
        self.backend.save_attestation({
            "agent_identity": "a", "task_id": "t", "timestamp": "2026-01-01",
            "metrics": {}, "governance_status": "COMPLIANT", "z3_verified": True,
            "signature": "s", "certificate_hash": "h1", "published": False,
        })
        stats = self.backend.get_stats()
        self.assertEqual(stats["backend"], "postgresql")
        self.assertEqual(stats["total_memories"], 1)
        self.assertEqual(stats["active_memories"], 1)
        self.assertEqual(stats["total_attestations"], 1)


# ─────────────────────────────────────────────────────────────────────
# StorageFactory Tests
# ─────────────────────────────────────────────────────────────────────

class TestStorageFactory(unittest.TestCase):
    def setUp(self):
        StorageFactory.reset()
        self._orig_url = os.environ.get("DOF_DATABASE_URL")
        os.environ.pop("DOF_DATABASE_URL", None)

    def tearDown(self):
        StorageFactory.reset()
        if self._orig_url is not None:
            os.environ["DOF_DATABASE_URL"] = self._orig_url
        else:
            os.environ.pop("DOF_DATABASE_URL", None)

    def test_returns_jsonl_when_no_url(self):
        backend = StorageFactory.get_backend()
        self.assertIsInstance(backend, JSONLBackend)
        self.assertEqual(StorageFactory.get_backend_name(), "jsonl")

    def test_singleton(self):
        b1 = StorageFactory.get_backend()
        b2 = StorageFactory.get_backend()
        self.assertIs(b1, b2)

    def test_reset(self):
        StorageFactory.get_backend()
        StorageFactory.reset()
        self.assertIsNone(StorageFactory._instance)


# ─────────────────────────────────────────────────────────────────────
# GovernedMemoryStore + Backend Integration
# ─────────────────────────────────────────────────────────────────────

@unittest.skipUnless(HAS_SQLALCHEMY, "sqlalchemy not installed")
class TestGovernedMemoryStoreWithBackend(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.backend = PostgreSQLBackend("sqlite:///:memory:")
        self.backend.initialize()

        import core.memory_governance as mg
        self._orig_store = mg.STORE_FILE
        self._orig_log = mg.LOG_FILE
        self._orig_decay = mg.DECAY_LOG_FILE
        mg.STORE_FILE = os.path.join(self._tmpdir, "store.jsonl")
        mg.LOG_FILE = os.path.join(self._tmpdir, "log.jsonl")
        mg.DECAY_LOG_FILE = os.path.join(self._tmpdir, "decay.jsonl")

        from core.memory_governance import GovernedMemoryStore
        self.store = GovernedMemoryStore(_storage_backend=self.backend)

    def tearDown(self):
        import core.memory_governance as mg
        mg.STORE_FILE = self._orig_store
        mg.LOG_FILE = self._orig_log
        mg.DECAY_LOG_FILE = self._orig_decay
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_add_writes_to_backend(self):
        entry = self.store.add("Z3 verified all invariants", category="knowledge")
        self.assertIsNotNone(entry)
        # Verify it was written to PostgreSQL (SQLite) backend
        memories = self.backend.load_memories()
        self.assertGreaterEqual(len(memories), 1)
        found = any(m["content"] == "Z3 verified all invariants" for m in memories)
        self.assertTrue(found)

    def test_update_writes_to_backend(self):
        entry = self.store.add("Original content for backend test", category="knowledge")
        updated = self.store.update(entry.id, "Updated content for backend test")
        memories = self.backend.load_memories()
        contents = [m["content"] for m in memories]
        self.assertIn("Updated content for backend test", contents)


# ─────────────────────────────────────────────────────────────────────
# Migration Tests
# ─────────────────────────────────────────────────────────────────────

@unittest.skipUnless(HAS_SQLALCHEMY, "sqlalchemy not installed")
class TestMigration(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._mem_dir = os.path.join(self._tmpdir, "memory")
        self._log_dir = os.path.join(self._tmpdir, "logs")
        os.makedirs(self._mem_dir)
        os.makedirs(self._log_dir)

        # Write test JSONL data
        with open(os.path.join(self._mem_dir, "governed_store.jsonl"), "w") as f:
            f.write(json.dumps({
                "id": "mig-001", "content": "Migrated memory",
                "category": "knowledge", "metadata": {},
                "valid_from": "2026-01-01", "valid_to": None,
                "recorded_at": "2026-01-01", "relevance_score": 1.0,
                "governance_status": "approved", "version": 1,
                "parent_id": None, "root_id": None,
            }) + "\n")

        with open(os.path.join(self._log_dir, "attestations.jsonl"), "w") as f:
            f.write(json.dumps({
                "agent_identity": "a", "task_id": "t", "timestamp": "2026-01-01",
                "metrics": {}, "governance_status": "COMPLIANT", "z3_verified": True,
                "signature": "s", "certificate_hash": "hmig", "published": False,
            }) + "\n")

        self._orig_url = os.environ.get("DOF_DATABASE_URL")
        os.environ["DOF_DATABASE_URL"] = "sqlite:///:memory:"

    def tearDown(self):
        shutil.rmtree(self._tmpdir, ignore_errors=True)
        if self._orig_url is not None:
            os.environ["DOF_DATABASE_URL"] = self._orig_url
        else:
            os.environ.pop("DOF_DATABASE_URL", None)

    def test_migrate_jsonl_to_postgres(self):
        result = migrate_jsonl_to_postgres(
            jsonl_dir=self._mem_dir,
            logs_dir=self._log_dir,
        )
        self.assertEqual(result["migrated_memories"], 1)
        self.assertEqual(result["migrated_attestations"], 1)
        self.assertIn("migrated_events", result)


# ─────────────────────────────────────────────────────────────────────
# Import Tests
# ─────────────────────────────────────────────────────────────────────

class TestStorageImports(unittest.TestCase):
    def test_dof_exports_storage(self):
        import dof
        self.assertTrue(hasattr(dof, "StorageFactory"))
        self.assertTrue(hasattr(dof, "JSONLBackend"))
        self.assertTrue(hasattr(dof, "PostgreSQLBackend"))

    def test_storage_factory_in_all(self):
        import dof
        self.assertIn("StorageFactory", dof.__all__)
        self.assertIn("JSONLBackend", dof.__all__)
        self.assertIn("PostgreSQLBackend", dof.__all__)


if __name__ == "__main__":
    unittest.main()
