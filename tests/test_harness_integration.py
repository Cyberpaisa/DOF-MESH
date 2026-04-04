"""
tests/test_harness_integration.py
───────────────────────────────────
Test de integración de los 3 módulos de harness de DOF-MESH v0.6.0:
  - tests/mocks/mock_provider.py  (patch_provider, MockLLM)
  - core/session_resume.py        (SessionStore, DaemonSession)
  - core/cost_tracker.py          (CostTracker, CallRecord)

Valida que los 3 módulos funcionen correctamente en conjunto
antes de integrarlos en autonomous_daemon.py.
"""

import os
import sys
import tempfile
import time
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from core.cost_tracker import CostTracker
from core.session_resume import SessionStore
from tests.mocks import patch_provider


# ─────────────────────────────────────────────────────────────────────────────
# TestHarnessIntegration
# ─────────────────────────────────────────────────────────────────────────────

class TestHarnessIntegration(unittest.TestCase):

    def _make_store(self, daemon_type="default") -> "tuple[SessionStore, str]":
        tmpdir = tempfile.mkdtemp()
        store = SessionStore(daemon_type=daemon_type, base_dir=tmpdir)
        return store, tmpdir

    # ── Test 1: ciclo completo ────────────────────────────────────────────────

    def test_full_cycle_simulation(self):
        """
        Simula un ciclo completo del daemon:
        1. CostTracker registra una llamada LLM mock
        2. SessionStore guarda el estado
        3. SessionStore carga el estado en un nuevo store (mismo directorio)
        4. El cycle_count y cost se preservan correctamente
        """
        tmpdir = tempfile.mkdtemp()

        # ── Ciclo 1: ejecutar y persistir ────────────────────────────────────
        tracker = CostTracker(session_id="integration-cycle-1")
        store = SessionStore(daemon_type="default", base_dir=tmpdir)

        with patch_provider("análisis completado") as mock_llm:
            response = mock_llm.call([{"role": "user", "content": "ejecuta tarea"}])
            tracker.record(
                role="architect",
                model=mock_llm.model,
                prompt_tokens=500,
                completion_tokens=200,
            )

        cycle_count = 1
        total_improvements = 1
        store.save(cycle_count=cycle_count, total_improvements=total_improvements)

        cost_after_cycle_1 = tracker.total_cost_usd()
        self.assertEqual(tracker.total_calls(), 1)

        # ── Reinicio: nuevo store, mismo directorio ───────────────────────────
        store2 = SessionStore(daemon_type="default", base_dir=tmpdir)
        session = store2.load()

        self.assertIsNotNone(session, "La sesión debe cargarse correctamente tras el reinicio")
        self.assertEqual(session.cycle_count, cycle_count)
        self.assertEqual(session.total_improvements, total_improvements)

        # El cost_tracker es independiente por diseño (no persistido en sesión)
        # pero el cycle_count restaurado permite correlacionar
        self.assertEqual(cost_after_cycle_1, 0.0)  # mock/model es gratis

    # ── Test 2: reinicio con contexto de costo ───────────────────────────────

    def test_session_resume_with_cost_context(self):
        """
        Simula reinicio del daemon con acumulación de llamadas:
        1. Ciclo 1: 3 llamadas LLM, guarda sesión
        2. Reinicio: nuevo SessionStore carga ciclo 1
        3. Ciclo 2: 2 llamadas más con nuevo tracker
        4. Los contadores acumulados son correctos
        """
        tmpdir = tempfile.mkdtemp()

        # ── Ciclo 1: 3 llamadas ───────────────────────────────────────────────
        tracker1 = CostTracker(session_id="cycle-1")
        store1 = SessionStore(daemon_type="builder", base_dir=tmpdir)

        with patch_provider("respuesta 1") as mock_llm:
            for i in range(3):
                mock_llm.call([])
                tracker1.record("architect", mock_llm.model, 300, 100)

        store1.save(cycle_count=3, total_improvements=2)
        cost_cycle_1 = tracker1.total_cost_usd()
        self.assertEqual(tracker1.total_calls(), 3)

        # ── Reinicio ──────────────────────────────────────────────────────────
        store2 = SessionStore(daemon_type="builder", base_dir=tmpdir)
        session = store2.load()
        self.assertIsNotNone(session)
        self.assertEqual(session.cycle_count, 3)
        self.assertEqual(session.total_improvements, 2)

        # ── Ciclo 2: 2 llamadas más (tracker nuevo, ciclos restaurados) ───────
        tracker2 = CostTracker(session_id="cycle-2")
        with patch_provider("respuesta 2") as mock_llm:
            for i in range(2):
                mock_llm.call([])
                tracker2.record("researcher", mock_llm.model, 400, 150)

        new_cycle_count = session.cycle_count + 2  # continuando desde el reinicio
        store2.save(cycle_count=new_cycle_count, total_improvements=session.total_improvements + 1)

        self.assertEqual(tracker2.total_calls(), 2)
        self.assertEqual(new_cycle_count, 5)

        # Verificar que el store conserva el session_id original
        session_updated = store2.current_session
        self.assertEqual(session_updated.session_id, session.session_id,
                         "session_id debe preservarse entre saves de la misma sesión")

    # ── Test 3: mock/model siempre cuesta $0 ─────────────────────────────────

    def test_mock_provider_cost_zero(self):
        """
        Verifica que mock/model siempre cuesta $0
        para no contaminar métricas reales en tests.
        """
        tracker = CostTracker(session_id="mock-cost-test")

        with patch_provider("respuesta mock") as mock_llm:
            # 100 llamadas con tokens altos
            for _ in range(100):
                mock_llm.call([])
                tracker.record(
                    role="architect",
                    model=mock_llm.model,
                    prompt_tokens=10_000,
                    completion_tokens=5_000,
                )

        self.assertEqual(tracker.total_calls(), 100)
        self.assertEqual(tracker.total_cost_usd(), 0.0,
                         "mock/model debe tener costo $0 para no contaminar métricas")
        self.assertEqual(mock_llm.call_count, 100)

        # El modelo del mock siempre empieza con "mock/"
        self.assertTrue(mock_llm.model.startswith("mock/"))

    # ── Test 4: todos los providers de DOF sin excepción ─────────────────────

    def test_cost_tracker_with_all_providers(self):
        """
        Registra llamadas para los providers reales de DOF.
        Verifica que ninguno lanza excepción y todos tienen precio >= 0.
        """
        providers = [
            ("architect",  "deepseek/deepseek-chat"),
            ("researcher", "groq/llama-3.3-70b-versatile"),
            ("guardian",   "nvidia_nim/qwen3.5-397b"),
            ("verifier",   "minimax/minimax-m2.1"),
            ("builder",    "cerebras/llama3.1-70b"),
            ("analyst",    "deepseek/deepseek-reasoner"),
            ("strategist", "openrouter/nousresearch/hermes-3-llama-3.1-405b"),
        ]

        tracker = CostTracker(session_id="all-providers-test")

        for role, model in providers:
            rec = tracker.record(
                role=role,
                model=model,
                prompt_tokens=1000,
                completion_tokens=500,
            )
            # Costo debe ser >= 0 para todos
            self.assertGreaterEqual(rec.cost_usd, 0.0,
                                    f"costo negativo para {model}")
            # Costo debe ser un float válido
            self.assertIsInstance(rec.cost_usd, float)
            self.assertFalse(
                rec.cost_usd != rec.cost_usd,  # NaN check
                f"cost_usd es NaN para {model}"
            )

        self.assertEqual(tracker.total_calls(), len(providers))

        # by_role debe tener un entry por cada rol
        summaries = tracker.by_role()
        for role, _ in providers:
            self.assertIn(role, summaries)

        # Costo total debe ser positivo (hay modelos de pago en la lista)
        self.assertGreater(tracker.total_cost_usd(), 0.0,
                           "Al menos algunos providers tienen costo > 0")

        # most_expensive_role debe retornar un rol válido
        expensive = tracker.most_expensive_role()
        self.assertIsNotNone(expensive)
        self.assertIn(expensive, [r for r, _ in providers])

    # ── Test 5: aislamiento — reset de los 3 módulos es independiente ─────────

    def test_three_modules_reset_isolation(self):
        """
        reset() de cada módulo no afecta a los otros.
        """
        tmpdir = tempfile.mkdtemp()
        tracker = CostTracker(session_id="isolation-test")
        store = SessionStore(daemon_type="default", base_dir=tmpdir)

        with patch_provider("ok") as mock_llm:
            mock_llm.call([])
            tracker.record("architect", mock_llm.model, 100, 50)
        store.save(cycle_count=1, total_improvements=0)

        # Reset tracker — no afecta store ni mock
        tracker.reset()
        self.assertEqual(tracker.total_calls(), 0)
        self.assertTrue(os.path.exists(store.session_path),
                        "reset() del tracker no debe borrar el archivo de sesión")

        # Reset store (en memoria) — no afecta tracker ni disco
        store.reset()
        self.assertIsNone(store.current_session)
        self.assertTrue(os.path.exists(store.session_path),
                        "reset() del store no debe borrar el archivo de sesión")

        # El archivo de sesión sigue siendo válido
        store3 = SessionStore(daemon_type="default", base_dir=tmpdir)
        session = store3.load()
        self.assertIsNotNone(session)
        self.assertEqual(session.cycle_count, 1)

    # ── Test 6: summary_dict incluye session_id ───────────────────────────────

    def test_cost_summary_correlates_with_session(self):
        """
        El session_id del CostTracker debe poder correlacionarse
        con el session_id del SessionStore para auditoría.
        """
        tmpdir = tempfile.mkdtemp()
        store = SessionStore(daemon_type="researcher", base_dir=tmpdir)

        # Primera escritura crea el session_id
        store.save(cycle_count=1, total_improvements=0)
        session_id = store.current_session.session_id

        # Crear CostTracker con el mismo session_id
        tracker = CostTracker(session_id=session_id)
        with patch_provider() as mock_llm:
            tracker.record("researcher", mock_llm.model, 200, 100)

        summary = tracker.summary_dict()
        self.assertEqual(summary["session_id"], session_id,
                         "CostTracker debe preservar el session_id del daemon")


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    unittest.main(verbosity=2)
