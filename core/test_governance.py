
import unittest
from core.governance import ConstitutionEnforcer

class TestConstitutionEnforcer(unittest.TestCase):

    def test_verify_constitution_integrity(self):
        enforcer = ConstitutionEnforcer()
        self.assertTrue(enforcer.verify_constitution_integrity())

    def test_validate_task(self):
        enforcer = ConstitutionEnforcer()
        task = {"task_type": "test"}
        self.assertTrue(enforcer.validate_task(task))

    def test_enforce_sovereignty(self):
        enforcer = ConstitutionEnforcer()
        enforcer.enforce_sovereignty()

    def test_enforce_hierarchy(self):
        enforcer = ConstitutionEnforcer()
        system_prompt = "test"
        user_prompt = "test"
        response = "test"
        enforcer.enforce_hierarchy(system_prompt, user_prompt, response)

    def test_check(self):
        enforcer = ConstitutionEnforcer()
        text = "test"
        result = enforcer.check(text)
        self.assertTrue(result.passed)

    def test_enforce(self):
        enforcer = ConstitutionEnforcer()
        text = "test"
        result = enforcer.enforce(text)
        self.assertEqual(result["status"], "COMPLIANT")

if __name__ == '__main__':
    unittest.main()
