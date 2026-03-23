"""
Tests for core/a_mem.py — A-Mem Zettelkasten Knowledge Graph.

All tests are deterministic, no LLM calls, use a temp directory.
"""

import math
import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.a_mem import AMem, MemoryNode, MemoryEdge, SearchResult, _fisher_rao_similarity


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────

def make_mem() -> tuple[AMem, str]:
    """Return (AMem instance, tmpdir path) — caller must clean up."""
    d = tempfile.mkdtemp()
    return AMem(d), d


# ─────────────────────────────────────────────────────────────────────
# Fisher-Rao similarity
# ─────────────────────────────────────────────────────────────────────

class TestFisherRaoSimilarity(unittest.TestCase):

    def test_identical_texts(self):
        s = _fisher_rao_similarity("hello world", "hello world")
        self.assertAlmostEqual(s, 1.0, places=2)

    def test_empty_inputs(self):
        self.assertEqual(_fisher_rao_similarity("", "hello"), 0.0)
        self.assertEqual(_fisher_rao_similarity("hello", ""), 0.0)

    def test_disjoint_texts(self):
        s = _fisher_rao_similarity("apple orange", "quantum neutron")
        self.assertLess(s, 0.2)

    def test_partial_overlap(self):
        s_high = _fisher_rao_similarity("Z3 verifier proof", "Z3 proof theorem")
        s_low = _fisher_rao_similarity("Z3 verifier proof", "banana mango")
        self.assertGreater(s_high, s_low)

    def test_result_in_unit_range(self):
        for a, b in [("foo", "bar"), ("x y z", "x"), ("", "")]:
            s = _fisher_rao_similarity(a, b)
            self.assertGreaterEqual(s, 0.0)
            self.assertLessEqual(s, 1.0)


# ─────────────────────────────────────────────────────────────────────
# MemoryNode basics
# ─────────────────────────────────────────────────────────────────────

class TestMemoryNode(unittest.TestCase):

    def test_id_auto_generated(self):
        n = MemoryNode(id="", content="test content", memory_type="semantic")
        self.assertTrue(len(n.id) == 12)

    def test_explicit_id_preserved(self):
        n = MemoryNode(id="myid", content="x", memory_type="episodic")
        self.assertEqual(n.id, "myid")

    def test_defaults(self):
        n = MemoryNode(id="", content="x", memory_type="semantic")
        self.assertEqual(n.tags, [])
        self.assertEqual(n.access_count, 0)
        self.assertAlmostEqual(n.importance, 0.5)


# ─────────────────────────────────────────────────────────────────────
# AMem.add()
# ─────────────────────────────────────────────────────────────────────

class TestAMemAdd(unittest.TestCase):

    def setUp(self):
        self.mem, self.tmpdir = make_mem()

    def test_add_returns_node(self):
        n = self.mem.add("Fisher-Rao distance test", memory_type="semantic")
        self.assertIsInstance(n, MemoryNode)
        self.assertTrue(n.id)

    def test_node_stored_in_memory(self):
        n = self.mem.add("stored node", memory_type="episodic")
        self.assertIn(n.id, self.mem._nodes)

    def test_custom_fields(self):
        n = self.mem.add("important fact", tags=["z3", "proof"],
                         source="test", importance=0.9)
        self.assertEqual(n.tags, ["z3", "proof"])
        self.assertEqual(n.source, "test")
        self.assertAlmostEqual(n.importance, 0.9)

    def test_node_persisted_to_disk(self):
        self.mem.add("persisted", memory_type="semantic")
        self.assertTrue(os.path.exists(self.mem._nodes_file))

    def test_multiple_adds(self):
        for i in range(5):
            self.mem.add(f"node {i}")
        self.assertEqual(len(self.mem._nodes), 5)


# ─────────────────────────────────────────────────────────────────────
# AMem.link()
# ─────────────────────────────────────────────────────────────────────

class TestAMemLink(unittest.TestCase):

    def setUp(self):
        self.mem, _ = make_mem()
        self.n1 = self.mem.add("node A", memory_type="semantic")
        self.n2 = self.mem.add("node B", memory_type="semantic")

    def test_link_creates_edge(self):
        edge = self.mem.link(self.n1.id, self.n2.id, "supports")
        self.assertIsInstance(edge, MemoryEdge)
        self.assertEqual(edge.relation, "supports")

    def test_link_bidirectional_adjacency(self):
        self.mem.link(self.n1.id, self.n2.id, "related")
        self.assertIn(self.n2.id, self.mem._adjacency.get(self.n1.id, []))
        self.assertIn(self.n1.id, self.mem._adjacency.get(self.n2.id, []))

    def test_link_unknown_node_returns_none(self):
        result = self.mem.link(self.n1.id, "nonexistent", "related")
        self.assertIsNone(result)

    def test_link_weight(self):
        edge = self.mem.link(self.n1.id, self.n2.id, "contradicts", weight=0.75)
        self.assertAlmostEqual(edge.weight, 0.75)


# ─────────────────────────────────────────────────────────────────────
# AMem.search()
# ─────────────────────────────────────────────────────────────────────

class TestAMemSearch(unittest.TestCase):

    def setUp(self):
        self.mem, _ = make_mem()
        self.mem.add("Z3 theorem prover verifies invariants",
                     tags=["z3", "proof"], importance=0.9)
        self.mem.add("Fisher-Rao distance improves memory retrieval",
                     tags=["memory", "fisher-rao"], importance=0.8)
        self.mem.add("Qwen3 runs at 60 tok/s on M4 Max",
                     tags=["local", "inference"], importance=0.7)

    def test_search_returns_results(self):
        results = self.mem.search("proof verification")
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)

    def test_search_result_type(self):
        results = self.mem.search("memory")
        for r in results:
            self.assertIsInstance(r, SearchResult)
            self.assertIsInstance(r.node, MemoryNode)
            self.assertGreaterEqual(r.similarity, 0.0)

    def test_search_empty_graph(self):
        mem, _ = make_mem()
        results = mem.search("anything")
        self.assertEqual(results, [])

    def test_top_k_respected(self):
        results = self.mem.search("test", top_k=2)
        self.assertLessEqual(len(results), 2)

    def test_relevant_result_ranks_higher(self):
        results = self.mem.search("Z3 proof theorem")
        top = results[0].node
        self.assertIn("Z3", top.content)

    def test_memory_type_filter(self):
        self.mem.add("episodic event", memory_type="episodic")
        results = self.mem.search("event", memory_type="episodic")
        for r in results:
            self.assertEqual(r.node.memory_type, "episodic")

    def test_access_count_incremented(self):
        results = self.mem.search("Z3")
        if results:
            node_id = results[0].node.id
            before = self.mem._nodes[node_id].access_count
            self.mem.search("Z3")
            after = self.mem._nodes[node_id].access_count
            self.assertGreater(after, before)


# ─────────────────────────────────────────────────────────────────────
# AMem.decay()  ← NEW method being tested
# ─────────────────────────────────────────────────────────────────────

class TestAMemDecay(unittest.TestCase):

    def setUp(self):
        self.mem, _ = make_mem()

    def test_decay_returns_int(self):
        self.mem.add("some fact", importance=0.8)
        result = self.mem.decay()
        self.assertIsInstance(result, int)

    def test_decay_reduces_importance_of_old_node(self):
        n = self.mem.add("old fact", importance=0.8)
        # Simulate node last accessed 100 hours ago
        self.mem._nodes[n.id].last_accessed = time.time() - (100 * 3600)
        original = self.mem._nodes[n.id].importance

        decayed_count = self.mem.decay(half_life_hours=72.0)

        self.assertGreaterEqual(decayed_count, 1)
        self.assertLess(self.mem._nodes[n.id].importance, original)

    def test_decay_respects_floor(self):
        n = self.mem.add("ancient node", importance=0.5)
        # Simulate node idle for 10 000 hours (importance would go to ~0)
        self.mem._nodes[n.id].last_accessed = time.time() - (10_000 * 3600)

        self.mem.decay(half_life_hours=72.0, floor=0.1)

        self.assertGreaterEqual(self.mem._nodes[n.id].importance, 0.1)

    def test_decay_skips_recent_nodes(self):
        n = self.mem.add("fresh node", importance=0.8)
        # last_accessed is now — should not be decayed
        original = self.mem._nodes[n.id].importance

        decayed_count = self.mem.decay()

        self.assertEqual(decayed_count, 0)
        self.assertAlmostEqual(self.mem._nodes[n.id].importance, original)

    def test_decay_half_life_semantics(self):
        n = self.mem.add("half-life test", importance=1.0)
        # Idle exactly one half-life
        half_life = 72.0
        self.mem._nodes[n.id].last_accessed = time.time() - (half_life * 3600)

        self.mem.decay(half_life_hours=half_life, floor=0.0)

        # importance should be ~0.5 (±5%)
        self.assertAlmostEqual(self.mem._nodes[n.id].importance, 0.5, delta=0.05)

    def test_decay_empty_graph(self):
        result = self.mem.decay()
        self.assertEqual(result, 0)


# ─────────────────────────────────────────────────────────────────────
# AMem.traverse()
# ─────────────────────────────────────────────────────────────────────

class TestAMemTraverse(unittest.TestCase):

    def setUp(self):
        self.mem, _ = make_mem()
        self.a = self.mem.add("node A", memory_type="semantic")
        self.b = self.mem.add("node B", memory_type="semantic")
        self.c = self.mem.add("node C", memory_type="semantic")
        # A → B → C chain (manual links, bypass auto-link threshold)
        self.mem._adjacency.setdefault(self.a.id, []).append(self.b.id)
        self.mem._adjacency.setdefault(self.b.id, []).append(self.a.id)
        self.mem._adjacency.setdefault(self.b.id, []).append(self.c.id)
        self.mem._adjacency.setdefault(self.c.id, []).append(self.b.id)

    def test_traverse_returns_start(self):
        results = self.mem.traverse(self.a.id, max_hops=0)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0].id, self.a.id)

    def test_traverse_unknown_start(self):
        results = self.mem.traverse("nonexistent")
        self.assertEqual(results, [])

    def test_traverse_reaches_neighbors(self):
        results = self.mem.traverse(self.a.id, max_hops=1)
        ids = [r[0].id for r in results]
        self.assertIn(self.b.id, ids)

    def test_traverse_hop_distance(self):
        results = self.mem.traverse(self.a.id, max_hops=2)
        distances = {r[0].id: r[1] for r in results}
        self.assertEqual(distances[self.a.id], 0)
        self.assertEqual(distances[self.b.id], 1)
        self.assertEqual(distances[self.c.id], 2)


# ─────────────────────────────────────────────────────────────────────
# AMem.stats() and get_contradictions()
# ─────────────────────────────────────────────────────────────────────

class TestAMemStats(unittest.TestCase):

    def setUp(self):
        self.mem, _ = make_mem()

    def test_stats_keys(self):
        s = self.mem.stats()
        for key in ("total_nodes", "total_edges", "types", "relations", "avg_connections"):
            self.assertIn(key, s)

    def test_stats_empty(self):
        s = self.mem.stats()
        self.assertEqual(s["total_nodes"], 0)
        self.assertEqual(s["total_edges"], 0)

    def test_stats_after_adds(self):
        self.mem.add("x", memory_type="semantic")
        self.mem.add("y", memory_type="episodic")
        s = self.mem.stats()
        self.assertEqual(s["total_nodes"], 2)
        self.assertEqual(s["types"]["semantic"], 1)
        self.assertEqual(s["types"]["episodic"], 1)

    def test_contradictions_detection(self):
        n1 = self.mem.add("fact A")
        n2 = self.mem.add("fact B")
        self.mem.link(n1.id, n2.id, "contradicts")
        contradictions = self.mem.get_contradictions()
        self.assertEqual(len(contradictions), 1)
        self.assertEqual(contradictions[0][2].relation, "contradicts")

    def test_no_contradictions_default(self):
        self.mem.add("fact X")
        self.assertEqual(self.mem.get_contradictions(), [])


# ─────────────────────────────────────────────────────────────────────
# Persistence: reload from JSONL
# ─────────────────────────────────────────────────────────────────────

class TestAMemPersistence(unittest.TestCase):

    def test_nodes_survive_reload(self):
        d = tempfile.mkdtemp()
        mem1 = AMem(d)
        n = mem1.add("persistent memory", memory_type="semantic", importance=0.77)
        node_id = n.id

        mem2 = AMem(d)  # fresh instance, same dir
        self.assertIn(node_id, mem2._nodes)
        self.assertAlmostEqual(mem2._nodes[node_id].importance, 0.77, places=2)

    def test_edges_survive_reload(self):
        d = tempfile.mkdtemp()
        mem1 = AMem(d)
        n1 = mem1.add("alpha")
        n2 = mem1.add("beta")
        mem1.link(n1.id, n2.id, "supports")

        mem2 = AMem(d)
        self.assertEqual(len(mem2._edges), 1)
        self.assertEqual(mem2._edges[0].relation, "supports")


if __name__ == "__main__":
    unittest.main()
