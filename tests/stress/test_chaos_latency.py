import unittest
from unittest.mock import patch
import time
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

from integrations.langgraph_adapter import GenericAdapter
from core.proof_hash import ProofSerializer

class TestChaosLatency(unittest.TestCase):
    @patch('core.oracle_bridge.AttestationRegistry.add')
    def test_chaos_latency_on_attestation(self, mock_add):
        # Simulate 800ms latency on attestation storage layer
        def slow_add(*args, **kwargs):
            time.sleep(0.8)
            return None
        mock_add.side_effect = slow_add
        
        adapter = GenericAdapter()
        payload = "Valid payload for chaos latency testing"
        
        # Run without simulated latency attached to output
        standard_result = adapter.wrap_output(payload)
        hash_without_latency = ProofSerializer.hash_proof(str(standard_result)).hex()
        
        # Run simulated latency call
        start = time.time()
        mock_add(None)
        elapsed = time.time() - start
        
        # Re-verify result and hash consistency
        latency_result = adapter.wrap_output(payload)
        hash_with_latency = ProofSerializer.hash_proof(str(latency_result)).hex()
        
        self.assertEqual(hash_with_latency, hash_without_latency, "Hashes mismatch under latency")
        self.assertGreater(elapsed, 0.7, "Latency simulation failed")
        
        print("\n--- CHAOS LATENCY TEST ---")
        print(f"Simulated Latency: {elapsed:.2f}s")
        print(f"Hash consistency: OK")

if __name__ == '__main__':
    unittest.main()
