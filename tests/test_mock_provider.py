"""
tests/test_mock_provider.py
────────────────────────────
Tests para tests/mocks/mock_provider.py.

Valida que el mock mismo sea correcto antes de usarlo en otros tests.

Suite:
    TestMockLLM           — comportamiento básico de MockLLM
    TestMockLLMFixtures   — fixtures de error (rate_limit, auth, timeout)
    TestPatchProvider     — context manager patch_provider()
"""

import os
import sys
import threading
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from tests.mocks import (
    MockLLM,
    MockRateLimitError,
    MockAuthenticationError,
    MockTimeoutError,
    make_fixture_success,
    make_fixture_rate_limit,
    make_fixture_auth_error,
    make_fixture_timeout,
    patch_provider,
)


# ─────────────────────────────────────────────────────────────────────────────
# TestMockLLM — comportamiento básico
# ─────────────────────────────────────────────────────────────────────────────

class TestMockLLM(unittest.TestCase):
    """Comportamiento básico de MockLLM."""

    def setUp(self):
        self.llm = MockLLM(response="respuesta de prueba")

    # ── Constructor ─────────────────────────────────────────────────────────

    def test_constructor_defaults_set_correctly(self):
        llm = MockLLM()
        self.assertEqual(llm.model, "mock/model")
        self.assertIsNone(llm.api_key)
        self.assertEqual(llm.temperature, 0.3)
        self.assertEqual(llm.max_tokens, 4096)

    def test_constructor_accepts_crewai_llm_kwargs(self):
        """Acepta los mismos kwargs que crewai.LLM sin lanzar excepciones."""
        llm = MockLLM(
            model="groq/llama-3.3-70b-versatile",
            api_key="test-key",
            temperature=0.7,
            max_tokens=2048,
        )
        self.assertEqual(llm.model, "groq/llama-3.3-70b-versatile")
        self.assertEqual(llm.api_key, "test-key")

    def test_constructor_accepts_extra_kwargs_without_error(self):
        """Kwargs desconocidos no lanzan TypeError."""
        llm = MockLLM(base_url="http://localhost", stream=True)
        self.assertIsNotNone(llm)

    # ── call() ──────────────────────────────────────────────────────────────

    def test_call_returns_configured_response(self):
        result = self.llm.call([{"role": "user", "content": "hola"}])
        self.assertEqual(result, "respuesta de prueba")

    def test_call_accepts_messages_list(self):
        messages = [
            {"role": "system", "content": "eres un agente"},
            {"role": "user", "content": "ejecuta tarea"},
        ]
        result = self.llm.call(messages)
        self.assertIsInstance(result, str)

    def test_call_accepts_extra_kwargs(self):
        """Los kwargs extra de crewai no rompen el mock."""
        result = self.llm.call([], temperature=0.1, max_tokens=100)
        self.assertEqual(result, "respuesta de prueba")

    # ── call_count ──────────────────────────────────────────────────────────

    def test_call_count_starts_at_zero(self):
        self.assertEqual(self.llm.call_count, 0)

    def test_call_count_increments_per_call(self):
        self.llm.call([])
        self.assertEqual(self.llm.call_count, 1)
        self.llm.call([])
        self.assertEqual(self.llm.call_count, 2)

    def test_call_count_increments_on_side_effect(self):
        """call_count sube incluso cuando lanza excepción."""
        llm = MockLLM(side_effect=MockAuthenticationError("test"))
        with self.assertRaises(MockAuthenticationError):
            llm.call([])
        self.assertEqual(llm.call_count, 1)

    # ── reset() ─────────────────────────────────────────────────────────────

    def test_reset_zeroes_call_count(self):
        self.llm.call([])
        self.llm.call([])
        self.llm.reset()
        self.assertEqual(self.llm.call_count, 0)

    def test_reset_does_not_change_response(self):
        self.llm.call([])
        self.llm.reset()
        result = self.llm.call([])
        self.assertEqual(result, "respuesta de prueba")

    def test_reset_idempotent_when_already_zero(self):
        self.llm.reset()
        self.assertEqual(self.llm.call_count, 0)

    # ── side_effect ─────────────────────────────────────────────────────────

    def test_side_effect_raises_on_call(self):
        llm = MockLLM(side_effect=MockTimeoutError("timeout"))
        with self.assertRaises(MockTimeoutError):
            llm.call([])

    def test_side_effect_raises_every_call(self):
        llm = MockLLM(side_effect=MockAuthenticationError("401"))
        for _ in range(3):
            with self.assertRaises(MockAuthenticationError):
                llm.call([])
        self.assertEqual(llm.call_count, 3)

    # ── thread safety ────────────────────────────────────────────────────────

    def test_call_count_is_thread_safe(self):
        """call_count es correcto bajo concurrencia."""
        results = []
        errors = []

        def worker():
            try:
                self.llm.call([])
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)
        self.assertEqual(self.llm.call_count, 50)

    # ── repr ─────────────────────────────────────────────────────────────────

    def test_repr_includes_model_and_call_count(self):
        self.llm.call([])
        r = repr(self.llm)
        self.assertIn("mock/model", r)
        self.assertIn("1", r)


# ─────────────────────────────────────────────────────────────────────────────
# TestMockLLMFixtures — factories de fixtures
# ─────────────────────────────────────────────────────────────────────────────

class TestMockLLMFixtures(unittest.TestCase):
    """Factories de fixtures retornan instancias frescas con comportamiento correcto."""

    def test_make_fixture_success_returns_fresh_instance(self):
        a = make_fixture_success()
        b = make_fixture_success()
        self.assertIsNot(a, b)

    def test_make_fixture_success_responds_normally(self):
        llm = make_fixture_success("ok")
        self.assertEqual(llm.call([]), "ok")

    def test_make_fixture_success_default_response(self):
        llm = make_fixture_success()
        result = llm.call([])
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_make_fixture_rate_limit_first_call_succeeds(self):
        llm = make_fixture_rate_limit("primera respuesta")
        result = llm.call([])
        self.assertEqual(result, "primera respuesta")

    def test_make_fixture_rate_limit_second_call_raises(self):
        llm = make_fixture_rate_limit()
        llm.call([])  # primera — OK
        with self.assertRaises(MockRateLimitError):
            llm.call([])  # segunda — rate limit

    def test_make_fixture_rate_limit_third_call_also_raises(self):
        llm = make_fixture_rate_limit()
        llm.call([])
        with self.assertRaises(MockRateLimitError):
            llm.call([])
        with self.assertRaises(MockRateLimitError):
            llm.call([])

    def test_make_fixture_auth_error_always_raises(self):
        llm = make_fixture_auth_error()
        for _ in range(3):
            with self.assertRaises(MockAuthenticationError):
                llm.call([])

    def test_make_fixture_auth_error_has_message(self):
        llm = make_fixture_auth_error()
        with self.assertRaises(MockAuthenticationError) as ctx:
            llm.call([])
        self.assertIn("API key", str(ctx.exception))

    def test_make_fixture_timeout_always_raises(self):
        llm = make_fixture_timeout()
        for _ in range(3):
            with self.assertRaises(MockTimeoutError):
                llm.call([])

    def test_make_fixture_timeout_has_message(self):
        llm = make_fixture_timeout()
        with self.assertRaises(MockTimeoutError) as ctx:
            llm.call([])
        self.assertIn("timed out", str(ctx.exception))

    def test_fixtures_are_independent_instances(self):
        """Cada factory retorna instancia fresca — sin estado compartido."""
        a = make_fixture_rate_limit()
        b = make_fixture_rate_limit()
        a.call([])  # primer call de 'a'
        # 'b' no fue llamado — su primer call no debe fallar
        result = b.call([])
        self.assertIsNotNone(result)


# ─────────────────────────────────────────────────────────────────────────────
# TestPatchProvider — context manager
# ─────────────────────────────────────────────────────────────────────────────

class TestPatchProvider(unittest.TestCase):
    """patch_provider() parchea y restaura ProviderManager correctamente."""

    def test_yields_mock_llm_instance(self):
        with patch_provider("test resp") as mock_llm:
            self.assertIsInstance(mock_llm, MockLLM)

    def test_mock_llm_has_configured_response(self):
        with patch_provider("respuesta inyectada") as mock_llm:
            result = mock_llm.call([])
        self.assertEqual(result, "respuesta inyectada")

    def test_provider_manager_returns_mock_inside_context(self):
        """get_llm_for_role() retorna MockLLM dentro del with."""
        from core.providers import ProviderManager
        with patch_provider("mock activo") as mock_llm:
            llm = ProviderManager.get_llm_for_role("architect")
            self.assertIs(llm, mock_llm)

    def test_provider_manager_any_role_returns_same_mock(self):
        """Todos los roles retornan el mismo MockLLM."""
        from core.providers import ProviderManager
        with patch_provider() as mock_llm:
            for role in ("architect", "researcher", "guardian", "verifier"):
                llm = ProviderManager.get_llm_for_role(role)
                self.assertIs(llm, mock_llm)

    def test_original_provider_restored_after_context(self):
        """Después del with, ProviderManager vuelve a su implementación real."""
        from core.providers import ProviderManager
        original = ProviderManager.get_llm_for_role

        with patch_provider():
            patched = ProviderManager.get_llm_for_role
            self.assertIsNot(patched, original)

        restored = ProviderManager.get_llm_for_role
        self.assertIs(restored, original)

    def test_call_count_tracks_calls_inside_context(self):
        from core.providers import ProviderManager
        with patch_provider("tracking") as mock_llm:
            ProviderManager.get_llm_for_role("researcher")
            ProviderManager.get_llm_for_role("architect")
            # Llamar directamente también cuenta
            mock_llm.call([])
        self.assertEqual(mock_llm.call_count, 1)  # solo la llamada directa

    def test_mock_llm_reset_works_inside_context(self):
        with patch_provider() as mock_llm:
            mock_llm.call([])
            mock_llm.call([])
            self.assertEqual(mock_llm.call_count, 2)
            mock_llm.reset()
            self.assertEqual(mock_llm.call_count, 0)

    def test_default_response_is_nonempty_string(self):
        with patch_provider() as mock_llm:
            result = mock_llm.call([])
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_context_manager_exception_still_restores_patch(self):
        """Si el cuerpo del with lanza excepción, el patch se restaura igual."""
        from core.providers import ProviderManager
        original = ProviderManager.get_llm_for_role

        try:
            with patch_provider():
                raise ValueError("error de prueba")
        except ValueError:
            pass

        self.assertIs(ProviderManager.get_llm_for_role, original)


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    unittest.main(verbosity=2)
