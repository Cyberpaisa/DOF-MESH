"""
RAG Engine — Retrieval Augmented Generation for DOF Mesh.
Indexes logs/docs/code, retrieves relevant context for agent queries.
Zero external ML dependencies — TF-IDF keyword scoring.
"""
import os
import re
import json
import math
import time
import threading
import logging
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Union, Any, Tuple

logger = logging.getLogger("core.rag_engine")

_BASE_DIR = Path(__file__).parent.parent
_INDEX_DIR = _BASE_DIR / "logs" / "rag"
_INDEX_FILE = _INDEX_DIR / "index.json"

_STOPWORDS = {
    "the", "a", "an", "in", "on", "of", "to", "for", "and", "or", "is", "it",
    "with", "this", "that", "are", "was", "be", "at", "by", "from", "as",
    "but", "not", "we", "i", "you", "he", "she", "they",
    "de", "la", "el", "en", "que", "y", "a", "un", "una", "los", "las",
    "por", "para", "con", "se", "del", "al",
}

_EXTENSION_TO_TYPE = {
    ".jsonl": "log",
    ".json": "log",
    ".md": "doc",
    ".txt": "doc",
    ".py": "code",
    ".ts": "code",
    ".js": "code",
    ".tsx": "code",
    ".jsx": "code",
    ".toml": "code",
    ".yaml": "code",
    ".yml": "code",
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class RAGDocument:
    doc_id: str
    source_path: str
    content: str
    chunks: list
    indexed_at: float
    doc_type: str  # log | doc | code


@dataclass
class RAGResult:
    doc_id: str
    source_path: str
    chunk: str
    score: float
    doc_type: str

    def to_dict(self) -> dict:
        return {
            "doc_id": self.doc_id,
            "source_path": self.source_path,
            "chunk": self.chunk,
            "score": self.score,
            "doc_type": self.doc_type,
        }


# ---------------------------------------------------------------------------
# RAGEngine
# ---------------------------------------------------------------------------

class RAGEngine:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._index: Dict[str, RAGDocument] = {}
        self._lock = threading.Lock()
        self._idf_cache: Dict = {}

        # Ensure log directory exists
        _INDEX_DIR.mkdir(parents=True, exist_ok=True)

        if _INDEX_FILE.exists():
            try:
                self.load_index()
                logger.info("RAGEngine: loaded existing index (%d docs)", len(self._index))
            except Exception as exc:
                logger.warning("RAGEngine: failed to load index — %s", exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def index_file(self, path) -> int:
        """Read a file, split into chunks, store in index. Returns chunk count."""
        path = Path(path)
        if not path.is_file():
            logger.warning("index_file: not a file: %s", path)
            return 0

        ext = path.suffix.lower()
        doc_type = _EXTENSION_TO_TYPE.get(ext, "doc")

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            logger.warning("index_file: cannot read %s — %s", path, exc)
            return 0

        # For JSONL files, try to extract readable text from each line
        if ext == ".jsonl":
            content = _flatten_jsonl(content)

        chunks = self._chunk_text(content)
        doc_id = str(path.resolve())

        doc = RAGDocument(
            doc_id=doc_id,
            source_path=str(path),
            content=content,
            chunks=chunks,
            indexed_at=time.time(),
            doc_type=doc_type,
        )

        with self._lock:
            self._index[doc_id] = doc
            self._idf_cache.clear()  # invalidate IDF cache after indexing

        return len(chunks)

    def index_directory(self, directory, extensions=None) -> int:
        """Index all matching files in a directory tree. Returns total chunks."""
        directory = Path(directory)
        if not directory.is_dir():
            logger.warning("index_directory: not a directory: %s", directory)
            return 0

        if extensions is None:
            extensions = list(_EXTENSION_TO_TYPE.keys())

        # Normalise extensions to lowercase with leading dot
        extensions = [
            e if e.startswith(".") else f".{e}"
            for e in extensions
        ]

        total = 0
        for root, dirs, files in os.walk(directory):
            # Skip hidden dirs and __pycache__
            dirs[:] = [
                d for d in dirs
                if not d.startswith(".") and d != "__pycache__"
            ]
            for fname in files:
                fpath = Path(root) / fname
                if fpath.suffix.lower() in extensions:
                    count = self.index_file(fpath)
                    if count:
                        logger.debug("indexed %s (%d chunks)", fpath, count)
                        total += count

        logger.info("index_directory: %s — %d total chunks", directory, total)
        return total

    def search(self, query: str, top_k: int = 5) -> List:
        """TF-IDF search over all indexed chunks. Returns top_k RAGResult list."""
        query_terms = self._tokenize(query)
        if not query_terms:
            return []

        with self._lock:
            docs = dict(self._index)

        results = []

        for doc_id, doc in docs.items():
            for idx, chunk in enumerate(doc.chunks):
                score = self._tfidf_score(query_terms, chunk, docs)
                if score > 0:
                    results.append(
                        RAGResult(
                            doc_id=f"{doc_id}#{idx}",
                            source_path=doc.source_path,
                            chunk=chunk,
                            score=score,
                            doc_type=doc.doc_type,
                        )
                    )

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def get_context(self, query: str, max_chars: int = 3000) -> str:
        """Return concatenated context string suitable for LLM injection."""
        results = self.search(query, top_k=10)
        parts = []
        total = 0

        for r in results:
            header = f"[{r.doc_type.upper()} | {Path(r.source_path).name} | score={r.score:.4f}]"
            block = f"{header}\n{r.chunk}"
            if total + len(block) > max_chars:
                remaining = max_chars - total
                if remaining > len(header) + 20:
                    parts.append(block[:remaining])
                break
            parts.append(block)
            total += len(block)

        if not parts:
            return ""

        return "\n\n---\n\n".join(parts)

    def get_stats(self) -> dict:
        """Return index statistics."""
        with self._lock:
            docs = dict(self._index)

        total_chunks = sum(len(d.chunks) for d in docs.values())
        index_size = _INDEX_FILE.stat().st_size if _INDEX_FILE.exists() else 0
        last_indexed = (
            max((d.indexed_at for d in docs.values()), default=0.0)
        )

        return {
            "total_docs": len(docs),
            "total_chunks": total_chunks,
            "index_size_bytes": index_size,
            "last_indexed": last_indexed,
        }

    def save_index(self):
        """Persist index to _INDEX_FILE as JSON."""
        _INDEX_DIR.mkdir(parents=True, exist_ok=True)

        serialisable = {}
        with self._lock:
            for doc_id, doc in self._index.items():
                serialisable[doc_id] = {
                    "doc_id": doc.doc_id,
                    "source_path": doc.source_path,
                    # Do not store full content to keep index compact
                    "content": "",
                    "chunks": doc.chunks,
                    "indexed_at": doc.indexed_at,
                    "doc_type": doc.doc_type,
                }

        with open(_INDEX_FILE, "w", encoding="utf-8") as fh:
            json.dump(serialisable, fh, ensure_ascii=False, indent=2)

        logger.info("RAGEngine: index saved (%d docs)", len(serialisable))

    def load_index(self):
        """Load index from _INDEX_FILE."""
        with open(_INDEX_FILE, "r", encoding="utf-8") as fh:
            raw = json.load(fh)

        loaded = {}
        for doc_id, data in raw.items():
            loaded[doc_id] = RAGDocument(
                doc_id=data["doc_id"],
                source_path=data["source_path"],
                content=data.get("content", ""),
                chunks=data.get("chunks", []),
                indexed_at=data.get("indexed_at", 0.0),
                doc_type=data.get("doc_type", "doc"),
            )

        with self._lock:
            self._index = loaded
            self._idf_cache.clear()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> list:
        """Split text into overlapping chunks of ~chunk_size chars."""
        if not text:
            return []

        chunks = []
        start = 0
        length = len(text)

        while start < length:
            end = min(start + chunk_size, length)
            chunks.append(text[start:end])
            if end == length:
                break
            start = end - overlap

        return chunks

    def _tfidf_score(self, query_terms: List, chunk: str, docs: Dict = None) -> float:
        """Compute TF-IDF score for query_terms against a single chunk."""
        if not query_terms or not chunk:
            return 0.0

        chunk_tokens = self._tokenize(chunk)
        if not chunk_tokens:
            return 0.0

        chunk_len = len(chunk_tokens)
        score = 0.0

        # Build IDF from cached or current docs
        total_docs = len(self._idf_cache.get("__total__", [])) if self._idf_cache else 0

        for term in query_terms:
            # Term frequency in this chunk
            tf = chunk_tokens.count(term) / chunk_len

            if tf == 0:
                continue

            # IDF: use cache or compute on the fly
            if docs is not None and term not in self._idf_cache:
                n_docs_with_term = sum(
                    1 for doc in docs.values()
                    if any(term in self._tokenize(c) for c in doc.chunks)
                )
                total = len(docs)
                idf = math.log((total + 1) / (n_docs_with_term + 1)) + 1.0
                self._idf_cache[term] = idf
            else:
                idf = self._idf_cache.get(term, 1.0)

            score += tf * idf

        return score

    def _tokenize(self, text: str) -> List:
        """Lowercase, split on non-alphanumeric, remove stopwords."""
        tokens = re.split(r"[^a-z0-9]+", text.lower())
        return [t for t in tokens if t and t not in _STOPWORDS and len(t) > 1]


# ---------------------------------------------------------------------------
# Private helpers (module level)
# ---------------------------------------------------------------------------

def _flatten_jsonl(content: str) -> str:
    """Extract string values from JSONL lines for better TF-IDF coverage."""
    lines = []
    for raw_line in content.splitlines():
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            obj = json.loads(raw_line)
            lines.append(_extract_strings(obj))
        except json.JSONDecodeError:
            lines.append(raw_line)
    return "\n".join(lines)


def _extract_strings(obj, depth: int = 0) -> str:
    """Recursively extract string values from a JSON object."""
    if depth > 5:
        return ""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        return " ".join(
            _extract_strings(v, depth + 1) for v in obj.values()
        )
    if isinstance(obj, list):
        return " ".join(_extract_strings(item, depth + 1) for item in obj)
    return str(obj)


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------

def get_rag_engine() -> RAGEngine:
    return RAGEngine()
