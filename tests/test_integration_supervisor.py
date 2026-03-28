"""Integration tests — CircuitBreaker in Supervisor + IntegrityWatcher in Governance."""

import unittest


class TestSupervisorCircuitBreakerIntegration(unittest.TestCase):
    """Verify that MetaSupervisor exposes circuit breaker infrastructure."""

    def test_supervisor_has_circuit_breakers(self):
        from core.supervisor import MetaSupervisor
        sup = MetaSupervisor()
        self.assertIsInstance(sup._circuit_breakers, dict)
        self.assertEqual(len(sup._circuit_breakers), 0)

    def test_get_breaker_creates_lazily(self):
        from core.supervisor import MetaSupervisor
        sup = MetaSupervisor()
        breaker = sup._get_breaker("test-agent")
        self.assertIn("test-agent", sup._circuit_breakers)
        self.assertEqual(breaker.agent_id, "test-agent")


class TestGovernanceIntegrityWatcherIntegration(unittest.TestCase):
    """Verify that ConstitutionEnforcer exposes integrity watcher."""

    def test_governance_has_integrity_watcher(self):
        from core.governance import ConstitutionEnforcer
        enforcer = ConstitutionEnforcer()
        self.assertTrue(hasattr(enforcer, "verify_constitution_integrity"))

    def test_governance_integrity_passes(self):
        from core.governance import ConstitutionEnforcer
        enforcer = ConstitutionEnforcer()
        result = enforcer.verify_constitution_integrity()
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
