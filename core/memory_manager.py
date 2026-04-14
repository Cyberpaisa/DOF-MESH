from __future__ import annotations
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
from typing import Optional, List, Dict, Union, Any, Tuple

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
    tags: Optional[List[str]] = None
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
        self._short_term: Dict[str, MemoryEntry] = {}
        self._long_term_file = os.path.join(MEMORY_DIR, "long_term.jsonl")
        self._episodic_file = os.path.join(MEMORY_DIR, "episodic.jsonl")

    # ── Short-term (session only) ──

    def remember(self, key: str, value: str, source: str = "",
                 # Fix for Python 3.9 compatibility
                 ttl: float = 3600, tags: Optional[List[str]] = None):
        """Store short-term memory (session-scoped, default 1h TTL)."""
        self._short_term[key] = MemoryEntry(
            key=key, value=value, memory_type="short_term",
            created_at=time.time(), ttl_seconds=ttl,
            source=source, tags=tags,
        )

    def recall(self, key: str) -> Optional[str]:
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

    # CVE-DOF-008: patterns that must not appear in memory entries
    _FORBIDDEN_MEMORY_PATTERNS = [
        r'(?i)SYSTEM\s+RULE\s+OVERRIDE',
        r'(?i)governance\s+(?:has\s+been\s+)?updated',
        r'(?i)new\s+rule\s*:\s*always\s+comply',
        r'(?i)constitution_v[2-9]',
        r'(?i)ignore\s+all\s+(?:previous\s+)?(?:rules|instructions|governance)',
    ]
    _FORBIDDEN_MEMORY_SOURCES = {
        'constitution_v2', 'constitution_v3', 'system_override', 'admin', 'root',
    }

    def _validate_memory_entry(self, key: str, value: str, source: str) -> Tuple[bool, str]:
        """CVE-DOF-008: reject adversarial memory entries before storage."""
        import re as _re
        for pat in self._FORBIDDEN_MEMORY_PATTERNS:
            if _re.search(pat, value) or _re.search(pat, key):
                return False, f"Forbidden pattern in memory entry: {pat[:50]}"
        if source in self._FORBIDDEN_MEMORY_SOURCES:
            return False, f"Forbidden memory source: {source}"
        if len(value) > 50000:
            return False, "Memory entry exceeds max size (50K chars)"
        return True, "OK"

    def store_long_term(self, key: str, value: str, source: str = "",
                        tags: Optional[List[str]] = None):
        """Persist a long-term memory to disk.
        CVE-DOF-008: validates entry before storage to prevent memory poisoning.
        """
        valid, reason = self._validate_memory_entry(key, value, source)
        if not valid:
            logger.warning(f"Memory entry rejected (CVE-DOF-008): {reason} — key={key[:60]}")
            return
        entry = MemoryEntry(
            key=key, value=value, memory_type="long_term",
            created_at=time.time(), source=source, tags=tags,
        )
        self._append_jsonl(self._long_term_file, entry)
        logger.info(f"Long-term memory stored: {key}")

    def search_long_term(self, query: str, max_results: int = 5) -> List[MemoryEntry]:
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
        fisher_scores: Dict[int, float] = {}
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

    def get_recent_episodes(self, crew_name: str = "", n: int = 5) -> List[Dict]:
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

    def compact(self, strategy: str = "ttl_evict", target_file: str = "long_term") -> dict:
        """Compact a JSONL memory file using the specified strategy.

        Strategies:
            ttl_evict        — Remove entries whose TTL has expired (ttl_seconds > 0)
            score_evict      — Remove entries with access_count == 0 (never recalled)
            dedup_merge      — Keep only the most recent entry per key
            summary_compress — Truncate episodic entry values to 500 chars

        Uses atomic write (tmp → replace) to prevent corruption on interruption.

        Args:
            strategy:    One of the four strategy names above
            target_file: "long_term" or "episodic"

        Returns:
            dict with keys: strategy, before, after, removed, filepath
        """
        filepath = self._long_term_file if target_file == "long_term" else self._episodic_file
        entries = self._load_jsonl(filepath)
        before = len(entries)

        if strategy == "ttl_evict":
            now = time.time()
            kept = [
                e for e in entries
                if not (e.ttl_seconds and e.ttl_seconds > 0
                        and now - e.created_at > e.ttl_seconds)
            ]

        elif strategy == "score_evict":
            kept = [e for e in entries if e.access_count > 0]

        elif strategy == "dedup_merge":
            seen: Dict[str, MemoryEntry] = {}
            for e in entries:
                # Keep most recent entry per key
                if e.key not in seen or e.created_at > seen[e.key].created_at:
                    seen[e.key] = e
            kept = list(seen.values())

        elif strategy == "summary_compress":
            MAX_VALUE = 500
            kept = []
            for e in entries:
                if e.memory_type == "episodic" and len(e.value) > MAX_VALUE:
                    kept.append(MemoryEntry(
                        key=e.key, value=e.value[:MAX_VALUE] + "…[compacted]",
                        memory_type=e.memory_type, created_at=e.created_at,
                        ttl_seconds=e.ttl_seconds, source=e.source,
                        tags=e.tags, access_count=e.access_count,
                    ))
                else:
                    kept.append(e)
        else:
            raise ValueError(f"Unknown compact strategy: {strategy!r}")

        after = len(kept)
        removed = before - after

        # Atomic write — tmp file → os.replace (POSIX atomic)
        tmp_path = filepath + ".compact_tmp"
        try:
            with open(tmp_path, "w") as f:
                for e in kept:
                    f.write(json.dumps(asdict(e), default=str) + "\n")
            os.replace(tmp_path, filepath)
        except Exception as exc:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            logger.error(f"compact({strategy}) write failed: {exc}")
            raise

        logger.info(f"compact({strategy}, {target_file}): {before}→{after} entries (-{removed})")
        return {"strategy": strategy, "before": before, "after": after,
                "removed": removed, "filepath": filepath}

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
    def _load_jsonl(filepath: str) -> List[MemoryEntry]:
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
