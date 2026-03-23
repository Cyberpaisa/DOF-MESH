"""
Memory Manager — Cross-session memory with TTL and compression.

Uses JSONL for persistence (no OpenAI dependency).
Memory types: short-term (session), long-term (persisted), episodic (run results).
"""

import os
import json
import time
import logging
from dataclasses import dataclass, asdict

logger = logging.getLogger("core.memory_manager")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMORY_DIR = os.path.join(BASE_DIR, "memory")


@dataclass
class MemoryEntry:
    """A single memory record."""
    key: str
    value: str
    memory_type: str  # short_term | long_term | episodic
    created_at: float = 0.0
    ttl_seconds: float = 0.0  # 0 = no expiry
    source: str = ""  # which agent/crew created it
    tags: list[str] | None = None


class MemoryManager:
    """Cross-session memory manager with JSONL persistence.

    No OpenAI or embedder dependency — pure text-based retrieval.
    """

    def __init__(self):
        os.makedirs(MEMORY_DIR, exist_ok=True)
        self._short_term: dict[str, MemoryEntry] = {}
        self._long_term_file = os.path.join(MEMORY_DIR, "long_term.jsonl")
        self._episodic_file = os.path.join(MEMORY_DIR, "episodic.jsonl")

    # ── Short-term (session only) ──

    def remember(self, key: str, value: str, source: str = "",
                 ttl: float = 3600, tags: list[str] | None = None):
        """Store short-term memory (session-scoped, default 1h TTL)."""
        self._short_term[key] = MemoryEntry(
            key=key, value=value, memory_type="short_term",
            created_at=time.time(), ttl_seconds=ttl,
            source=source, tags=tags,
        )

    def recall(self, key: str) -> str | None:
        """Recall short-term memory if not expired."""
        entry = self._short_term.get(key)
        if not entry:
            return None
        if entry.ttl_seconds > 0:
            if time.time() - entry.created_at > entry.ttl_seconds:
                del self._short_term[key]
                return None
        return entry.value

    def get_context(self, max_entries: int = 10) -> str:
        """Get all active short-term memories as context string."""
        self._cleanup_expired()
        entries = list(self._short_term.values())[-max_entries:]
        if not entries:
            return ""
        lines = ["## Contexto de sesión activo:"]
        for e in entries:
            lines.append(f"- **{e.key}**: {e.value[:300]}")
        return "\n".join(lines)

    # ── Long-term (persisted) ──

    def store_long_term(self, key: str, value: str, source: str = "",
                        tags: list[str] | None = None):
        """Persist a long-term memory to disk."""
        entry = MemoryEntry(
            key=key, value=value, memory_type="long_term",
            created_at=time.time(), source=source, tags=tags,
        )
        self._append_jsonl(self._long_term_file, entry)
        logger.info(f"Long-term memory stored: {key}")

    def search_long_term(self, query: str, max_results: int = 5) -> list[MemoryEntry]:
        """Search long-term memory using Fisher-Rao similarity.

        Uses information geometry (Fisher-Rao distance on term frequency
        distributions) for semantic-aware retrieval. Falls back to keyword
        matching if Fisher-Rao module is unavailable.
        """
        entries = self._load_jsonl(self._long_term_file)
        if not entries:
            return []

        try:
            from core.fisher_rao import fisher_rao_similarity
            # Rank by Fisher-Rao similarity (higher = better)
            scored = []
            for e in entries:
                full_text = f"{e.key} {e.value}"
                sim = fisher_rao_similarity(query, full_text)
                scored.append((sim, e))
            scored.sort(key=lambda x: x[0], reverse=True)
            # Filter: minimum similarity threshold 0.05
            results = [e for sim, e in scored[:max_results] if sim > 0.05]
            if results:
                return results
        except ImportError:
            pass

        # Fallback: keyword matching
        query_lower = query.lower()
        matches = [
            e for e in entries
            if query_lower in e.key.lower() or query_lower in e.value.lower()
        ]
        return matches[-max_results:]

    # ── Episodic (run results) ──

    def store_episode(self, run_id: str, crew_name: str, input_text: str,
                      output_text: str, status: str, source: str = ""):
        """Store a crew execution episode."""
        entry = MemoryEntry(
            key=f"{crew_name}:{run_id}",
            value=json.dumps({
                "crew": crew_name,
                "input": input_text[:500],
                "output": output_text[:2000],
                "status": status,
            }),
            memory_type="episodic",
            created_at=time.time(),
            source=source,
        )
        self._append_jsonl(self._episodic_file, entry)

    def get_recent_episodes(self, crew_name: str = "", n: int = 5) -> list[dict]:
        """Get recent execution episodes. Returns [] for n <= 0."""
        if n <= 0:
            return []
        entries = self._load_jsonl(self._episodic_file)
        if crew_name:
            entries = [e for e in entries if crew_name in e.key]
        results = []
        for e in entries[-n:]:
            try:
                data = json.loads(e.value)
                data["timestamp"] = e.created_at
                results.append(data)
            except json.JSONDecodeError:
                pass
        return results

    # ── Internal ──

    def _cleanup_expired(self):
        """Remove expired short-term entries."""
        now = time.time()
        expired = [
            k for k, v in self._short_term.items()
            if v.ttl_seconds > 0 and now - v.created_at > v.ttl_seconds
        ]
        for k in expired:
            del self._short_term[k]

    @staticmethod
    def _append_jsonl(filepath: str, entry: MemoryEntry):
        """Append entry to JSONL file."""
        try:
            data = asdict(entry)
            with open(filepath, "a") as f:
                f.write(json.dumps(data, default=str) + "\n")
        except Exception as e:
            logger.error(f"Memory write error: {e}")

    @staticmethod
    def _load_jsonl(filepath: str) -> list[MemoryEntry]:
        """Load entries from JSONL file."""
        if not os.path.exists(filepath):
            return []
        entries = []
        try:
            with open(filepath) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    entries.append(MemoryEntry(**data))
        except Exception as e:
            logger.error(f"Memory load error: {e}")
        return entries
