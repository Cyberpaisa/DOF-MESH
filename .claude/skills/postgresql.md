---
name: postgresql-table-design
description: PostgreSQL schema design for DOF SDK storage backend. Covers DOF-specific table design, indexing, JSONB patterns, and the dual JSONL/PostgreSQL architecture. Use when designing database tables, optimizing queries, or extending core/storage.py.
---

# PostgreSQL Table Design — DOF Adapted

PostgreSQL schema design for the DOF SDK dual storage backend (`core/storage.py`).

## DOF Storage Architecture

DOF uses a dual-write pattern:
1. **JSONL** (default): zero dependencies, append-only, always available
2. **PostgreSQL** (optional): via `DOF_DATABASE_URL` env var, SQLAlchemy ORM

`StorageFactory` auto-detects: if `DOF_DATABASE_URL` is set → PostgreSQL, else → JSONL.

## Current DOF Tables

### dof_memories

```sql
CREATE TABLE dof_memories (
    id TEXT PRIMARY KEY,               -- UUID string from MemoryEntry
    content TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT '',
    governance_status TEXT NOT NULL DEFAULT 'pending',
    timestamp_ TIMESTAMPTZ NOT NULL DEFAULT now(),
    relevance DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    access_count INTEGER NOT NULL DEFAULT 0,
    metadata_ JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ON dof_memories (category);
CREATE INDEX ON dof_memories (governance_status);
CREATE INDEX ON dof_memories (created_at);
CREATE INDEX ON dof_memories USING GIN (metadata_);
```

### dof_attestations

```sql
CREATE TABLE dof_attestations (
    certificate_id TEXT PRIMARY KEY,   -- UUID from AttestationCertificate
    run_id TEXT NOT NULL,
    agent TEXT NOT NULL DEFAULT '',
    claim_hash TEXT NOT NULL,
    governance_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    z3_verified BOOLEAN NOT NULL DEFAULT false,
    timestamp_ TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata_ JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ON dof_attestations (run_id);
CREATE INDEX ON dof_attestations (agent);
CREATE INDEX ON dof_attestations (created_at);
```

### dof_audit_events

```sql
CREATE TABLE dof_audit_events (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_type TEXT NOT NULL,
    entity_id TEXT NOT NULL DEFAULT '',
    details JSONB NOT NULL DEFAULT '{}',
    timestamp_ TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ON dof_audit_events (event_type);
CREATE INDEX ON dof_audit_events (entity_id);
CREATE INDEX ON dof_audit_events (timestamp_);
```

## Core PostgreSQL Rules for DOF

### Data Types
- **IDs**: `TEXT` (DOF uses UUID strings from Python `uuid4()`)
- **Timestamps**: always `TIMESTAMPTZ`, never `TIMESTAMP`
- **Scores/Floats**: `DOUBLE PRECISION` for governance scores, relevance
- **Metadata**: `JSONB` with GIN index for flexible attributes
- **Strings**: `TEXT`, never `VARCHAR(n)` or `CHAR(n)`
- **Money**: `NUMERIC(p,s)` if ever needed (never float)
- **Booleans**: `BOOLEAN NOT NULL` (e.g., `z3_verified`)

### Indexing Strategy
- **B-tree**: default for equality/range (`category`, `governance_status`, `created_at`)
- **GIN**: for JSONB containment queries on `metadata_`
- **FK columns**: always index manually (PostgreSQL doesn't auto-index FKs)
- **Partial indexes**: consider for hot subsets (`WHERE governance_status = 'approved'`)

### Constraints
- `NOT NULL` everywhere semantically required
- `DEFAULT` values for common fields (`now()`, empty string, `0.0`)
- `CHECK` constraints for valid ranges: `CHECK (relevance >= 0.0 AND relevance <= 1.0)`

## JSONB Patterns for DOF

DOF stores flexible metadata in JSONB columns:

```python
# SQLAlchemy column definition
from sqlalchemy import Column, JSON

metadata_ = Column("metadata_", JSON, nullable=False, server_default="{}")
```

Query patterns:
```sql
-- Find memories with specific metadata key
SELECT * FROM dof_memories WHERE metadata_ ? 'source';

-- Find memories with specific metadata value
SELECT * FROM dof_memories WHERE metadata_ @> '{"source": "governance"}';

-- Filter by nested JSONB field
SELECT * FROM dof_audit_events WHERE details->>'action' = 'memory_add';
```

## Adding New Tables to DOF

When extending `core/storage.py`:

1. Define SQLAlchemy model with `if HAS_SQLALCHEMY` guard:
```python
if HAS_SQLALCHEMY:
    class _NewRow(Base):
        __tablename__ = "dof_new_table"
        id = Column(String, primary_key=True)
        # ... columns
```

2. Add `save_*` and `load_*` methods to both `JSONLBackend` and `PostgreSQLBackend`
3. Update `StorageBackend` ABC with new abstract methods
4. Add migration support in `migrate_jsonl_to_postgres()`
5. Write tests using SQLite in-memory as PostgreSQL proxy

## Performance Patterns

### Insert-Heavy (Audit Events, Traces)
- Minimize indexes on high-write tables
- Consider `UNLOGGED` for non-critical staging data
- Batch inserts where possible
- Partition by time for very large audit tables

### Query-Heavy (Memory Queries)
- GIN index on `metadata_` for flexible queries
- Partial indexes for frequently filtered subsets
- Covering indexes for common access patterns

### DOF-Specific Considerations
- **Dual-write overhead**: PostgreSQL write is secondary; JSONL is always primary
- **Backend failure tolerance**: if PostgreSQL fails, JSONL continues (warning logged)
- **Migration**: `migrate_jsonl_to_postgres()` for JSONL → PostgreSQL one-time migration
- **SQLite proxy for tests**: use `sqlite:///:memory:` in tests (no PostgreSQL required)

## Common Pitfalls

- Using `timestamp` without timezone (always use `timestamptz`)
- Using `serial` instead of `generated always as identity`
- Not indexing FK columns manually
- Storing governance scores as `INTEGER` instead of `DOUBLE PRECISION`
- Using `VARCHAR(n)` instead of `TEXT`
- Not using `JSONB` (using `JSON` loses indexing benefits)
- Forgetting `NOT NULL` on columns that should never be null
- Not adding `server_default` in SQLAlchemy (causes NULL on DB-level inserts)

## Supabase-Specific Notes

DOF uses Supabase PostgreSQL:
- Connection via `DOF_DATABASE_URL` env var
- Pooler URL format: `postgresql://postgres.{project}:{password}@{host}:5432/postgres`
- Row Level Security available but not currently used
- Auto-creates tables via SQLAlchemy `Base.metadata.create_all()`
