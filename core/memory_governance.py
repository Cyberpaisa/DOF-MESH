"""
Memory Governance — Constitutional memory store with governance enforcement.

GovernedMemoryStore: add/update/delete with ConstitutionEnforcer validation on
every operation. All operations are logged to JSONL for full audit trail.

TemporalGraph: bi-temporal versioning with point-in-time snapshots, timeline,
diff, and age distribution for dashboards.

MemoryClassifier: deterministic keyword-based category assignment (no LLM).

ConstitutionalDecay: relevance decay with protected categories.

Zero external dependencies. Zero LLM involvement. Fully deterministic.

Usage:
    from core.memory_governance import GovernedMemoryStore, TemporalGraph
    from core.memory_governance import MemoryClassifier, ConstitutionalDecay
    store = GovernedMemoryStore()
    entry = store.add("The Z3 verifier proved GCR invariant.", category="knowledge")
    graph = TemporalGraph(store)
    snapshot = graph.snapshot(as_of=datetime(2026, 3, 1))
    classifier = MemoryClassifier()
    category = classifier.classify("error in provider")  # → "errors"
    decay = ConstitutionalDecay(store)
    decay.decay_cycle()
"""

import os
import re
import uuid
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("core.memory_governance")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMORY_DIR = os.path.join(BASE_DIR, "memory")
STORE_FILE = os.path.join(MEMORY_DIR, "governed_store.jsonl")
LOG_FILE = os.path.join(BASE_DIR, "logs", "memory_governance.jsonl")
DECAY_LOG_FILE = os.path.join(BASE_DIR, "logs", "memory_decay.jsonl")

VALID_CATEGORIES = {"knowledge", "preferences", "context", "decisions", "errors"}


# ─────────────────────────────────────────────────────────────────────
# Data class
# ─────────────────────────────────────────────────────────────────────

@dataclass
class MemoryEntry:
    """A governed memory record with full versioning and temporal validity."""
    id: str
    content: str
    category: str               # knowledge | preferences | context | decisions | errors
    metadata: dict = field(default_factory=dict)
    valid_from: str = ""        # ISO 8601 UTC
    valid_to: Optional[str] = None   # None = currently active
    recorded_at: str = ""
    relevance_score: float = 1.0
    governance_status: str = "approved"   # approved | warning | rejected
    version: int = 1
    parent_id: Optional[str] = None      # points to previous version
    root_id: Optional[str] = None        # points to version 1 (None = this IS the root)


class ConflictError(Exception):
    """Raised when optimistic concurrency check fails in update()."""
    pass


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(s: str) -> datetime:
    """Parse ISO string; always return timezone-aware datetime (UTC if naive)."""
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _ensure_aware(dt: datetime) -> datetime:
    """Return timezone-aware datetime; if naive, assume UTC."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _to_dict(entry: MemoryEntry) -> dict:
    return asdict(entry)


def _from_dict(d: dict) -> MemoryEntry:
    # Backward compat: old JSONL may lack root_id
    if "root_id" not in d:
        d["root_id"] = None
    return MemoryEntry(**d)


# ─────────────────────────────────────────────────────────────────────
# GovernedMemoryStore
# ─────────────────────────────────────────────────────────────────────

class GovernedMemoryStore:
    """Memory store with constitutional governance on every add/update/delete.

    Governance rules from dof.constitution.yml are enforced via ConstitutionEnforcer:
      - HARD_RULE violation → entry marked "rejected" (not active)
      - SOFT_RULE violation → entry marked "warning" (stored but flagged)
      - No violations       → entry marked "approved"

    Persistence: append-only JSONL in memory/governed_store.jsonl.
    Audit log:   append-only JSONL in logs/memory_governance.jsonl.
    Optional:    StorageBackend (PostgreSQL) for production persistence.
    """

    def __init__(
        self,
        constitution_path: str = "dof.constitution.yml",
        _store_file: str = None,
        _log_file: str = None,
        _storage_backend=None,
    ):
        self._store_file = _store_file or STORE_FILE
        self._log_file = _log_file or LOG_FILE
        os.makedirs(os.path.dirname(self._store_file), exist_ok=True)
        os.makedirs(os.path.dirname(self._log_file), exist_ok=True)
        self._entries: list[MemoryEntry] = []
        self._root_index: dict[str, list[MemoryEntry]] = {}  # root_id → versions
        self._decay: Optional["ConstitutionalDecay"] = None

        # Storage backend (optional — for dual persistence)
        self._backend = _storage_backend

        # Load memory config from constitution YAML
        self._memory_config = self._load_memory_config(constitution_path)

        self._load_state()

    # ─── Config ─────────────────────────────────────────────────

    @staticmethod
    def _load_memory_config(constitution_path: str) -> dict:
        """Load memory section from dof.constitution.yml. Returns defaults on failure."""
        defaults = {
            "categories": list(VALID_CATEGORIES),
            "decay": {"lambda": 0.99, "threshold": 0.1, "protected_categories": ["decisions", "errors"]},
            "limits": {"max_memories": 10000, "max_content_length": 50000},
            "governance": {"enforce_on_add": True, "enforce_on_update": True, "log_queries": True},
        }
        try:
            import yaml
            path = constitution_path
            if not os.path.isabs(path):
                path = os.path.join(BASE_DIR, path)
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return data.get("memory", defaults)
        except Exception:
            return defaults

    # ─── Persistence ──────────────────────────────────────────────

    def _load_state(self) -> None:
        """Load and reconstruct state from JSONL store."""
        if not os.path.exists(self._store_file):
            return
        try:
            # Last-written record for each ID takes precedence (handles deletes)
            entries_by_id: dict[str, MemoryEntry] = {}
            with open(self._store_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    d = json.loads(line)
                    entries_by_id[d["id"]] = _from_dict(d)

            self._entries = list(entries_by_id.values())

            # Reconstruct valid_to for parents superseded by a newer version
            id_map = {e.id: e for e in self._entries}
            for e in self._entries:
                if e.parent_id and e.parent_id in id_map:
                    parent = id_map[e.parent_id]
                    if parent.valid_to is None:
                        parent.valid_to = e.valid_from

            # Rebuild root_id index
            self._rebuild_root_index()
        except Exception as exc:
            logger.error(f"Failed to load memory store: {exc}")

    def _rebuild_root_index(self) -> None:
        """Rebuild root_id → [entries] index from current entries."""
        self._root_index.clear()
        for e in self._entries:
            root = e.root_id or e.id
            self._root_index.setdefault(root, []).append(e)

    def _index_entry(self, entry: MemoryEntry) -> None:
        """Add a single entry to the root index."""
        root = entry.root_id or entry.id
        self._root_index.setdefault(root, []).append(entry)

    def _persist_entry(self, entry: MemoryEntry) -> None:
        """Append entry to the JSONL store and optional backend."""
        try:
            with open(self._store_file, "a") as f:
                f.write(json.dumps(_to_dict(entry)) + "\n")
        except Exception as exc:
            logger.error(f"Failed to persist memory entry: {exc}")
        # Dual-write to storage backend if available
        if self._backend is not None:
            try:
                self._backend.save_memory(_to_dict(entry))
            except Exception as exc:
                logger.warning(f"Backend save_memory failed: {exc}")

    def _log_op(self, operation: str, memory_id: str, status: str, reason: str = "") -> None:
        """Append an audit entry to memory_governance.jsonl."""
        try:
            record = {
                "timestamp": _now_iso(),
                "operation": operation,
                "memory_id": memory_id,
                "status": status,
                "reason": reason,
            }
            with open(self._log_file, "a") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as exc:
            logger.warning(f"Failed to log memory operation: {exc}")

    # ─── Governance ───────────────────────────────────────────────

    def _check_governance(self, content: str) -> str:
        """Run ConstitutionEnforcer on content.

        Returns 'approved', 'warning', or 'rejected'.
        Fails open on import errors (governance unavailable → approved).
        """
        try:
            from core.governance import ConstitutionEnforcer
            enforcer = ConstitutionEnforcer()
            result = enforcer.check(content)
            if not result.passed:
                return "rejected"
            if result.warnings:
                return "warning"
            return "approved"
        except Exception as exc:
            logger.warning(f"Governance check failed: {exc} — failing open")
            return "approved"

    # ─── Similarity ───────────────────────────────────────────────

    def _keyword_similarity(self, a: str, b: str) -> float:
        """Fraction of shared tokens relative to the shorter document."""
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        if not words_a or not words_b:
            return 0.0
        overlap = words_a & words_b
        return len(overlap) / min(len(words_a), len(words_b))

    def _find_similar(self, content: str, category: str) -> Optional[MemoryEntry]:
        """Return an active, non-rejected memory with >70% keyword overlap, or None."""
        for e in self._entries:
            if e.valid_to is not None:
                continue
            if e.governance_status == "rejected":
                continue
            if e.category != category:
                continue
            if self._keyword_similarity(content, e.content) > 0.70:
                return e
        return None

    # ─── Public API ───────────────────────────────────────────────

    def add(
        self,
        content: str,
        category: str = "",
        metadata: dict = None,
    ) -> MemoryEntry:
        """Add a governed memory entry.

        If a similar active memory exists (>70% keyword overlap in same category),
        calls update() instead of creating a duplicate.

        Returns MemoryEntry with governance_status in {'approved','warning','rejected'}.
        Rejected entries are persisted for audit but NOT returned by query().
        """
        metadata = metadata or {}
        if not category or category not in VALID_CATEGORIES:
            classifier = MemoryClassifier()
            category = classifier.classify(content)

        # Merge with similar existing memory instead of duplicating
        similar = self._find_similar(content, category)
        if similar is not None:
            return self.update(similar.id, content)

        gov_status = self._check_governance(content)
        now = _now_iso()
        entry = MemoryEntry(
            id=str(uuid.uuid4()),
            content=content,
            category=category,
            metadata=metadata,
            valid_from=now,
            valid_to=None,
            recorded_at=now,
            relevance_score=1.0,
            governance_status=gov_status,
            version=1,
            parent_id=None,
            root_id=None,  # this IS the root
        )

        self._entries.append(entry)
        self._index_entry(entry)
        self._persist_entry(entry)
        self._log_op("add", entry.id, gov_status,
                     "HARD_RULE violation" if gov_status == "rejected" else "")
        return entry

    def update(
        self,
        memory_id: str,
        new_content: str,
        expected_version: int = None,
    ) -> MemoryEntry:
        """Create a new version of an existing memory (non-destructive).

        The previous version is marked valid_to=now in memory.
        The new version has version+1 and parent_id pointing to the previous.

        If expected_version is provided and doesn't match the current version,
        raises ConflictError (optimistic concurrency control).
        """
        existing = next((e for e in self._entries if e.id == memory_id), None)
        if existing is None:
            return self.add(new_content)

        # Optimistic concurrency check
        if expected_version is not None and existing.version != expected_version:
            raise ConflictError(
                f"Version conflict: expected {expected_version}, "
                f"found {existing.version} for memory {memory_id}"
            )

        gov_status = self._check_governance(new_content)
        now = _now_iso()

        # Mark old version as expired (in-memory; reconstructed from child on reload)
        existing.valid_to = now

        # root_id: inherit from existing, or use existing.id if existing is the root
        new_root_id = existing.root_id or existing.id

        new_entry = MemoryEntry(
            id=str(uuid.uuid4()),
            content=new_content,
            category=existing.category,
            metadata=existing.metadata.copy(),
            valid_from=now,
            valid_to=None,
            recorded_at=now,
            relevance_score=existing.relevance_score,
            governance_status=gov_status,
            version=existing.version + 1,
            parent_id=memory_id,
            root_id=new_root_id,
        )
        self._entries.append(new_entry)
        self._index_entry(new_entry)
        self._persist_entry(new_entry)
        self._log_op("update", new_entry.id, gov_status, f"parent={memory_id}")
        return new_entry

    def delete(self, memory_id: str, reason: str = "") -> bool:
        """Soft-delete: mark valid_to=now without physical removal.

        Persists the deletion by appending the modified entry to JSONL.
        Returns True if found and marked.
        """
        entry = next((e for e in self._entries if e.id == memory_id), None)
        if entry is None:
            return False
        entry.valid_to = _now_iso()
        self._persist_entry(entry)   # append with valid_to set
        self._log_op("delete", memory_id, "deleted", reason)
        return True

    def query(
        self,
        query: str = "",
        category: str = "",
        as_of: datetime = None,
    ) -> list[MemoryEntry]:
        """Return active memories matching optional keyword, category, and time filters.

        If as_of is provided, returns the state at that point in time
        (entries where valid_from <= as_of < valid_to or valid_to is None).
        Results are ordered by relevance_score descending.
        """
        results = []
        for e in self._entries:
            if e.governance_status == "rejected":
                continue

            if as_of:
                as_of = _ensure_aware(as_of)
                valid_from_dt = _parse_iso(e.valid_from)
                if valid_from_dt > as_of:
                    continue
                if e.valid_to is not None:
                    valid_to_dt = _parse_iso(e.valid_to)
                    if valid_to_dt <= as_of:
                        continue
            else:
                if e.valid_to is not None:
                    continue

            if category and e.category != category:
                continue

            if query:
                query_lower = query.lower()
                if not any(w in e.content.lower() for w in query_lower.split()):
                    continue

            results.append(e)

        results.sort(key=lambda e: e.relevance_score, reverse=True)

        # Reinforce queried memories (access = relevance boost)
        if self._decay is not None:
            for e in results:
                self._decay.reinforce(e.id)

        return results

    def get_history(self, memory_id: str) -> list[MemoryEntry]:
        """Return all versions of a memory chain in chronological order.

        Uses root_id index for O(1) lookup instead of O(n) chain traversal.
        """
        target = next((e for e in self._entries if e.id == memory_id), None)
        if target is None:
            return []

        # Determine the root_id for this chain
        target_root = target.root_id or target.id

        # O(1) lookup via root index
        chain = self._root_index.get(target_root, [])
        if not chain:
            return [target]

        chain = list(chain)  # copy to avoid mutating index
        chain.sort(key=lambda e: e.valid_from)
        return chain

    def get_stats(self) -> dict:
        """Return summary statistics for the memory store."""
        active = [
            e for e in self._entries
            if e.valid_to is None and e.governance_status != "rejected"
        ]
        by_category: dict[str, int] = {}
        by_status: dict[str, int] = {}

        for e in self._entries:
            by_status[e.governance_status] = by_status.get(e.governance_status, 0) + 1

        for e in active:
            by_category[e.category] = by_category.get(e.category, 0) + 1

        avg_relevance = (
            sum(e.relevance_score for e in active) / len(active) if active else 0.0
        )
        return {
            "total_memories": len(self._entries),
            "active_memories": len(active),
            "by_category": by_category,
            "by_status": by_status,
            "avg_relevance": round(avg_relevance, 3),
        }


# ─────────────────────────────────────────────────────────────────────
# TemporalGraph — bi-temporal versioning layer
# ─────────────────────────────────────────────────────────────────────

class TemporalGraph:
    """Bi-temporal versioning over GovernedMemoryStore.

    Provides point-in-time snapshots, timeline of changes, diff between
    two dates, and age distribution for dashboard rendering.

    "What did the agent know last Tuesday at 3 pm?"
    """

    def __init__(self, store: GovernedMemoryStore):
        self._store = store

    # ─── snapshot ─────────────────────────────────────────────────

    def snapshot(self, as_of: datetime) -> list[MemoryEntry]:
        """Return the complete memory state at a specific point in time.

        For versioned memories, returns only the version that was active
        at *as_of*.  Rejected entries are excluded.
        """
        # Gather all entries valid at as_of
        as_of = _ensure_aware(as_of)
        candidates = []
        for e in self._store._entries:
            if e.governance_status == "rejected":
                continue
            vf = _parse_iso(e.valid_from)
            if vf > as_of:
                continue
            if e.valid_to is not None:
                vt = _parse_iso(e.valid_to)
                if vt <= as_of:
                    continue
            candidates.append(e)

        # For versioned chains keep only the latest version at as_of
        # (i.e., highest version number per root chain).
        root_map: dict[str, MemoryEntry] = {}
        for e in candidates:
            root_id = self._root_id(e)
            existing = root_map.get(root_id)
            if existing is None or e.version > existing.version:
                root_map[root_id] = e

        return sorted(root_map.values(), key=lambda e: e.valid_from)

    def _root_id(self, entry: MemoryEntry) -> str:
        """Return the root id for a version chain. O(1) via root_id field."""
        return entry.root_id or entry.id

    # ─── timeline ─────────────────────────────────────────────────

    def timeline(self, category: str = None) -> list[dict]:
        """Return a chronological timeline of ALL memory mutations.

        Each event: {memory_id, action, timestamp, category, content_summary}.
        """
        events: list[dict] = []
        for e in self._store._entries:
            if category and e.category != category:
                continue

            # Determine action
            if e.parent_id is None:
                action = "ADD"
            else:
                action = "UPDATE"

            events.append({
                "memory_id": e.id,
                "action": action,
                "timestamp": e.valid_from,
                "category": e.category,
                "content_summary": e.content[:100],
            })

            # Detect explicit deletes (valid_to set, no child superseding)
            if e.valid_to is not None:
                has_child = any(
                    c.parent_id == e.id for c in self._store._entries
                )
                if not has_child:
                    events.append({
                        "memory_id": e.id,
                        "action": "DELETE",
                        "timestamp": e.valid_to,
                        "category": e.category,
                        "content_summary": e.content[:100],
                    })

        events.sort(key=lambda ev: ev["timestamp"])
        return events

    # ─── diff ─────────────────────────────────────────────────────

    def diff(self, from_date: datetime, to_date: datetime) -> dict:
        """Compare memory state between two dates.

        Returns {added: [...], updated: [...], deleted: [...], unchanged: int}.
        """
        snap_from = {e.id: e for e in self.snapshot(as_of=from_date)}
        snap_to = {e.id: e for e in self.snapshot(as_of=to_date)}

        # Map each snapshot entry to its root chain for comparison
        roots_from: dict[str, MemoryEntry] = {}
        for e in snap_from.values():
            roots_from[self._root_id(e)] = e

        roots_to: dict[str, MemoryEntry] = {}
        for e in snap_to.values():
            roots_to[self._root_id(e)] = e

        added = []
        updated = []
        deleted = []
        unchanged = 0

        for root_id, entry in roots_to.items():
            if root_id not in roots_from:
                added.append(entry.id)
            else:
                old_entry = roots_from[root_id]
                if old_entry.id != entry.id:
                    # Different version → updated
                    updated.append(entry.id)
                else:
                    unchanged += 1

        for root_id in roots_from:
            if root_id not in roots_to:
                deleted.append(roots_from[root_id].id)

        return {
            "added": added,
            "updated": updated,
            "deleted": deleted,
            "unchanged": unchanged,
        }

    # ─── age distribution ─────────────────────────────────────────

    def memory_age_distribution(self) -> dict:
        """Return age distribution of active memories in buckets.

        Buckets: <1h, 1h-24h, 1d-7d, 7d-30d, >30d.
        """
        now = datetime.now(timezone.utc)
        buckets = {
            "<1h": 0,
            "1h-24h": 0,
            "1d-7d": 0,
            "7d-30d": 0,
            ">30d": 0,
        }
        for e in self._store._entries:
            if e.valid_to is not None or e.governance_status == "rejected":
                continue
            age = now - _parse_iso(e.valid_from)
            hours = age.total_seconds() / 3600
            if hours < 1:
                buckets["<1h"] += 1
            elif hours < 24:
                buckets["1h-24h"] += 1
            elif hours < 24 * 7:
                buckets["1d-7d"] += 1
            elif hours < 24 * 30:
                buckets["7d-30d"] += 1
            else:
                buckets[">30d"] += 1
        return buckets


# ─────────────────────────────────────────────────────────────────────
# MemoryClassifier — deterministic keyword-based categorization
# ─────────────────────────────────────────────────────────────────────

# Keyword → category mapping.
# Priority order: decisions > errors > context > preferences > knowledge (default).
# Uses regex word boundaries to prevent false positives.
_CATEGORY_KEYWORDS: list[tuple[str, list[str]]] = [
    ("decisions", ["decidido", "decided", "elegimos", "optamos", "chose"]),
    ("errors", ["error", "fail", "exception", "bug", "crash"]),
    ("context", ["task", "pending", "current", "session", "working on"]),
    ("preferences", ["prefer", "config", "setting", "option"]),
]


def _word_match(keyword: str, text: str) -> bool:
    """Check if keyword matches as a whole word (or phrase) in text."""
    # For multi-word keywords like "working on", use literal match
    if " " in keyword:
        return keyword in text
    return bool(re.search(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE))


class MemoryClassifier:
    """Deterministic category assignment via keyword matching.

    No LLM — pure pattern matching against predefined keyword lists.
    Categories: knowledge, preferences, context, decisions, errors.
    Priority: decisions > errors > context > preferences > knowledge (default).
    Uses regex word boundaries to prevent false positives.
    """

    def classify(self, content: str) -> str:
        """Classify content into a category by keyword matching.

        Priority: decisions > errors > context > preferences > knowledge.
        Uses word boundaries for accurate matching.
        Default: "knowledge".
        """
        text_lower = content.lower()
        for category, keywords in _CATEGORY_KEYWORDS:
            for kw in keywords:
                if _word_match(kw, text_lower):
                    return category
        return "knowledge"

    def classify_with_confidence(self, content: str) -> tuple[str, float]:
        """Classify with confidence score.

        Confidence = matched_keywords / total_keywords_checked across ALL categories.
        If confidence < 0.3, returns ("uncategorized", confidence).
        Priority order is respected for the best_category selection.
        """
        text_lower = content.lower()
        total_keywords = sum(len(kws) for _, kws in _CATEGORY_KEYWORDS)
        matched = 0
        best_category = "knowledge"
        best_count = 0

        for category, keywords in _CATEGORY_KEYWORDS:
            cat_matches = sum(1 for kw in keywords if _word_match(kw, text_lower))
            matched += cat_matches
            if cat_matches > best_count:
                best_count = cat_matches
                best_category = category

        confidence = matched / total_keywords if total_keywords > 0 else 0.0

        if confidence < 0.3:
            return ("uncategorized", round(confidence, 4))
        return (best_category, round(confidence, 4))


# ─────────────────────────────────────────────────────────────────────
# ConstitutionalDecay — relevance decay with protected categories
# ─────────────────────────────────────────────────────────────────────

class ConstitutionalDecay:
    """Exponential relevance decay with constitutional protections.

    Protected categories (decisions, errors) never decay.
    When relevance_score drops below threshold, the memory is archived
    (valid_to=now) unless it belongs to a protected category.

    All decay cycles are logged to logs/memory_decay.jsonl.
    """

    def __init__(
        self,
        store: GovernedMemoryStore,
        decay_lambda: float = 0.99,
        threshold: float = 0.1,
        _decay_log_file: str = None,
    ):
        self._store = store
        self._decay_lambda = decay_lambda
        self._threshold = threshold
        self._protected_categories = {"decisions", "errors"}
        self._decay_log_file = _decay_log_file or DECAY_LOG_FILE
        os.makedirs(os.path.dirname(self._decay_log_file), exist_ok=True)

    def decay_cycle(self) -> dict:
        """Apply exponential decay to all active memories.

        For each active memory:
          - If category is protected → skip (no decay)
          - Else: relevance_score *= decay_lambda ^ hours_since_last_update
          - If score < threshold → archive (valid_to=now)

        Returns {processed, decayed, archived, protected}.
        """
        now = datetime.now(timezone.utc)
        processed = 0
        decayed = 0
        archived = 0
        protected = 0

        for entry in self._store._entries:
            # Skip inactive or rejected
            if entry.valid_to is not None:
                continue
            if entry.governance_status == "rejected":
                continue

            processed += 1

            # Protected categories never decay
            if entry.category in self._protected_categories:
                protected += 1
                continue

            # Calculate hours since last update (valid_from)
            last_update = _parse_iso(entry.valid_from)
            hours = (now - last_update).total_seconds() / 3600
            if hours <= 0:
                continue

            # Apply exponential decay
            old_score = entry.relevance_score
            entry.relevance_score = old_score * (self._decay_lambda ** hours)
            decayed += 1

            # Archive if below threshold
            if entry.relevance_score < self._threshold:
                entry.valid_to = _now_iso()
                self._store._persist_entry(entry)
                archived += 1

        result = {
            "processed": processed,
            "decayed": decayed,
            "archived": archived,
            "protected": protected,
        }

        # Log the cycle
        self._log_cycle(result)
        return result

    def reinforce(self, memory_id: str, boost: float = 0.1) -> float:
        """Reinforce a memory's relevance score (capped at 1.0).

        Called when a memory is accessed/queried to keep it alive.
        Returns the new score, or -1.0 if not found.
        """
        entry = next(
            (e for e in self._store._entries if e.id == memory_id), None
        )
        if entry is None:
            return -1.0
        entry.relevance_score = min(1.0, entry.relevance_score + boost)
        return entry.relevance_score

    def get_decay_status(self) -> list[dict]:
        """Return active memories sorted by relevance_score ascending.

        Lowest-score memories are listed first (most likely to be archived next).
        """
        active = [
            e for e in self._store._entries
            if e.valid_to is None and e.governance_status != "rejected"
        ]
        active.sort(key=lambda e: e.relevance_score)
        return [
            {
                "id": e.id,
                "category": e.category,
                "relevance_score": round(e.relevance_score, 4),
                "content_summary": e.content[:100],
                "protected": e.category in self._protected_categories,
            }
            for e in active
        ]

    def _log_cycle(self, result: dict) -> None:
        """Append decay cycle result to memory_decay.jsonl."""
        try:
            record = {
                "timestamp": _now_iso(),
                "operation": "decay_cycle",
                **result,
            }
            with open(self._decay_log_file, "a") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as exc:
            logger.warning(f"Failed to log decay cycle: {exc}")
