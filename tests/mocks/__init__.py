"""
tests/mocks — Mocks determinísticos para tests de DOF-MESH.

Importar desde aquí para compatibilidad futura:
    from tests.mocks import patch_provider, MockLLM
    from tests.mocks import make_fixture_success, make_fixture_rate_limit
    from tests.mocks import make_fixture_auth_error, make_fixture_timeout
    from tests.mocks import MockRateLimitError, MockAuthenticationError, MockTimeoutError
"""

from .mock_provider import (
    MockLLM,
    MockLLMError,
    MockRateLimitError,
    MockAuthenticationError,
    MockTimeoutError,
    make_fixture_success,
    make_fixture_rate_limit,
    make_fixture_auth_error,
    make_fixture_timeout,
    patch_provider,
)

__all__ = [
    "MockLLM",
    "MockLLMError",
    "MockRateLimitError",
    "MockAuthenticationError",
    "MockTimeoutError",
    "make_fixture_success",
    "make_fixture_rate_limit",
    "make_fixture_auth_error",
    "make_fixture_timeout",
    "patch_provider",
]
