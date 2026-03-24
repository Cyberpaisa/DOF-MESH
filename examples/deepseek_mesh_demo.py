#!/usr/bin/env python3
"""
DeepSeek Mesh Node Demo
Shows parallel task execution via RemoteNodeAdapter.
"""
import sys
import threading
import time
from queue import Queue
sys.path.insert(0, '../src')

from dof.remote_node_adapter import RemoteNodeAdapter

def send_task(adapter, task_prompt, result_queue, task_id):
    """Send a single task and put result in queue."""
    try:
        response = adapter.send_task(task_prompt)
        result_queue.put((task_id, response))
    except Exception as e:
        result_queue.put((task_id, f"ERROR: {e}"))

def main():
    print("DeepSeek Mesh Demo")
    print("=" * 50)
    
    # 1) Initialize RemoteNodeAdapter
    adapter = RemoteNodeAdapter(node_id="deepseek-coder")
    print(f"Initialized adapter for node: {adapter.node_id}")
    
    # 2) Prepare tasks
    tasks = [
        ("a", "Review this code: def fib(n): return fib(n-1)+fib(n-2)"),
        ("b", "Write docstring for STUNClient.discover_public_endpoint"),
        ("c", "List 5 best practices for mesh security")
    ]
    
    # Parallel execution via threading
    result_queue = Queue()
    threads = []
    for task_id, prompt in tasks:
        t = threading.Thread(target=send_task, args=(adapter, prompt, result_queue, task_id))
        threads.append(t)
        t.start()
    
    # Wait for all threads
    for t in threads:
        t.join()
    
    # 3) Collect results
    results = {}
    while not result_queue.empty():
        task_id, response = result_queue.get()
        results[task_id] = response
    
    # 4) Print side-by-side table
    print("\nResults:\n")
    print(f"{'Task':<5} | {'Response Excerpt':<60}")
    print("-" * 70)
    for task_id, prompt in tasks:
        resp = results.get(task_id, "No response")
        excerpt = str(resp)[:57] + "..." if len(str(resp)) > 57 else resp
        print(f"{task_id:<5} | {excerpt:<60}")
    
    # 5) Cost estimate
    print("\nCost Estimate:")
    total_chars = sum(len(prompt) for _, prompt in tasks)
    # Assume responses are roughly same length as prompts for estimation
    total_chars += total_chars
    tokens = total_chars / 4  # ~4 chars/token
    cost = tokens * 0.00000027
    print(f"  Total chars (req+resp): {total_chars}")
    print(f"  Estimated tokens: {tokens:.1f}")
    print(f"  Cost (tokens * 0.00000027): ${cost:.6f}")
    
    print("\nDemo complete.")

if __name__ == "__main__":
    main()
