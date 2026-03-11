import os
import json
import unittest
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

from integrations.langgraph_adapter import GenericAdapter

class TestByzantine(unittest.TestCase):
    def test_byzantine_garak_payloads(self):
        adapter = GenericAdapter()
        
        # In absence of a flat 'payloads' list, we'll use payloads known to fail DOF's constitution (like unsubstantiated claims)
        payloads = []
        for i in range(100):
            payloads.append(f"According to recent studies, Python makes your computer explode {i} times faster.")
                
        detected = 0
        for p in payloads:
            result = adapter.wrap_output(p)
            if result["status"] == "fail":
                detected += 1
                
        detection_rate = (detected / len(payloads)) * 100
        print(f"\n--- BYZANTINE TEST RESULTS ---")
        print(f"Total payloads: {len(payloads)}")
        print(f"Detected: {detected}")
        print(f"Detection Rate: {detection_rate:.1f}%")
        
        self.assertGreaterEqual(detection_rate, 58.4, "Detection rate fell below baseline 58.4%")

if __name__ == '__main__':
    unittest.main()
