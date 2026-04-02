"""
Memory Manager — Cross-session memory with TTL and compression.

Uses JSONL for persistence (no OpenAI dependency).
Memory types: short-term (session), long-term (persisted), episodic (run results).

Search strategy (hybrid, inspired by S+Memory):
  score = fisher_rao(0.4) + bm25(0.4) + temporal_decay(0.2)
  Temporal tiers: recent(0-7d)×2.0 | medium(7-30d)×1.0 | old(30-90d)×0.5 | archived(90+d)×0.1
"""

import math
import os
import json
import time
import logging
from dataclasses import dataclass, field, asdict

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
    access_count: int = 0       # S+Memory: how many times retrieved
    last_accessed: float = 0.0  # S+Memory: timestamp of last retrieval


# ─────────────────────────────────────────────────────────────────────
# S+Memory: Temporal Decay + BM25 (pure Python, zero deps)
# λ=0.05, tiers: recent(0-7d)×2.0 | medium(7-30d)×1.0 | old(30-90d)×0.5 | archived(90+d)×0.1
# ─────────────────────────────────────────────────────────────────────

def _temporal_multiplier(created_at: float) -> float:
    """Return recency boost multiplier based on age of memory."""
    age_days = (time.time() - created_at) / 86400
    if age_days <= 7:
        return 2.0
    elif age_days <= 30:
        return 1.0
    elif age_days <= 90:
        return 0.5
    return 0.1


def _bm25_score(query: str, text: str, corpus_texts: list[str],
                k1: float = 1.5, b: float = 0.75) -> float:
    """Pure-Python BM25 score for (query, text) given a corpus.

    No external dependencies — implements Okapi BM25 from scratch.
    """
    query_terms = query.lower().split()
    if not query_terms:
        return 0.0

    # Tokenize corpus
    tokenized = [t.lower().split() for t in corpus_texts]
    N = len(tokenized)
    if N == 0:
        return 0.0

    avg_dl = sum(len(d) for d in tokenized) / N
    doc_tokens = text.lower().split()
    dl = len(doc_tokens)
    score = 0.0

    for term in query_terms:
        # Term frequency in document
        tf = doc_tokens.count(term)
        if tf == 0:
            continue
        # Document frequency across corpus
        df = sum(1 for d in tokenized if term in d)
        # IDF (Robertson-Spärck Jones)
        idf = math.log((N - df + 0.5) / (df + 0.5) + 1)
        # BM25 term score
        tf_norm = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / avg_dl))
        score += idf * tf_norm

    return score


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
        """Search long-term memory using hybrid scoring.

        Hybrid score = fisher_rao(0.4) + bm25(0.4) + temporal_decay(0.2)

        Fisher-Rao captures semantic similarity via information geometry.
        BM25 captures lexical/keyword relevance (pure Python, zero deps).
        Temporal decay boosts recent memories, fades archived ones.

        Falls back to keyword matching if all scoring fails.
        """
        entries = self._load_jsonl(self._long_term_file)
        if not entries:
            return []

        corpus_texts = [f"{e.key} {e.value}" for e in entries]

        # Try Fisher-Rao for semantic component
        fisher_scores: dict[int, float] = {}
        try:
            from core.fisher_rao import fisher_rao_similarity
            for i, e in enumerate(entries):
                fisher_scores[i] = fisher_rao_similarity(query, corpus_texts[i])
        except ImportError:
            pass

        scored = []
        for i, e in enumerate(entries):
            fr = fisher_scores.get(i, 0.0)
            bm25 = _bm25_score(query, corpus_texts[i], corpus_texts)
            # Normalize BM25 to [0,1] range (cap at 20 for practical texts)
            bm25_norm = min(bm25 / 20.0, 1.0)
            temporal = _temporal_multiplier(e.created_at) / 2.0  # normalize 0.05–1.0
            hybrid = fr * 0.4 + bm25_norm * 0.4 + temporal * 0.2
            scored.append((hybrid, e))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = [e for score, e in scored[:max_results] if score > 0.05]
        if results:
            logger.debug(f"Hybrid search '{query[:40]}': top score={scored[0][0]:.3f}, {len(results)} results")
            return results

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
