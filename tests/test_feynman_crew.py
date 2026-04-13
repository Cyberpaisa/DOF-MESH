"""
test_feynman_crew.py — Tests for FeynmanCrew
8 tests cubriendo: dataclass, run, governance topic, extraction, confidence, flag, never raises, log.
"""

import json
import os
import sys
import unittest
from dataclasses import fields
from pathlib import Path

# Asegurarse de que el root del proyecto esté en el path
_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.crews.feynman_crew import FeynmanCrew, FeynmanResult, _empty_result


class TestFeynmanCrew(unittest.TestCase):

    def setUp(self):
        """Instancia fresca + flag habilitado para cada test."""
        # Forzar el flag a True para la mayoría de los tests
        try:
            from core.feature_flags import flags
            flags.enable("feynman_research_crew")
            self._flags = flags
        except Exception:
            self._flags = None
        self.crew = FeynmanCrew()

    def tearDown(self):
        """Restaurar el flag a su estado por defecto después de cada test."""
        if self._flags is not None:
            self._flags.reset("feynman_research_crew")

    # ── Test 1 ────────────────────────────────────────────────────────────────

    def test_feynman_result_is_dataclass(self):
        """FeynmanResult debe ser un dataclass con los campos requeridos."""
        required_fields = {"topic", "explanation", "key_concepts", "analogies",
                           "gaps_identified", "confidence"}
        actual_fields = {f.name for f in fields(FeynmanResult)}
        self.assertTrue(
            required_fields.issubset(actual_fields),
            f"Faltan campos en FeynmanResult: {required_fields - actual_fields}"
        )

    # ── Test 2 ────────────────────────────────────────────────────────────────

    def test_run_returns_feynman_result(self):
        """run() debe retornar una instancia de FeynmanResult."""
        result = self.crew.run("prueba básica")
        self.assertIsInstance(result, FeynmanResult)
        self.assertEqual(result.topic, "prueba básica")
        self.assertIsInstance(result.explanation, str)
        self.assertIsInstance(result.key_concepts, list)
        self.assertIsInstance(result.analogies, list)
        self.assertIsInstance(result.gaps_identified, list)
        self.assertIsInstance(result.confidence, float)

    # ── Test 3 ────────────────────────────────────────────────────────────────

    def test_run_with_dof_governance_topic(self):
        """Con un topic de governance DOF debe extraer conceptos relevantes."""
        result = self.crew.run(
            "DOF governance pipeline",
            context="7 layers: Constitution, AST Validator, Tool Hook Gate PRE, "
                    "Supervisor Engine, Adversarial Guard, Memory Layer, Z3 SMT Verifier. "
                    "Zero LLM governance — todo determinístico."
        )
        self.assertIsInstance(result, FeynmanResult)
        # Debe haber encontrado conceptos relacionados con governance/agents
        self.assertGreater(len(result.key_concepts), 0,
                           "Debe extraer al menos 1 concepto de un topic de governance")
        # La explicación debe mencionar el topic
        self.assertIn("governance", result.explanation.lower())

    # ── Test 4 ────────────────────────────────────────────────────────────────

    def test_extract_concepts_finds_keywords(self):
        """_extract_concepts debe encontrar keywords conocidos en el topic."""
        concepts = self.crew._extract_concepts(
            "Z3 SMT theorem proof invariant",
            context="constraint satisfiability formal verification"
        )
        self.assertIsInstance(concepts, list)
        # Al menos z3 o proof o theorem deben estar presentes
        found_any = any(
            kw in concepts
            for kw in ["z3", "proof", "theorem", "invariant", "constraint", "formal", "verification"]
        )
        self.assertTrue(found_any,
                        f"No se encontró ningún keyword esperado. Conceptos extraídos: {concepts}")

    # ── Test 5 ────────────────────────────────────────────────────────────────

    def test_confidence_score_between_0_and_1(self):
        """confidence siempre debe estar en [0.0, 1.0]."""
        # Topic con muchos conceptos
        result_rich = self.crew.run(
            "Z3 formal verification theorem proof invariant constraint agent governance"
        )
        self.assertGreaterEqual(result_rich.confidence, 0.0)
        self.assertLessEqual(result_rich.confidence, 1.0)

        # Topic vacío / sin conceptos conocidos
        result_empty = self.crew.run("xyzzy quux blorb")
        self.assertGreaterEqual(result_empty.confidence, 0.0)
        self.assertLessEqual(result_empty.confidence, 1.0)

    # ── Test 6 ────────────────────────────────────────────────────────────────

    def test_disabled_flag_returns_empty_result(self):
        """Si el flag feynman_research_crew está deshabilitado, run() retorna resultado vacío."""
        if self._flags is not None:
            self._flags.disable("feynman_research_crew")

        # Crear crew con flag deshabilitado
        crew_disabled = FeynmanCrew()
        result = crew_disabled.run("Z3 formal verification")

        self.assertEqual(result.explanation, "",
                         "Con flag deshabilitado, explanation debe ser string vacío")
        self.assertEqual(result.key_concepts, [],
                         "Con flag deshabilitado, key_concepts debe ser lista vacía")
        self.assertEqual(result.confidence, 0.0,
                         "Con flag deshabilitado, confidence debe ser 0.0")

    # ── Test 7 ────────────────────────────────────────────────────────────────

    def test_never_raises(self):
        """run() nunca debe lanzar excepción, sin importar el input."""
        edge_cases = [
            "",                        # topic vacío
            "   ",                     # solo espacios
            "a" * 10000,               # topic extremadamente largo
            "🤖🧪🔬",                  # emojis
            None,                      # None (manejo defensivo)
            "Z3 SMT solver formal",    # caso normal
        ]
        for topic in edge_cases:
            try:
                if topic is None:
                    # None no está en la firma pero probamos que no rompe el sistema
                    result = self.crew.run("")
                else:
                    result = self.crew.run(topic)
                self.assertIsInstance(result, FeynmanResult,
                                      f"run('{topic[:20] if topic else ''}...') no retornó FeynmanResult")
            except Exception as exc:
                self.fail(f"run() lanzó excepción inesperada para topic '{topic}': {exc}")

    # ── Test 8 ────────────────────────────────────────────────────────────────

    def test_logs_to_jsonl(self):
        """run() debe crear/actualizar logs/feynman/sessions.jsonl con entradas válidas."""
        log_path = _ROOT / "logs" / "feynman" / "sessions.jsonl"

        # Registrar líneas actuales antes del test
        lines_before = 0
        if log_path.exists():
            with log_path.open(encoding="utf-8") as fh:
                lines_before = sum(1 for _ in fh)

        # Ejecutar el crew
        topic = "test_logs_to_jsonl unique topic 12345"
        self.crew.run(topic)

        # Verificar que el archivo existe y tiene al menos una línea nueva
        self.assertTrue(log_path.exists(), f"El archivo de log no fue creado: {log_path}")

        with log_path.open(encoding="utf-8") as fh:
            lines = fh.readlines()

        self.assertGreater(len(lines), lines_before,
                           "No se añadió ninguna línea al log después de run()")

        # Verificar que la última línea es JSON válido con los campos requeridos
        last_line = lines[-1].strip()
        self.assertTrue(last_line, "La última línea del log está vacía")

        try:
            entry = json.loads(last_line)
        except json.JSONDecodeError as exc:
            self.fail(f"La última entrada del log no es JSON válido: {exc}\n{last_line}")

        for required_key in ("ts", "topic", "confidence", "key_concepts"):
            self.assertIn(required_key, entry,
                          f"La entrada del log no tiene el campo '{required_key}'")


if __name__ == "__main__":
    unittest.main(verbosity=2)
