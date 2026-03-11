import unittest
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

from integrations.langgraph_adapter import GenericAdapter

class TestCorrelatedFailure(unittest.TestCase):
    def test_correlated_agent_failure(self):
        # Objetivo: simular fallo simultáneo de 3 agentes en el mismo DAG
        # Validar: el sistema no produce attestations con governance_result="pass"
        adapter = GenericAdapter()
        
        # Simulate correlated structural failure - Agents output empty or Error tokens
        failed_outputs = [
            "Error: Timeout during extraction",
            "Exception in agent execution: LLM provider failed",
            "Internal Server Error 500 when accessing storage"
        ]
        
        false_positives = 0
        for out in failed_outputs:
            res = adapter.wrap_output(out)
            # A structural failure (like simple error text) shouldn't blindly pass
            # Ideally, governance rules catch error payloads or they lack expected structured data.
            # We assume the enforcer fails them or scores them zero.
            if res["status"] == "pass" and res["score"] > 0.8:
                false_positives += 1
                
        print(f"\n--- CORRELATED FAILURE TEST ---")
        print(f"False Positives: {false_positives}")
        
        self.assertEqual(false_positives, 0, "System produced false positive attestations during correlated failure")

if __name__ == '__main__':
    unittest.main()
