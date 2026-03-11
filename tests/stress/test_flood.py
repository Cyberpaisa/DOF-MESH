import concurrent.futures
import time
import statistics
import unittest

import sys
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

from integrations.langgraph_adapter import GenericAdapter

class TestFlood(unittest.TestCase):
    def test_flood_1000_calls(self):
        adapter = GenericAdapter()
        payload = "This is a standard output payload that should pass governance."
        
        latencies = []
        
        def run_single():
            start = time.time()
            adapter.wrap_output(payload)
            return (time.time() - start) * 1000
            
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(run_single) for _ in range(1000)]
            for future in concurrent.futures.as_completed(futures):
                latencies.append(future.result())
                
        p50 = statistics.quantiles(latencies, n=100)[49]
        p95 = statistics.quantiles(latencies, n=100)[94]
        p99 = statistics.quantiles(latencies, n=100)[98]
        mean = statistics.mean(latencies)
        mx = max(latencies)
        mn = min(latencies)
        
        print("\n--- FLOOD TEST RESULTS ---")
        print(f"Total Calls: 1000")
        print(f"Min: {mn:.2f}ms | Max: {mx:.2f}ms | Mean: {mean:.2f}ms")
        print(f"p50: {p50:.2f}ms | p95: {p95:.2f}ms | p99: {p99:.2f}ms")
        
        self.assertLess(p99, 500.0, "p99 latency exceeded 500ms")

if __name__ == '__main__':
    unittest.main()
