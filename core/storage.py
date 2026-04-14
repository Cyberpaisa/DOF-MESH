from __future__ import annotations
"""
Storage Backend — Dual JSONL / PostgreSQL persistence layer.

StorageBackend: abstract interface for all persistence operations.
JSONLBackend: default backend using append-only JSONL files (zero deps).
PostgreSQLBackend: production backend using SQLAlchemy ORM + Supabase.
StorageFactory: auto-selects backend from DOF_DATABASE_URL env var.

JSONL is the default — PostgreSQL is OPTIONAL and requires:
  pip install sqlalchemy psycopg2-binary

Usage:
    from core.storage import StorageFactory
    backend = StorageFactory.get_backend()
    backend.save_memory({"id": "...", "content": "...", ...})
    memories = backend.load_memories()
"""

import os
import json
import uuid
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone

logger = logging.getLogger("core.storage")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMORY_DIR = os.path.join(BASE_DIR, "memory")
LOGS_DIR = os.path.join(BASE_DIR, "logs")


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat()


# ─────────────────────────────────────────────────────────────────────
# Abstract Backend
# ─────────────────────────────────────────────────────────────────────

class StorageBackend(ABC):
    """Abstract storage interface for DOF persistence."""

    @abstractmethod
    def initialize(self) -> None:
        """Create tables / directories if they don't exist."""

    @abstractmethod
    def save_memory(self, entry: dict) -> bool:
        """Persist a memory entry. Returns True on success."""

    @abstractmethod
    def load_memories(self) -> list[dict]:
        """Load all memory entries."""

    @abstractmethod
    def save_attestation(self, cert: dict) -> bool:
        """Persist an attestation certificate. Returns True on success."""

    @abstractmethod
    def load_attestations(self) -> list[dict]:
        """Load all attestation certificates."""

    @abstractmethod
    def save_audit_event(self, event: dict) -> bool:
        """Persist an audit event. Returns True on success."""

    @abstractmethod
    def query_memories(self, query: str = "", category: str = None,
                       as_of: str = None) -> list[dict]:
        """Query memories with optional filters."""

    @abstractmethod
    def get_stats(self) -> dict:
        """Return storage statistics."""


# ─────────────────────────────────────────────────────────────────────
# JSONL Backend (default)
# ─────────────────────────────────────────────────────────────────────

class JSONLBackend(StorageBackend):
    """Append-only JSONL file backend — zero external dependencies.

    This wraps the existing JSONL persistence pattern used by
    GovernedMemoryStore and AttestationRegistry.
    """

    def __init__(self, memory_file: str = None, attestation_file: str = None,
                 audit_file: str = None):
        self._memory_file = memory_file or os.path.join(MEMORY_DIR, "governed_store.jsonl")
        self._attestation_file = attestation_file or os.path.join(LOGS_DIR, "attestations.jsonl")
        self._audit_file = audit_file or os.path.join(LOGS_DIR, "storage_audit.jsonl")

    def initialize(self) -> None:
        """Ensure directories exist. JSONL files are created on first write."""
        os.makedirs(os.path.dirname(self._memory_file), exist_ok=True)
        os.makedirs(os.path.dirname(self._attestation_file), exist_ok=True)
        os.makedirs(os.path.dirname(self._audit_file), exist_ok=True)

    def save_memory(self, entry: dict) -> bool:
        if not isinstance(entry, dict):
            logger.warning(f"save_memory: entry must be a dict, got {type(entry).__name__}")
            return False
        try:
            os.makedirs(os.path.dirname(self._memory_file), exist_ok=True)
            with open(self._memory_file, "a") as f:
                f.write(json.dumps(entry, default=str) + "\n")
            return True
        except Exception as exc:
            logger.error(f"JSONL save_memory failed: {exc}")
            return False

    def load_memories(self) -> list[dict]:
        return self._load_jsonl(self._memory_file)

    def save_attestation(self, cert: dict) -> bool:
        if not isinstance(cert, dict):
            logger.warning(f"save_attestation: cert must be a dict, got {type(cert).__name__}")
            return False
        try:
            os.makedirs(os.path.dirname(self._attestation_file), exist_ok=True)
            with open(self._attestation_file, "a") as f:
                f.write(json.dumps(cert, default=str) + "\n")
            return True
        except Exception as exc:
            logger.error(f"JSONL save_attestation failed: {exc}")
            return False

    def load_attestations(self) -> list[dict]:
        return self._load_jsonl(self._attestation_file)

    def save_audit_event(self, event: dict) -> bool:
        if not isinstance(event, dict):
            logger.warning(f"save_audit_event: event must be a dict, got {type(event).__name__}")
            return False
        try:
            os.makedirs(os.path.dirname(self._audit_file), exist_ok=True)
            with open(self._audit_file, "a") as f:
                f.write(json.dumps(event, default=str) + "\n")
            return True
        except Exception as exc:
            logger.error(f"JSONL save_audit_event failed: {exc}")
            return False

    def query_memories(self, query: str = "", category: str = None,
                       as_of: str = None) -> list[dict]:
        entries = self.load_memories()
        # Deduplicate by id (last write wins)
        by_id = {}
        for e in entries:
            by_id[e["id"]] = e
        results = []
        for e in by_id.values():
            # Skip rejected
            if e.get("governance_status") == "rejected":
                continue
            # Skip expired (unless as_of query)
            if as_of:
                vf = e.get("valid_from", "")
                vt = e.get("valid_to")
                if vf > as_of:
                    continue
                if vt is not None and vt <= as_of:
                    continue
            else:
                if e.get("valid_to") is not None:
                    continue
            # Category filter
            if category and e.get("category") != category:
                continue
            # Keyword filter
            if query:
                content = e.get("content", "").lower()
                if not any(w in content for w in query.lower().split()):
                    continue
            results.append(e)
        results.sort(key=lambda e: e.get("relevance_score", 0), reverse=True)
        return results

    def get_stats(self) -> dict:
        entries = self.load_memories()
        by_id = {}
        for e in entries:
            by_id[e["id"]] = e
        all_entries = list(by_id.values())
        active = [e for e in all_entries
                  if e.get("valid_to") is None and e.get("governance_status") != "rejected"]
        by_category = {}
        for e in active:
            cat = e.get("category", "unknown")
            by_category[cat] = by_category.get(cat, 0) + 1
        by_status = {}
        for e in all_entries:
            st = e.get("governance_status", "unknown")
            by_status[st] = by_status.get(st, 0) + 1
        avg_rel = (sum(e.get("relevance_score", 0) for e in active) / len(active)
                   if active else 0.0)
        attestations = self.load_attestations()
        return {
            "backend": "jsonl",
            "total_memories": len(all_entries),
            "active_memories": len(active),
            "by_category": by_category,
            "by_status": by_status,
            "avg_relevance": round(avg_rel, 3),
            "total_attestations": len(attestations),
        }

    @staticmethod
    def _load_jsonl(path: str) -> list[dict]:
        if not os.path.exists(path):
            return []
        results = []
        try:
            with open(path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        results.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except Exception as exc:
            logger.error(f"Failed to load JSONL {path}: {exc}")
        return results


# ─────────────────────────────────────────────────────────────────────
# PostgreSQL Backend (optional)
# ─────────────────────────────────────────────────────────────────────

try:
    from sqlalchemy import (
        create_engine, Column, String, Text, Float, Integer, Boolean,
        DateTime, JSON, MetaData, Table, inspect,
    )
    from sqlalchemy.orm import DeclarativeBase, Session
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False


if HAS_SQLALCHEMY:
    class _Base(DeclarativeBase):
        pass

    class _MemoryRow(_Base):
        __tablename__ = "dof_memories"
        id = Column(String, primary_key=True)
        content = Column(Text, nullable=False)
        category = Column(String(50), nullable=False)
        metadata_ = Column("metadata", JSON, default=dict)
        valid_from = Column(String, nullable=False)
        valid_to = Column(String, nullable=True)
        recorded_at = Column(String, nullable=False)
        relevance_score = Column(Float, default=1.0)
        governance_status = Column(String(20), default="approved")
        version = Column(Integer, default=1)
        parent_id = Column(String, nullable=True)
        root_id = Column(String, nullable=True)

    class _AttestationRow(_Base):
        __tablename__ = "dof_attestations"
        id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
        agent_identity = Column(String, nullable=False)
        task_id = Column(String, nullable=False)
        timestamp = Column(String, nullable=False)
        metrics = Column(JSON, default=dict)
        governance_status = Column(String(20), nullable=False)
        z3_verified = Column(Boolean, default=False)
        signature = Column(String, nullable=False)
        certificate_hash = Column(String, nullable=False, unique=True)
        published = Column(Boolean, default=False)

    class _AuditEventRow(_Base):
        __tablename__ = "dof_audit_events"
        id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
        timestamp = Column(String, nullable=False)
        event_type = Column(String(50), nullable=False)
        module = Column(String(100), nullable=True)
        payload = Column(JSON, default=dict)


class PostgreSQLBackend(StorageBackend):
    """PostgreSQL backend using SQLAlchemy ORM.

    Requires: pip install sqlalchemy psycopg2-binary
    Connection string from DOF_DATABASE_URL environment variable.
    """

    def __init__(self, connection_url: str = None):
        if not HAS_SQLALCHEMY:
            raise ImportError("sqlalchemy is required for PostgreSQLBackend")
        self._url = connection_url or os.environ.get("DOF_DATABASE_URL", "")
        if not self._url:
            raise ValueError("No database URL provided")
        self._engine = create_engine(self._url, echo=False)
        self._initialized = False

    def initialize(self) -> None:
        """Create tables if they don't exist."""
        if self._initialized:
            return
        try:
            _Base.metadata.create_all(self._engine)
            self._initialized = True
            logger.info("PostgreSQL tables initialized")
        except Exception as exc:
            logger.error(f"Failed to initialize PostgreSQL tables: {exc}")
            raise

    def _ensure_init(self):
        if not self._initialized:
            self.initialize()

    def save_memory(self, entry: dict) -> bool:
        self._ensure_init()
        try:
            with Session(self._engine) as session:
                # Handle metadata key mapping
                row_data = dict(entry)
                if "metadata" in row_data:
                    row_data["metadata_"] = row_data.pop("metadata")
                row = _MemoryRow(**row_data)
                session.merge(row)
                session.commit()
            return True
        except Exception as exc:
            logger.error(f"PostgreSQL save_memory failed: {exc}")
            return False

    def load_memories(self) -> list[dict]:
        self._ensure_init()
        try:
            with Session(self._engine) as session:
                rows = session.query(_MemoryRow).all()
                return [self._memory_to_dict(r) for r in rows]
        except Exception as exc:
            logger.error(f"PostgreSQL load_memories failed: {exc}")
            return []

    def save_attestation(self, cert: dict) -> bool:
        self._ensure_init()
        try:
            with Session(self._engine) as session:
                row_data = dict(cert)
                if "id" not in row_data:
                    row_data["id"] = str(uuid.uuid4())
                row = _AttestationRow(**row_data)
                session.merge(row)
                session.commit()
            return True
        except Exception as exc:
            logger.error(f"PostgreSQL save_attestation failed: {exc}")
            return False

    def load_attestations(self) -> list[dict]:
        self._ensure_init()
        try:
            with Session(self._engine) as session:
                rows = session.query(_AttestationRow).all()
                return [self._attestation_to_dict(r) for r in rows]
        except Exception as exc:
            logger.error(f"PostgreSQL load_attestations failed: {exc}")
            return []

    def save_audit_event(self, event: dict) -> bool:
        self._ensure_init()
        try:
            with Session(self._engine) as session:
                row_data = dict(event)
                if "id" not in row_data:
                    row_data["id"] = str(uuid.uuid4())
                row = _AuditEventRow(**row_data)
                session.add(row)
                session.commit()
            return True
        except Exception as exc:
            logger.error(f"PostgreSQL save_audit_event failed: {exc}")
            return False

    def query_memories(self, query: str = "", category: str = None,
                       as_of: str = None) -> list[dict]:
        self._ensure_init()
        try:
            with Session(self._engine) as session:
                q = session.query(_MemoryRow).filter(
                    _MemoryRow.governance_status != "rejected"
                )
                if category:
                    q = q.filter(_MemoryRow.category == category)
                if as_of:
                    q = q.filter(_MemoryRow.valid_from <= as_of)
                    q = q.filter(
                        (_MemoryRow.valid_to == None) | (_MemoryRow.valid_to > as_of)
                    )
                else:
                    q = q.filter(_MemoryRow.valid_to == None)
                rows = q.order_by(_MemoryRow.relevance_score.desc()).all()
                results = [self._memory_to_dict(r) for r in rows]
                if query:
                    query_lower = query.lower()
                    results = [
                        r for r in results
                        if any(w in r.get("content", "").lower()
                               for w in query_lower.split())
                    ]
                return results
        except Exception as exc:
            logger.error(f"PostgreSQL query_memories failed: {exc}")
            return []

    def get_stats(self) -> dict:
        self._ensure_init()
        try:
            with Session(self._engine) as session:
                total = session.query(_MemoryRow).count()
                active = session.query(_MemoryRow).filter(
                    _MemoryRow.valid_to == None,
                    _MemoryRow.governance_status != "rejected"
                ).count()
                attestations = session.query(_AttestationRow).count()
                audit_events = session.query(_AuditEventRow).count()
                return {
                    "backend": "postgresql",
                    "total_memories": total,
                    "active_memories": active,
                    "total_attestations": attestations,
                    "total_audit_events": audit_events,
                }
        except Exception as exc:
            logger.error(f"PostgreSQL get_stats failed: {exc}")
            return {"backend": "postgresql", "error": str(exc)}

    @staticmethod
    def _memory_to_dict(row) -> dict:
        return {
            "id": row.id,
            "content": row.content,
            "category": row.category,
            "metadata": row.metadata_ or {},
            "valid_from": row.valid_from,
            "valid_to": row.valid_to,
            "recorded_at": row.recorded_at,
            "relevance_score": row.relevance_score,
            "governance_status": row.governance_status,
            "version": row.version,
            "parent_id": row.parent_id,
            "root_id": row.root_id,
        }

    @staticmethod
    def _attestation_to_dict(row) -> dict:
        return {
            "agent_identity": row.agent_identity,
            "task_id": row.task_id,
            "timestamp": row.timestamp,
            "metrics": row.metrics or {},
            "governance_status": row.governance_status,
            "z3_verified": row.z3_verified,
            "signature": row.signature,
            "certificate_hash": row.certificate_hash,
            "published": row.published,
        }


# ─────────────────────────────────────────────────────────────────────
# Storage Factory (Singleton)
# ─────────────────────────────────────────────────────────────────────

class StorageFactory:
    """Auto-select storage backend based on environment.

    If DOF_DATABASE_URL is set and SQLAlchemy is available → PostgreSQLBackend.
    Otherwise → JSONLBackend.

    Singleton: always returns the same backend instance.
    """

    _instance: StorageBackend | None = None
    _backend_name: str = ""

    @classmethod
    def get_backend(cls) -> StorageBackend:
        """Return the active storage backend (singleton)."""
        if cls._instance is not None:
            return cls._instance

        db_url = os.environ.get("DOF_DATABASE_URL", "")

        if db_url and HAS_SQLALCHEMY:
            try:
                backend = PostgreSQLBackend(db_url)
                backend.initialize()
                cls._instance = backend
                cls._backend_name = "postgresql"
                logger.info(f"Storage backend: PostgreSQL ({db_url[:30]}...)")
                return backend
            except Exception as exc:
                logger.warning(
                    f"PostgreSQL backend failed ({exc}) — falling back to JSONL"
                )

        backend = JSONLBackend()
        backend.initialize()
        cls._instance = backend
        cls._backend_name = "jsonl"
        logger.info("Storage backend: JSONL (default)")
        return backend

    @classmethod
    def get_backend_name(cls) -> str:
        """Return the name of the active backend."""
        if cls._instance is None:
            cls.get_backend()
        return cls._backend_name

    @classmethod
    def reset(cls) -> None:
        """Reset singleton (for testing)."""
        cls._instance = None
        cls._backend_name = ""


# ─────────────────────────────────────────────────────────────────────
# Migration Utility
# ─────────────────────────────────────────────────────────────────────

def migrate_jsonl_to_postgres(jsonl_dir: str = None, logs_dir: str = None) -> dict:
    """Migrate existing JSONL data to PostgreSQL.

    Reads from JSONL files and inserts into PostgreSQL backend.
    Returns counts of migrated records.
    """
    jsonl_dir = jsonl_dir or MEMORY_DIR
    logs_dir = logs_dir or LOGS_DIR

    if not HAS_SQLALCHEMY:
        return {"error": "sqlalchemy not installed"}

    db_url = os.environ.get("DOF_DATABASE_URL", "")
    if not db_url:
        return {"error": "DOF_DATABASE_URL not set"}

    # Source: JSONL
    source = JSONLBackend(
        memory_file=os.path.join(jsonl_dir, "governed_store.jsonl"),
        attestation_file=os.path.join(logs_dir, "attestations.jsonl"),
    )

    # Target: PostgreSQL
    target = PostgreSQLBackend(db_url)
    target.initialize()

    # Migrate memories
    memories = source.load_memories()
    migrated_memories = 0
    for m in memories:
        if target.save_memory(m):
            migrated_memories += 1

    # Migrate attestations
    attestations = source.load_attestations()
    migrated_attestations = 0
    for a in attestations:
        if target.save_attestation(a):
            migrated_attestations += 1

    # Migrate audit events from memory_governance.jsonl
    audit_file = os.path.join(logs_dir, "memory_governance.jsonl")
    audit_events = JSONLBackend._load_jsonl(audit_file)
    migrated_events = 0
    for event in audit_events:
        evt = {
            "id": str(uuid.uuid4()),
            "timestamp": event.get("timestamp", _now_iso()),
            "event_type": event.get("operation", "unknown"),
            "module": "memory_governance",
            "payload": event,
        }
        if target.save_audit_event(evt):
            migrated_events += 1

    result = {
        "migrated_memories": migrated_memories,
        "migrated_attestations": migrated_attestations,
        "migrated_events": migrated_events,
    }
    logger.info(f"Migration complete: {result}")
    return result
