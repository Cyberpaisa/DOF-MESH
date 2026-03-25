"""
Tests for core.rag_engine — RAGEngine, RAGResult, get_rag_engine, index_directory.
Uses only stdlib: unittest + tempfile.
"""
import json
import os
import sys
import tempfile
import unittest

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.rag_engine import RAGEngine, RAGResult, get_rag_engine


def _fresh_engine() -> RAGEngine:
    """Return a RAGEngine with a clean in-memory index (bypasses singleton state)."""
    engine = RAGEngine()
    with engine._lock:
        engine._index.clear()
        engine._idf_cache.clear()
    return engine


class TestRAGEngineInstantiation(unittest.TestCase):
    """RAGEngine() creates an instance and respects singleton semantics."""

    def test_creates_instance(self):
        engine = RAGEngine()
        self.assertIsInstance(engine, RAGEngine)

    def test_singleton_same_object(self):
        e1 = RAGEngine()
        e2 = RAGEngine()
        self.assertIs(e1, e2)

    def test_get_rag_engine_returns_ragengine(self):
        result = get_rag_engine()
        self.assertIsInstance(result, RAGEngine)

    def test_get_rag_engine_is_singleton(self):
        e1 = get_rag_engine()
        e2 = get_rag_engine()
        self.assertIs(e1, e2)


class TestIndexFile(unittest.TestCase):
    """index_file() behaviour with various file types and edge cases."""

    def setUp(self):
        self.engine = _fresh_engine()

    def test_index_real_txt_file_returns_positive_int(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w",
                                        delete=False, encoding="utf-8") as fh:
            fh.write("deterministic observability framework " * 50)
            path = fh.name
        try:
            count = self.engine.index_file(path)
            self.assertIsInstance(count, int)
            self.assertGreater(count, 0)
        finally:
            os.unlink(path)

    def test_index_md_file_works(self):
        with tempfile.NamedTemporaryFile(suffix=".md", mode="w",
                                        delete=False, encoding="utf-8") as fh:
            fh.write("# DOF Architecture\n\nCore module map and data flow.\n" * 20)
            path = fh.name
        try:
            count = self.engine.index_file(path)
            self.assertGreater(count, 0)
        finally:
            os.unlink(path)

    def test_index_jsonl_file_works(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", mode="w",
                                        delete=False, encoding="utf-8") as fh:
            for i in range(30):
                fh.write(json.dumps({"level": "INFO", "msg": f"agent cycle {i} complete"}) + "\n")
            path = fh.name
        try:
            count = self.engine.index_file(path)
            self.assertGreater(count, 0)
        finally:
            os.unlink(path)

    def test_index_nonexistent_file_returns_zero(self):
        count = self.engine.index_file("/tmp/does_not_exist_xyzzy_12345.txt")
        self.assertEqual(count, 0)

    def test_index_nonexistent_file_does_not_raise(self):
        try:
            self.engine.index_file("/tmp/phantom_file_abc.txt")
        except Exception as exc:
            self.fail(f"index_file raised unexpectedly: {exc}")

    def test_index_py_file_increments_doc_count(self):
        stats_before = self.engine.get_stats()
        docs_before = stats_before["total_docs"]
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w",
                                        delete=False, encoding="utf-8") as fh:
            fh.write("def hello():\n    return 'world'\n" * 40)
            path = fh.name
        try:
            self.engine.index_file(path)
            stats_after = self.engine.get_stats()
            self.assertGreater(stats_after["total_docs"], docs_before)
        finally:
            os.unlink(path)


class TestIndexDirectory(unittest.TestCase):
    """index_directory() with a temporary directory tree."""

    def setUp(self):
        self.engine = _fresh_engine()

    def test_index_directory_returns_int(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = os.path.join(tmpdir, "notes.md")
            with open(fpath, "w", encoding="utf-8") as fh:
                fh.write("# Notes\nThis is a test document.\n" * 30)
            result = self.engine.index_directory(tmpdir)
            self.assertIsInstance(result, int)

    def test_index_directory_returns_positive_for_valid_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            for name in ("a.md", "b.txt", "c.py"):
                with open(os.path.join(tmpdir, name), "w", encoding="utf-8") as fh:
                    fh.write("governance deterministic framework " * 30)
            result = self.engine.index_directory(tmpdir)
            self.assertGreater(result, 0)

    def test_index_nonexistent_directory_returns_zero(self):
        result = self.engine.index_directory("/tmp/no_such_dir_xyz_99999")
        self.assertEqual(result, 0)


class TestSearch(unittest.TestCase):
    """search() return types, structure, and relevance behaviour."""

    def setUp(self):
        self.engine = _fresh_engine()

    def _index_content(self, content: str, suffix: str = ".txt") -> str:
        with tempfile.NamedTemporaryFile(suffix=suffix, mode="w",
                                        delete=False, encoding="utf-8") as fh:
            fh.write(content)
            return fh.name

    def test_search_returns_list(self):
        path = self._index_content("hello world testing " * 40)
        try:
            self.engine.index_file(path)
            results = self.engine.search("hello")
            self.assertIsInstance(results, list)
        finally:
            os.unlink(path)

    def test_search_returns_ragresult_objects(self):
        path = self._index_content("foo bar baz qux " * 40)
        try:
            self.engine.index_file(path)
            results = self.engine.search("foo bar")
            if results:
                self.assertIsInstance(results[0], RAGResult)
        finally:
            os.unlink(path)

    def test_search_empty_query_returns_list(self):
        results = self.engine.search("")
        self.assertIsInstance(results, list)

    def test_search_top_k_limits_results(self):
        path = self._index_content(
            "machine learning neural network deep learning " * 100
        )
        try:
            self.engine.index_file(path)
            results = self.engine.search("learning network", top_k=2)
            self.assertLessEqual(len(results), 2)
        finally:
            os.unlink(path)

    def test_search_finds_relevant_content(self):
        unique_term = "xqzdeterministicxqz"
        path = self._index_content(f"{unique_term} framework " * 20)
        try:
            self.engine.index_file(path)
            results = self.engine.search(unique_term)
            self.assertGreater(len(results), 0)
            found = any(unique_term in r.chunk for r in results)
            self.assertTrue(found, "Expected unique term in at least one result chunk")
        finally:
            os.unlink(path)

    def test_search_result_scores_positive(self):
        path = self._index_content("supervisory control deterministic " * 30)
        try:
            self.engine.index_file(path)
            results = self.engine.search("supervisory control")
            for r in results:
                self.assertGreater(r.score, 0.0)
        finally:
            os.unlink(path)

    def test_search_results_sorted_descending_score(self):
        path = self._index_content("alpha beta gamma delta " * 50)
        try:
            self.engine.index_file(path)
            results = self.engine.search("alpha beta gamma", top_k=5)
            scores = [r.score for r in results]
            self.assertEqual(scores, sorted(scores, reverse=True))
        finally:
            os.unlink(path)


class TestGetContext(unittest.TestCase):
    """get_context() returns strings, respects max_chars, surfaces content."""

    def setUp(self):
        self.engine = _fresh_engine()

    def test_get_context_returns_string(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w",
                                        delete=False, encoding="utf-8") as fh:
            fh.write("mesh governance engine " * 40)
            path = fh.name
        try:
            self.engine.index_file(path)
            ctx = self.engine.get_context("governance")
            self.assertIsInstance(ctx, str)
        finally:
            os.unlink(path)

    def test_get_context_contains_relevant_content(self):
        unique = "xyzrelevantcontentxyz"
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w",
                                        delete=False, encoding="utf-8") as fh:
            fh.write(f"{unique} extra text " * 20)
            path = fh.name
        try:
            self.engine.index_file(path)
            ctx = self.engine.get_context(unique)
            self.assertIn(unique, ctx)
        finally:
            os.unlink(path)

    def test_get_context_respects_max_chars(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w",
                                        delete=False, encoding="utf-8") as fh:
            fh.write("agent framework deterministic score " * 200)
            path = fh.name
        try:
            self.engine.index_file(path)
            ctx = self.engine.get_context("agent framework", max_chars=500)
            self.assertLessEqual(len(ctx), 500)
        finally:
            os.unlink(path)

    def test_get_context_empty_index_returns_string(self):
        ctx = self.engine.get_context("anything")
        self.assertIsInstance(ctx, str)


class TestGetStats(unittest.TestCase):
    """get_stats() structure and correctness."""

    def setUp(self):
        self.engine = _fresh_engine()

    def test_get_stats_returns_dict(self):
        stats = self.engine.get_stats()
        self.assertIsInstance(stats, dict)

    def test_get_stats_has_required_keys(self):
        stats = self.engine.get_stats()
        for key in ("total_docs", "total_chunks", "index_size_bytes", "last_indexed"):
            self.assertIn(key, stats, f"Missing key: {key}")

    def test_get_stats_total_docs_increases_after_index(self):
        stats_before = self.engine.get_stats()
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w",
                                        delete=False, encoding="utf-8") as fh:
            fh.write("stat increment test content " * 30)
            path = fh.name
        try:
            self.engine.index_file(path)
            stats_after = self.engine.get_stats()
            self.assertGreater(stats_after["total_docs"], stats_before["total_docs"])
        finally:
            os.unlink(path)

    def test_get_stats_total_chunks_non_negative(self):
        stats = self.engine.get_stats()
        self.assertGreaterEqual(stats["total_chunks"], 0)

    def test_get_stats_index_size_bytes_non_negative(self):
        stats = self.engine.get_stats()
        self.assertGreaterEqual(stats["index_size_bytes"], 0)


class TestRAGResult(unittest.TestCase):
    """RAGResult dataclass and to_dict() contract."""

    def _make_result(self) -> RAGResult:
        return RAGResult(
            doc_id="doc123#0",
            source_path="/tmp/test.txt",
            chunk="some chunk text here",
            score=0.75,
            doc_type="doc",
        )

    def test_to_dict_returns_dict(self):
        r = self._make_result()
        self.assertIsInstance(r.to_dict(), dict)

    def test_to_dict_has_required_keys(self):
        r = self._make_result()
        d = r.to_dict()
        for key in ("doc_id", "source_path", "chunk", "score", "doc_type"):
            self.assertIn(key, d, f"Missing key: {key}")

    def test_to_dict_values_match(self):
        r = self._make_result()
        d = r.to_dict()
        self.assertEqual(d["doc_id"], "doc123#0")
        self.assertEqual(d["source_path"], "/tmp/test.txt")
        self.assertEqual(d["chunk"], "some chunk text here")
        self.assertAlmostEqual(d["score"], 0.75)
        self.assertEqual(d["doc_type"], "doc")


class TestPrivateHelpers(unittest.TestCase):
    """_chunk_text() and _tokenize() internal contract."""

    def setUp(self):
        self.engine = _fresh_engine()

    def test_chunk_text_returns_list(self):
        chunks = self.engine._chunk_text("hello world " * 100)
        self.assertIsInstance(chunks, list)

    def test_chunk_text_returns_strings(self):
        chunks = self.engine._chunk_text("alpha beta gamma " * 80)
        for c in chunks:
            self.assertIsInstance(c, str)

    def test_chunk_text_respects_chunk_size(self):
        text = "x" * 2000
        chunks = self.engine._chunk_text(text, chunk_size=300, overlap=0)
        for c in chunks:
            self.assertLessEqual(len(c), 300)

    def test_chunk_text_empty_returns_empty_list(self):
        chunks = self.engine._chunk_text("")
        self.assertEqual(chunks, [])

    def test_tokenize_returns_list(self):
        tokens = self.engine._tokenize("The quick brown fox")
        self.assertIsInstance(tokens, list)

    def test_tokenize_removes_stopwords(self):
        tokens = self.engine._tokenize("the a an in on of to for and or is it")
        # All tokens are English stopwords; result should be empty (or very small)
        stopwords = {"the", "a", "an", "in", "on", "of", "to", "for", "and", "or", "is", "it"}
        for t in tokens:
            self.assertNotIn(t, stopwords)

    def test_tokenize_lowercases(self):
        tokens = self.engine._tokenize("DETERMINISTIC Observability Framework")
        for t in tokens:
            self.assertEqual(t, t.lower())


if __name__ == "__main__":
    unittest.main()
