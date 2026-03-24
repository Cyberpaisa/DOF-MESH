#!/usr/bin/env python3
"""Benchmark DOF mesh performance."""

import argparse
import json
import os
import shutil
import time
import tempfile
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import secrets
import sys


def benchmark_message_throughput(iterations: int, work_dir: Path) -> float:
    """Write 1000 JSON files to inbox, measure msgs/sec."""
    inbox = work_dir / "logs" / "mesh" / "inbox" / "bench"
    inbox.mkdir(parents=True, exist_ok=True)
    
    payload = {"test": "data", "timestamp": time.time()}
    start = time.perf_counter()
    for i in range(iterations * 1000):
        (inbox / f"msg_{i}.json").write_text(json.dumps(payload))
    end = time.perf_counter()
    
    total_msgs = iterations * 1000
    elapsed = end - start
    return total_msgs / elapsed if elapsed > 0 else 0.0


def benchmark_encryption_overhead(iterations: int) -> float:
    """AES-GCM encrypt/decrypt 1000x 1KB payload, measure ms/op."""
    key = AESGCM.generate_key(bit_length=256)
    aesgcm = AESGCM(key)
    nonce = secrets.token_bytes(12)
    data = secrets.token_bytes(1024)
    
    start = time.perf_counter()
    for _ in range(iterations * 1000):
        ciphertext = aesgcm.encrypt(nonce, data, None)
        aesgcm.decrypt(nonce, ciphertext, None)
    end = time.perf_counter()
    
    total_ops = iterations * 1000 * 2  # encrypt + decrypt
    elapsed_ms = (end - start) * 1000
    return elapsed_ms / total_ops if total_ops > 0 else 0.0


def benchmark_node_registry(iterations: int, work_dir: Path) -> float:
    """Read nodes.json 1000x, measure ops/sec."""
    nodes_file = work_dir / "logs" / "mesh" / "nodes.json"
    nodes_file.parent.mkdir(parents=True, exist_ok=True)
    nodes_file.write_text(json.dumps({"nodes": [{"id": "test", "status": "active"}]}))
    
    start = time.perf_counter()
    for _ in range(iterations * 1000):
        with open(nodes_file, 'r') as f:
            json.load(f)
    end = time.perf_counter()
    
    total_reads = iterations * 1000
    elapsed = end - start
    return total_reads / elapsed if elapsed > 0 else 0.0


def benchmark_broadcast_simulation(iterations: int) -> float:
    """Simulate 10 nodes, 100 messages each, measure total time per iteration."""
    total_messages = 10 * 100  # per iteration
    
    start = time.perf_counter()
    for _ in range(iterations):
        # Simulate message passing with minimal overhead
        for node in range(10):
            for msg in range(100):
                _ = node + msg  # dummy work
    end = time.perf_counter()
    
    elapsed = end - start
    return elapsed / iterations if iterations > 0 else 0.0


def print_results(results: dict):
    """Print ASCII table."""
    headers = ["Benchmark", "Result", "Unit"]
    rows = [
        ["Message throughput", f"{results['throughput']:.2f}", "msgs/sec"],
        ["Encryption overhead", f"{results['encryption']:.4f}", "ms/op"],
        ["Node registry read", f"{results['registry']:.2f}", "ops/sec"],
        ["Broadcast simulation", f"{results['broadcast']:.6f}", "sec/iter"],
    ]
    
    col_widths = [max(len(str(item)) for item in col) for col in zip(headers, *rows)]
    
    def print_row(items):
        print(" | ".join(str(item).ljust(w) for item, w in zip(items, col_widths)))
    
    print_row(headers)
    print("-" * (sum(col_widths) + 3 * (len(headers) - 1)))
    for row in rows:
        print_row(row)


def main():
    parser = argparse.ArgumentParser(description="Benchmark DOF mesh performance.")
    parser.add_argument(
        "--iterations",
        type=int,
        default=1,
        help="Number of iterations per benchmark (multiplies base counts)"
    )
    args = parser.parse_args()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        work_dir = Path(tmpdir)
        
        print(f"Running benchmarks with {args.iterations} iteration(s)...")
        
        throughput = benchmark_message_throughput(args.iterations, work_dir)
        encryption = benchmark_encryption_overhead(args.iterations)
        registry = benchmark_node_registry(args.iterations, work_dir)
        broadcast = benchmark_broadcast_simulation(args.iterations)
        
        results = {
            "throughput": throughput,
            "encryption": encryption,
            "registry": registry,
            "broadcast": broadcast,
        }
        
        print()
        print_results(results)


if __name__ == "__main__":
    main()
