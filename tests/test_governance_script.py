
import unittest
from core.governance import ConstitutionEnforcer, GovernanceResult, RulePriority

class TestGovernance(unittest.TestCase):
    def test_constitution_enforcer_init(self):
        enforcer = ConstitutionEnforcer(mesh_dir="test_mesh")
        self.assertEqual(enforcer.mesh_dir, Path("test_mesh"))

    def test_governance_result_dataclass(self):
        result = GovernanceResult(passed=True, score=1.0, violations=[], warnings=[])
        self.assertTrue(result.passed)
        self.assertEqual(result.score, 1.0)
        self.assertEqual(result.violations, [])
        self.assertEqual(result.warnings, [])

    def test_rule_priority_enum(self):
        self.assertEqual(RulePriority.SYSTEM.value, "SYSTEM")
        self.assertEqual(RulePriority.USER.value, "USER")
        self.assertEqual(RulePriority.ASSISTANT.value, "ASSISTANT")

if __name__ == "__main__":
    unittest.main()
