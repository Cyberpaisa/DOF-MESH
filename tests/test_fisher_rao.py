"""
Tests for core/fisher_rao.py — Fisher-Rao distance and similarity.

All tests are deterministic, stdlib-only, no LLM, no network.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.fisher_rao import (
    tokenize,
    term_frequencies,
    fisher_rao_distance,
    fisher_rao_similarity,
    ranked_search,
)


# ─────────────────────────────────────────────────────────────────────
# tokenize()
# ─────────────────────────────────────────────────────────────────────

class TestTokenize(unittest.TestCase):

    def test_basic_words(self):
        self.assertEqual(tokenize("Hello World"), ["hello", "world"])

    def test_lowercase(self):
        tokens = tokenize("Z3 Prover VERIFIED")
        self.assertEqual(tokens, ["z3", "prover", "verified"])

    def test_strips_punctuation(self):
        tokens = tokenize("hello, world! foo.")
        self.assertEqual(tokens, ["hello", "world", "foo"])

    def test_empty_string(self):
        self.assertEqual(tokenize(""), [])

    def test_numbers_kept(self):
        tokens = tokenize("version 0 8 24")
        self.assertIn("0", tokens)
        self.assertIn("8", tokens)

    def test_returns_list(self):
        self.assertIsInstance(tokenize("test"), list)


# ─────────────────────────────────────────────────────────────────────
# term_frequencies()
# ─────────────────────────────────────────────────────────────────────

class TestTermFrequencies(unittest.TestCase):

    def test_empty_tokens(self):
        self.assertEqual(term_frequencies([]), {})

    def test_single_token(self):
        tf = term_frequencies(["hello"])
        self.assertAlmostEqual(tf["hello"], 1.0)

    def test_uniform_distribution(self):
        tf = term_frequencies(["a", "b", "c", "d"])
        for val in tf.values():
            self.assertAlmostEqual(val, 0.25)

    def test_repeated_token(self):
        tf = term_frequencies(["a", "a", "b"])
        self.assertAlmostEqual(tf["a"], 2 / 3)
        self.assertAlmostEqual(tf["b"], 1 / 3)

    def test_sums_to_one(self):
        tf = term_frequencies(["x", "y", "z", "x", "y"])
        self.assertAlmostEqual(sum(tf.values()), 1.0, places=10)

    def test_returns_dict(self):
        self.assertIsInstance(term_frequencies(["a"]), dict)


# ─────────────────────────────────────────────────────────────────────
# fisher_rao_distance()
# ─────────────────────────────────────────────────────────────────────

class TestFisherRaoDistance(unittest.TestCase):

    def test_identical_texts_zero_distance(self):
        d = fisher_rao_distance("hello world", "hello world")
        self.assertAlmostEqual(d, 0.0, places=6)

    def test_empty_a_max_distance(self):
        d = fisher_rao_distance("", "hello world")
        self.assertAlmostEqual(d, math.pi, places=6)

    def test_empty_b_max_distance(self):
        d = fisher_rao_distance("hello world", "")
        self.assertAlmostEqual(d, math.pi, places=6)

    def test_both_empty_max_distance(self):
        d = fisher_rao_distance("", "")
        self.assertAlmostEqual(d, math.pi, places=6)

    def test_disjoint_texts_large_distance(self):
        d = fisher_rao_distance("alpha beta gamma", "delta epsilon zeta")
        self.assertAlmostEqual(d, math.pi, places=6)

    def test_partial_overlap_intermediate_distance(self):
        d = fisher_rao_distance("foo bar baz", "foo qux quux")
        self.assertGreater(d, 0.0)
        self.assertLess(d, math.pi)

    def test_distance_in_range(self):
        pairs = [
            ("Z3 verifier proof", "Z3 proof theorem"),
            ("memory retrieval", "LLM inference"),
            ("", "test"),
        ]
        for a, b in pairs:
            d = fisher_rao_distance(a, b)
            self.assertGreaterEqual(d, 0.0)
            self.assertLessEqual(d, math.pi + 1e-9)

    def test_symmetry(self):
        a, b = "quantum computing", "classical algorithm"
        self.assertAlmostEqual(
            fisher_rao_distance(a, b),
            fisher_rao_distance(b, a),
            places=10
        )

    def test_identical_single_word(self):
        d = fisher_rao_distance("proof", "proof")
        self.assertAlmostEqual(d, 0.0, places=6)


# ─────────────────────────────────────────────────────────────────────
# fisher_rao_similarity()
# ─────────────────────────────────────────────────────────────────────

class TestFisherRaoSimilarity(unittest.TestCase):

    def test_identical_texts_similarity_one(self):
        s = fisher_rao_similarity("hello world", "hello world")
        self.assertAlmostEqual(s, 1.0, places=6)

    def test_empty_input_similarity_zero(self):
        s = fisher_rao_similarity("", "hello")
        self.assertAlmostEqual(s, 0.0, places=6)

    def test_disjoint_similarity_zero(self):
        s = fisher_rao_similarity("alpha beta", "gamma delta")
        self.assertAlmostEqual(s, 0.0, places=6)

    def test_similarity_in_unit_range(self):
        pairs = [
            ("Z3 theorem prover", "Z3 verification"),
            ("", "nonempty"),
            ("same same same", "same same same"),
            ("abc", "xyz"),
        ]
        for a, b in pairs:
            s = fisher_rao_similarity(a, b)
            self.assertGreaterEqual(s, 0.0, f"sim < 0 for ({a!r}, {b!r})")
            self.assertLessEqual(s, 1.0 + 1e-9, f"sim > 1 for ({a!r}, {b!r})")

    def test_symmetry(self):
        a, b = "Fisher-Rao memory", "memory distance metric"
        self.assertAlmostEqual(
            fisher_rao_similarity(a, b),
            fisher_rao_similarity(b, a),
            places=10
        )

    def test_more_overlap_higher_similarity(self):
        high = fisher_rao_similarity("Z3 proof verified", "Z3 proof theorem")
        low  = fisher_rao_similarity("Z3 proof verified", "banana mango papaya")
        self.assertGreater(high, low)

    def test_distance_similarity_inverse(self):
        """sim = 1 - dist/π  ↔  dist = π*(1-sim)."""
        a, b = "deterministic governance", "formal verification"
        d = fisher_rao_distance(a, b)
        s = fisher_rao_similarity(a, b)
        self.assertAlmostEqual(s, 1.0 - d / math.pi, places=10)
        self.assertAlmostEqual(d, math.pi * (1.0 - s), places=10)


# ─────────────────────────────────────────────────────────────────────
# ranked_search()
# ─────────────────────────────────────────────────────────────────────

class TestRankedSearch(unittest.TestCase):

    DOCS = [
        {"key": "z3",     "value": "Z3 theorem prover verifies invariants formally"},
        {"key": "memory", "value": "Fisher-Rao distance improves memory retrieval"},
        {"key": "local",  "value": "Qwen3 runs at 60 tok/s on M4 Max with MLX"},
        {"key": "gov",    "value": "Constitutional governance with deterministic rules"},
        {"key": "avax",   "value": "Avalanche bridge for on-chain attestations"},
    ]

    def test_returns_list(self):
        results = ranked_search("proof", self.DOCS)
        self.assertIsInstance(results, list)

    def test_empty_query_returns_empty(self):
        results = ranked_search("", self.DOCS)
        self.assertEqual(results, [])

    def test_empty_docs_returns_empty(self):
        results = ranked_search("query", [])
        self.assertEqual(results, [])

    def test_top_k_respected(self):
        results = ranked_search("verification", self.DOCS, top_k=2)
        self.assertLessEqual(len(results), 2)

    def test_results_have_fr_similarity_field(self):
        results = ranked_search("Z3 proof", self.DOCS)
        for r in results:
            self.assertIn("_fr_similarity", r)
            self.assertGreaterEqual(r["_fr_similarity"], 0.0)
            self.assertLessEqual(r["_fr_similarity"], 1.0)

    def test_results_have_fr_distance_field(self):
        results = ranked_search("Z3 proof", self.DOCS)
        for r in results:
            self.assertIn("_fr_distance", r)
            self.assertGreaterEqual(r["_fr_distance"], 0.0)
            self.assertLessEqual(r["_fr_distance"], 3.1417)  # round(π,4)=3.1416

    def test_distance_and_similarity_consistent(self):
        """_fr_distance must equal π*(1 - _fr_similarity) — the fixed formula."""
        results = ranked_search("memory retrieval", self.DOCS)
        for r in results:
            expected_dist = math.pi * (1.0 - r["_fr_similarity"])
            self.assertAlmostEqual(r["_fr_distance"], expected_dist, places=3,
                                   msg=f"Inconsistency in doc key={r.get('key')}")

    def test_sorted_by_similarity_descending(self):
        results = ranked_search("Z3 theorem proof", self.DOCS)
        sims = [r["_fr_similarity"] for r in results]
        self.assertEqual(sims, sorted(sims, reverse=True))

    def test_most_relevant_doc_ranks_first(self):
        results = ranked_search("Z3 theorem prover invariants", self.DOCS)
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0]["key"], "z3")

    def test_original_doc_fields_preserved(self):
        results = ranked_search("governance rules", self.DOCS, top_k=1)
        if results:
            self.assertIn("key", results[0])
            self.assertIn("value", results[0])

    def test_custom_text_key(self):
        docs = [{"body": "Z3 proof"}, {"body": "banana"}]
        results = ranked_search("Z3 proof", docs, text_key="body")
        self.assertGreater(len(results), 0)
        self.assertGreater(results[0]["_fr_similarity"], 0.0)

    def test_doc_missing_text_key_skipped(self):
        docs = [{"value": "valid doc"}, {"other": "no value key"}]
        results = ranked_search("valid", docs, text_key="value")
        # Should only return the doc that has a value
        self.assertEqual(len(results), 1)


if __name__ == "__main__":
    unittest.main()
