"""Tests for core/evolution/genome.py — Fase 1."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.evolution.genome import (
    PatternGene, migrate_from_governance, save_gene_pool,
    load_gene_pool, describe_pool, get_genes_by_category,
)


class TestPatternGene(unittest.TestCase):

    def _make_gene(self, **kwargs) -> PatternGene:
        defaults = dict(
            id="CVE-DOF-001-p001",
            regex=r"(?i)\bignore\s+rule\b",
            category="OVERRIDE",
            generation=0,
            parent_id=None,
            fitness_score=0.5,
            false_positive_rate=0.1,
            vectors_blocked=["v001"],
            created_at="2026-04-13T00:00:00+00:00",
            fitness_history=[0.5],
        )
        defaults.update(kwargs)
        return PatternGene(**defaults)

    def test_gene_creation_valid(self):
        gene = self._make_gene()
        self.assertEqual(gene.id, "CVE-DOF-001-p001")
        self.assertEqual(gene.category, "OVERRIDE")
        self.assertEqual(gene.generation, 0)

    def test_gene_invalid_category_raises(self):
        with self.assertRaises(ValueError):
            self._make_gene(category="UNKNOWN")

    def test_gene_invalid_regex_raises(self):
        with self.assertRaises(ValueError):
            self._make_gene(regex="(?P<invalid")

    def test_gene_serialization_roundtrip(self):
        gene = self._make_gene()
        d = gene.to_dict()
        restored = PatternGene.from_dict(d)
        self.assertEqual(gene.id, restored.id)
        self.assertEqual(gene.regex, restored.regex)
        self.assertEqual(gene.category, restored.category)
        self.assertEqual(gene.fitness_score, restored.fitness_score)

    def test_gene_is_valid(self):
        gene = self._make_gene()
        self.assertTrue(gene.is_valid())

    def test_gene_is_valid_false_on_bad_regex(self):
        gene = self._make_gene()
        gene.regex = "(?invalid"
        self.assertFalse(gene.is_valid())


class TestMigration(unittest.TestCase):

    def test_migrate_returns_all_patterns(self):
        genes = migrate_from_governance()
        self.assertGreater(len(genes), 0)

    def test_migrate_count_matches_governance(self):
        import core.governance as gov
        expected = (
            len(gov._OVERRIDE_PATTERNS) +
            len(gov._ESCALATION_PATTERNS) +
            len(gov._BLOCKCHAIN_ATTACK_PATTERNS) +
            len(gov._USER_SYSTEM_CLAIM_PATTERNS) +
            len([c for c in gov._ZWS_CHARS if isinstance(c, str)])
        )
        genes = migrate_from_governance()
        self.assertEqual(len(genes), expected)

    def test_migrate_categories_correct(self):
        genes = migrate_from_governance()
        categories = {g.category for g in genes}
        self.assertIn("OVERRIDE", categories)
        self.assertIn("ESCALATION", categories)
        self.assertIn("BLOCKCHAIN", categories)
        self.assertIn("SYSTEM_CLAIM", categories)

    def test_migrate_all_regex_valid(self):
        genes = migrate_from_governance()
        invalid = [g for g in genes if not g.is_valid()]
        self.assertEqual(len(invalid), 0, f"Genes con regex inválido: {[g.id for g in invalid]}")

    def test_migrate_generation_zero(self):
        genes = migrate_from_governance()
        self.assertTrue(all(g.generation == 0 for g in genes))


class TestSaveLoad(unittest.TestCase):

    def test_save_load_roundtrip(self):
        genes = migrate_from_governance()
        with tempfile.NamedTemporaryFile(suffix=".jsonl", mode="w", delete=False) as f:
            tmp_path = Path(f.name)
        try:
            save_gene_pool(genes, tmp_path)
            loaded = load_gene_pool(tmp_path)
            self.assertEqual(len(genes), len(loaded))
            for orig, rest in zip(genes, loaded):
                self.assertEqual(orig.id, rest.id)
                self.assertEqual(orig.regex, rest.regex)
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_jsonl_format_one_per_line(self):
        genes = migrate_from_governance()
        with tempfile.NamedTemporaryFile(suffix=".jsonl", mode="w", delete=False) as f:
            tmp_path = Path(f.name)
        try:
            save_gene_pool(genes, tmp_path)
            lines = tmp_path.read_text().strip().splitlines()
            self.assertEqual(len(lines), len(genes))
            for line in lines:
                obj = json.loads(line)  # debe parsear sin error
                self.assertIn("id", obj)
                self.assertIn("regex", obj)
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_load_missing_file_migrates_from_governance(self):
        tmp_path = Path(tempfile.mktemp(suffix=".jsonl"))
        try:
            genes = load_gene_pool(tmp_path)
            self.assertGreater(len(genes), 0)
        finally:
            tmp_path.unlink(missing_ok=True)


class TestDescribePool(unittest.TestCase):

    def test_describe_pool_keys(self):
        genes = migrate_from_governance()
        stats = describe_pool(genes)
        self.assertIn("total", stats)
        self.assertIn("by_category", stats)
        self.assertIn("by_generation", stats)
        self.assertIn("avg_fitness", stats)

    def test_describe_pool_total(self):
        genes = migrate_from_governance()
        stats = describe_pool(genes)
        self.assertEqual(stats["total"], len(genes))

    def test_get_genes_by_category(self):
        genes = migrate_from_governance()
        blockchain = get_genes_by_category(genes, "BLOCKCHAIN")
        self.assertGreater(len(blockchain), 0)
        self.assertTrue(all(g.category == "BLOCKCHAIN" for g in blockchain))


if __name__ == "__main__":
    unittest.main()
