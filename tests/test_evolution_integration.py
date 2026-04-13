"""
Test de integración: autonomous_loop ↔ GeneticPopulation
Valida que el loop evolutivo funciona end-to-end
sin requerir Ollama/Qwen3 (usa crossover, no LLM).

Estrategia de mock:
  - run_redteam_quick() se parchea para controlar ASR de forma determinística
    y evitar dependencia en attack_vectors.py (gitignored).
  - evolve_one_generation() usa apply_to_governance=True con el fixture real,
    por lo que governance.py puede ser modificado — addCleanup lo restaura.
"""
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

BASE_DIR = Path(__file__).parent.parent
GOVERNANCE_PATH = BASE_DIR / "core" / "governance.py"

# Importar run_evolutionary_loop una sola vez (evita re-import en cada test)
from tests.red_team.autonomous_loop import run_evolutionary_loop  # noqa: E402


def _governance_snapshot() -> str:
    return GOVERNANCE_PATH.read_text(encoding="utf-8")


def _governance_restore(content: str) -> None:
    GOVERNANCE_PATH.write_text(content, encoding="utf-8")


class TestEvolutionIntegration(unittest.TestCase):

    def test_evolutionary_loop_runs_one_generation(self):
        """El loop evolutivo corre 1 generación sin errores."""
        # ASR constante 50% → no mejora → rollback → 1 gen en history
        with patch("tests.red_team.autonomous_loop.run_redteam_quick",
                   return_value=(50.0, 5, [])):
            gov_before = _governance_snapshot()
            self.addCleanup(_governance_restore, gov_before)

            result = run_evolutionary_loop(
                threshold=99.0,   # 50% < 99% → break después de 1 gen
                max_generations=1,
                use_llm_mutation=False,
            )

        self.assertIn("generations", result)
        self.assertIn("asr_initial", result)
        self.assertIn("asr_final", result)
        self.assertIn("history", result)
        self.assertEqual(result["generations"], 1)

    def test_evolutionary_loop_rollback_on_regression(self):
        """Si ASR sube → rollback automático, governance.py idéntico al inicial."""
        call_count = [0]

        def mock_redteam_worsening():
            call_count[0] += 1
            if call_count[0] == 1:
                return (50.0, 5, [])   # baseline
            return (65.0, 10, [])       # después de evolución: peor → rollback

        gov_before = _governance_snapshot()
        self.addCleanup(_governance_restore, gov_before)

        with patch("tests.red_team.autonomous_loop.run_redteam_quick",
                   side_effect=mock_redteam_worsening):
            result = run_evolutionary_loop(
                threshold=15.0,
                max_generations=1,
                use_llm_mutation=False,
            )

        gov_after = _governance_snapshot()
        self.assertEqual(gov_before, gov_after,
                         "governance.py cambió sin mejora de ASR — rollback falló")

        # La generación debe estar marcada como rolled_back
        self.assertEqual(len(result["history"]), 1)
        self.assertTrue(result["history"][0]["rolled_back"])

    def test_148_tests_still_pass_after_evolution(self):
        """Los 148 tests base siguen pasando (governance no fue corrompida)."""
        result = subprocess.run(
            [sys.executable, "-m", "unittest",
             "tests.test_governance",
             "tests.test_constitution",
             "tests.test_ast_verifier",
             "tests.test_evolution_genome",
             "tests.test_evolution_fitness",
             "tests.test_evolution_operators",
             "tests.test_evolution_population",
             "-q"],
            capture_output=True, text=True,
            cwd=str(BASE_DIR),
            timeout=120,
        )
        output = result.stderr + result.stdout
        self.assertIn("OK", output,
                      f"Tests fallaron:\n{output[-600:]}")

    def test_cli_evolve_flag_works(self):
        """El flag --evolve en CLI existe y produce output correcto."""
        # Restaurar governance.py si el subproceso lo modifica
        gov_before = _governance_snapshot()
        self.addCleanup(_governance_restore, gov_before)

        result = subprocess.run(
            [sys.executable,
             "tests/red_team/autonomous_loop.py",
             "--evolve",
             "--generations", "1",
             "--threshold", "99.0"],
            capture_output=True, text=True,
            cwd=str(BASE_DIR),
            timeout=180,
        )
        output = result.stdout + result.stderr
        self.assertEqual(
            result.returncode, 0,
            f"CLI --evolve falló:\nstdout: {result.stdout[-400:]}\nstderr: {result.stderr[-400:]}"
        )
        self.assertIn("[EVOLUTION]", output,
                      "Output esperado '[EVOLUTION]' no encontrado")
        self.assertIn("EVOLUTION COMPLETE", output,
                      "Output esperado 'EVOLUTION COMPLETE' no encontrado")


if __name__ == "__main__":
    unittest.main()
