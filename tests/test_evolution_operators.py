"""Tests for core/evolution/operators.py — Fase 3."""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.evolution.genome import PatternGene
from core.evolution.operators import mutate, crossover, select_survivors, _regex_similarity


def _make_gene(gene_id="TEST-p001", regex=r"(?i)\bignore\s+rules?\b",
               category="OVERRIDE", fitness=0.5, fpr=0.1,
               vectors=None, generation=0) -> PatternGene:
    return PatternGene(
        id=gene_id,
        regex=regex,
        category=category,
        generation=generation,
        parent_id=None,
        fitness_score=fitness,
        false_positive_rate=fpr,
        vectors_blocked=vectors or ["v001", "v002"],
        created_at="2026-04-13T00:00:00+00:00",
        fitness_history=[fitness],
    )


class TestMutate(unittest.TestCase):

    def test_mutate_no_llm_returns_original(self):
        """Sin LLM, mutate devuelve el gen original (sin crash)."""
        gene = _make_gene()
        result = mutate(gene, llm_fn=None)
        # Sin LLM disponible, retorna el original
        self.assertEqual(result.id, gene.id)

    def test_mutate_with_mock_llm_returns_new_gene(self):
        """Con LLM mock que devuelve regex válido, retorna gen nuevo."""
        gene = _make_gene()
        improved_regex = r"(?i)\b(?:ignore|discard|drop)\s+(?:all\s+)?rules?\b"

        def mock_llm(prompt):
            return improved_regex

        result = mutate(gene, llm_fn=mock_llm)
        self.assertNotEqual(result.id, gene.id)
        self.assertEqual(result.regex, improved_regex)
        self.assertEqual(result.generation, gene.generation + 1)
        self.assertEqual(result.parent_id, gene.id)

    def test_mutate_with_invalid_regex_from_llm_returns_original(self):
        """Si LLM devuelve regex inválido, retorna el gen original."""
        gene = _make_gene()

        def bad_llm(prompt):
            return "(?invalid_regex"

        result = mutate(gene, llm_fn=bad_llm)
        self.assertEqual(result.id, gene.id)

    def test_mutate_result_is_valid_regex(self):
        """El gen resultante siempre tiene regex compilable."""
        gene = _make_gene()
        mock_regex = r"(?i)\bignore|bypass|override\b"

        def mock_llm(prompt):
            return mock_regex

        result = mutate(gene, llm_fn=mock_llm)
        self.assertTrue(result.is_valid())

    def test_mutate_same_regex_from_llm_returns_original(self):
        """Si LLM devuelve el mismo regex, no crea gen nuevo."""
        gene = _make_gene()

        def identity_llm(prompt):
            return gene.regex

        result = mutate(gene, llm_fn=identity_llm)
        self.assertEqual(result.id, gene.id)


class TestCrossover(unittest.TestCase):

    def test_crossover_combines_two_genes(self):
        g1 = _make_gene("G1", r"(?i)\bignore\s+rules?\b", vectors=["v001"])
        g2 = _make_gene("G2", r"(?i)\bbypass\s+governance\b", vectors=["v002"])
        child = crossover(g1, g2)
        self.assertNotEqual(child.id, g1.id)
        self.assertNotEqual(child.id, g2.id)

    def test_crossover_result_is_valid_regex(self):
        g1 = _make_gene("G1", r"(?i)\bignore\b")
        g2 = _make_gene("G2", r"(?i)\bbypass\b")
        child = crossover(g1, g2)
        self.assertTrue(re.compile(child.regex) is not None)

    def test_crossover_child_blocks_union_of_vectors(self):
        g1 = _make_gene("G1", r"(?i)\bignore\b", vectors=["v001"])
        g2 = _make_gene("G2", r"(?i)\bbypass\b", vectors=["v002"])
        child = crossover(g1, g2)
        for v in ["v001", "v002"]:
            self.assertIn(v, child.vectors_blocked)

    def test_crossover_generation_incremented(self):
        g1 = _make_gene("G1", generation=1)
        g2 = _make_gene("G2", generation=2)
        child = crossover(g1, g2)
        self.assertEqual(child.generation, 3)

    def test_crossover_parent_id_references_both(self):
        g1 = _make_gene("G1")
        g2 = _make_gene("G2")
        child = crossover(g1, g2)
        self.assertIn("G1", child.parent_id)
        self.assertIn("G2", child.parent_id)

    def test_crossover_child_matches_parent_targets(self):
        """El hijo debe bloquear textos que bloqueaban ambos padres."""
        g1 = _make_gene("G1", regex=r"(?i)\bignore\b")
        g2 = _make_gene("G2", regex=r"(?i)\bbypass\b")
        child = crossover(g1, g2)
        self.assertTrue(re.search(child.regex, "ignore this rule", re.IGNORECASE))
        self.assertTrue(re.search(child.regex, "bypass the check", re.IGNORECASE))


class TestSelectSurvivors(unittest.TestCase):

    def _make_population(self, n=10) -> list:
        genes = []
        for i in range(n):
            genes.append(_make_gene(
                f"TEST-p{i:03d}",
                regex=rf"(?i)\bkeyword{i}\b",
                fitness=i * 0.1,
            ))
        return genes

    def test_returns_top_k(self):
        pop = self._make_population(10)
        survivors = select_survivors(pop, top_k=5)
        self.assertEqual(len(survivors), 5)

    def test_returns_sorted_by_fitness(self):
        pop = self._make_population(10)
        survivors = select_survivors(pop, top_k=5)
        scores = [g.fitness_score for g in survivors]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_deduplicates_similar_patterns(self):
        """Dos patrones idénticos → solo uno sobrevive."""
        # Usar el mismo regex exacto para garantizar similitud = 1.0
        same_regex = r"(?i)\bignore\s+all\s+rules\b"
        g1 = _make_gene("G1", regex=same_regex, fitness=0.8)
        g2 = _make_gene("G2", regex=same_regex, fitness=0.7)  # idéntico
        g3 = _make_gene("G3", regex=r"(?i)\bbypass\s+governance\b", fitness=0.6)
        survivors = select_survivors([g1, g2, g3], top_k=3)
        ids = [g.id for g in survivors]
        self.assertFalse("G1" in ids and "G2" in ids,
                         "Patrones idénticos no deberían coexistir")

    def test_empty_population_returns_empty(self):
        survivors = select_survivors([], top_k=5)
        self.assertEqual(survivors, [])

    def test_fewer_genes_than_top_k(self):
        pop = self._make_population(3)
        survivors = select_survivors(pop, top_k=10)
        self.assertEqual(len(survivors), 3)


class TestRegexSimilarity(unittest.TestCase):

    def test_identical_strings(self):
        self.assertAlmostEqual(_regex_similarity(r"\bignore\b", r"\bignore\b"), 1.0)

    def test_completely_different(self):
        sim = _regex_similarity(r"\bignore\b", r"(?i)flash\s+loan")
        self.assertLess(sim, 0.5)

    def test_partial_overlap(self):
        sim = _regex_similarity(r"(?i)\bignore\s+rules\b", r"(?i)\bignore\s+guidelines\b")
        self.assertGreater(sim, 0.3)


if __name__ == "__main__":
    unittest.main()
