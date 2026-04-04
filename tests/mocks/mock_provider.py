"""
tests/mocks/mock_provider.py
────────────────────────────
Mock determinístico de crewai.LLM y ProviderManager.

Permite testear cualquier módulo que llame a ProviderManager.get_llm_for_role()
sin necesitar API keys ni conexión de red.

Uso básico:
    from tests.mocks import patch_provider

    with patch_provider("respuesta custom") as mock_llm:
        result = my_function_that_uses_provider()
        assert mock_llm.call_count == 1

Fixtures disponibles (factories — cada llamada crea una instancia fresca):
    make_fixture_success()      → respuesta normal
    make_fixture_rate_limit()   → lanza MockRateLimitError en el 2do call
    make_fixture_auth_error()   → lanza MockAuthenticationError siempre
    make_fixture_timeout()      → lanza MockTimeoutError siempre
"""

import logging
import threading
from contextlib import contextmanager
from typing import Any, Generator, Optional
from unittest.mock import patch

logger = logging.getLogger("dof.mock_provider")


# ─────────────────────────────────────────────────────────────────────────────
# Excepciones mock (imitan errores reales de providers)
# ─────────────────────────────────────────────────────────────────────────────

class MockLLMError(Exception):
    """Base para excepciones de fixtures mock."""


class MockRateLimitError(MockLLMError):
    """Simula HTTP 429 — rate limit del provider."""


class MockAuthenticationError(MockLLMError):
    """Simula HTTP 401 — API key inválida o expirada."""


class MockTimeoutError(MockLLMError):
    """Simula timeout de conexión."""


# ─────────────────────────────────────────────────────────────────────────────
# MockLLM
# ─────────────────────────────────────────────────────────────────────────────

class MockLLM:
    """
    Mock de crewai.LLM.

    Acepta el mismo constructor que crewai.LLM para que sea
    intercambiable. Retorna respuestas determinísticas sin API.

    Sigue el patrón singleton DOF: tiene reset() para aislamiento entre tests.
    Thread-safe: usa lock interno para call_count.
    """

    def __init__(
        self,
        model: str = "mock/model",
        api_key: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        response: str = "Mock LLM response",
        side_effect: Optional[BaseException] = None,
        **kwargs: Any,
    ) -> None:
        self.model = model
        self.api_key = api_key
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._response = response
        self._side_effect = side_effect
        self._call_count = 0
        self._lock = threading.Lock()
        logger.debug("MockLLM created: model=%s side_effect=%s", model,
                     type(side_effect).__name__ if side_effect else None)

    # ── Interfaz pública ────────────────────────────────────────────────────

    def call(self, messages: list, **kwargs: Any) -> str:
        """
        Simula una llamada LLM.

        Returns:
            self._response si no hay side_effect.

        Raises:
            self._side_effect si fue configurado.
        """
        with self._lock:
            self._call_count += 1
        if self._side_effect is not None:
            raise self._side_effect
        logger.debug("MockLLM.call() → %r", self._response[:60])
        return self._response

    @property
    def call_count(self) -> int:
        """Número de veces que call() fue invocado."""
        with self._lock:
            return self._call_count

    def reset(self) -> None:
        """Resetea call_count a 0. Requerido por patrón singleton DOF."""
        with self._lock:
            self._call_count = 0
        logger.debug("MockLLM.reset(): model=%s", self.model)

    def __repr__(self) -> str:
        return f"MockLLM(model={self.model!r}, call_count={self._call_count})"


# ─────────────────────────────────────────────────────────────────────────────
# _RateLimitAfterFirstLLM — fixture interno
# ─────────────────────────────────────────────────────────────────────────────

class _RateLimitAfterFirstLLM(MockLLM):
    """LLM que responde la primera llamada y lanza rate limit en la segunda."""

    def call(self, messages: list, **kwargs: Any) -> str:
        with self._lock:
            self._call_count += 1
            count = self._call_count
        if count >= 2:
            raise MockRateLimitError(
                f"Rate limit exceeded (mock) on call #{count}"
            )
        return self._response


# ─────────────────────────────────────────────────────────────────────────────
# Factories de fixtures (cada llamada → instancia fresca, sin estado compartido)
# ─────────────────────────────────────────────────────────────────────────────

def make_fixture_success(response: str = "Mock success response") -> MockLLM:
    """MockLLM que siempre responde exitosamente."""
    return MockLLM(model="mock/success", response=response)


def make_fixture_rate_limit(first_response: str = "First call OK") -> _RateLimitAfterFirstLLM:
    """MockLLM que responde en el primer call y lanza rate limit en el segundo."""
    return _RateLimitAfterFirstLLM(model="mock/rate-limit", response=first_response)


def make_fixture_auth_error() -> MockLLM:
    """MockLLM que siempre lanza MockAuthenticationError."""
    return MockLLM(
        model="mock/auth-error",
        side_effect=MockAuthenticationError("Invalid API key (mock)"),
    )


def make_fixture_timeout() -> MockLLM:
    """MockLLM que siempre lanza MockTimeoutError."""
    return MockLLM(
        model="mock/timeout",
        side_effect=MockTimeoutError("Connection timed out after 30s (mock)"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# patch_provider — context manager principal
# ─────────────────────────────────────────────────────────────────────────────

@contextmanager
def patch_provider(
    response: str = "Mock response",
) -> Generator[MockLLM, None, None]:
    """
    Parchea ProviderManager.get_llm_for_role() en el scope del with.

    Reemplaza el método estático por una función que retorna un MockLLM
    sin importar el 'role' solicitado. Restaura el original al salir.

    Args:
        response: Texto que retornará MockLLM.call().

    Yields:
        MockLLM configurado con la respuesta dada.

    Ejemplo:
        with patch_provider("análisis completado") as mock_llm:
            resultado = funcion_que_usa_provider()
            assert mock_llm.call_count >= 1
    """
    mock_llm = MockLLM(model="mock/patched", response=response)

    def _get_mock_llm(role: str) -> MockLLM:
        logger.debug("patch_provider: get_llm_for_role(%r) → MockLLM", role)
        return mock_llm

    with patch("core.providers.ProviderManager.get_llm_for_role",
               side_effect=_get_mock_llm):
        yield mock_llm
