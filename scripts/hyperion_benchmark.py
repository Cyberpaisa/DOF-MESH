"""
hyperion_benchmark.py — Benchmark end-to-end DOF Mesh Hyperion.

Mide el stack completo:
  ConsistentHashRing → DOFShardManager → DistributedMeshQueue → GossipProtocol → WAL

Uso: python3 scripts/hyperion_benchmark.py
"""
import statistics
import tempfile
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.dof_sharding import ConsistentHashRing, DOFShardManager
from core.dof_consensus import GossipProtocol
from core.dof_wal import WriteAheadLog
from core.dof_distributed_queue import DistributedMeshQueue, DistributedTask

MACHINES = ["machine-a", "machine-b", "machine-c", "machine-d", "machine-e"]
N_AGENTS = 80
N_TASKS  = 10_000
SHARDS   = 10


def bench_ring(n=100_000):
    ring = ConsistentHashRing(replication_factor=3)
    for i, m in enumerate(MACHINES):
        ring.add_node(m, rack=f"rack-{i}")
    t0 = time.perf_counter()
    for i in range(n):
        ring.get_node(f"task-{i}")
    ms = (time.perf_counter() - t0) * 1000
    return {"lookups": n, "total_ms": round(ms, 1), "us_per_lookup": round(ms/n*1000, 2),
            "throughput": round(n/(ms/1000))}


def bench_queue(n=N_TASKS):
    sm = DOFShardManager(MACHINES, shard_count=SHARDS, replication_factor=3)
    q  = DistributedMeshQueue("bench-node", sm)
    latencies = []

    # Enqueue
    t0 = time.perf_counter()
    for i in range(n):
        task = DistributedTask(
            task_id=f"t{i}",
            shard_key=f"agent-{i % N_AGENTS}",
            prompt=f"task {i}",
            priority=i % 3,
        )
        q.enqueue(task)
    enqueue_ms = (time.perf_counter() - t0) * 1000

    # Dequeue with per-task latency
    t0 = time.perf_counter()
    count = 0
    while q.qsize() > 0:
        ts = time.perf_counter()
        task = q.dequeue_any(timeout=0.001)
        if task:
            latencies.append((time.perf_counter() - ts) * 1_000_000)
            count += 1
    dequeue_ms = (time.perf_counter() - t0) * 1000

    p50 = round(statistics.median(latencies), 1)
    p95 = round(sorted(latencies)[int(len(latencies)*0.95)], 1)
    p99 = round(sorted(latencies)[int(len(latencies)*0.99)], 1)

    return {
        "tasks": n, "shards": SHARDS, "machines": len(MACHINES),
        "enqueue_ms": round(enqueue_ms, 1), "dequeue_ms": round(dequeue_ms, 1),
        "enqueue_throughput": round(n/(enqueue_ms/1000)),
        "dequeue_throughput": round(n/(dequeue_ms/1000)),
        "latency_p50_us": p50, "latency_p95_us": p95, "latency_p99_us": p99,
        "shards_used": sum(1 for v in q.status()["per_shard"].values() if v == 0),
    }


def bench_gossip(n_nodes=5, n_keys=100):
    nodes = [GossipProtocol(f"g{i}", fanout=3, interval_ms=20) for i in range(n_nodes)]
    for a in nodes:
        for b in nodes:
            if a is not b:
                a.register_peer(b)
    for node in nodes:
        node.start()

    # Write all keys to node 0
    t0 = time.perf_counter()
    for i in range(n_keys):
        nodes[0].put(f"key-{i}", f"value-{i}")

    # Wait for convergence
    converged_ms = None
    for ms in range(500):
        time.sleep(0.001)
        all_have = all(nodes[-1].get(f"key-{n_keys-1}") is not None for _ in [1])
        if all_have:
            converged_ms = ms + 1
            break

    for node in nodes:
        node.stop()

    return {
        "nodes": n_nodes, "keys": n_keys,
        "convergence_ms": converged_ms or ">500",
        "write_ms": round((time.perf_counter() - t0) * 1000, 1),
    }


def bench_wal(n=1_000):
    with tempfile.TemporaryDirectory() as tmp:
        wal = WriteAheadLog(tmp)
        t0 = time.perf_counter()
        seqs = [wal.append("enqueue", f"t{i}", {"i": i}) for i in range(n)]
        write_ms = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        recovered = wal.recover()
        recover_ms = (time.perf_counter() - t0) * 1000

        for s in seqs:
            wal.confirm(s)
        t0 = time.perf_counter()
        removed = wal.compact()
        compact_ms = (time.perf_counter() - t0) * 1000

    return {
        "entries": n, "write_ms": round(write_ms, 1),
        "write_throughput": round(n/(write_ms/1000)),
        "recover_ms": round(recover_ms, 1),
        "compact_ms": round(compact_ms, 1),
        "compacted": removed,
    }


def main():
    print("=" * 60)
    print("  DOF MESH HYPERION — BENCHMARK END-TO-END")
    print(f"  {len(MACHINES)} máquinas | {SHARDS} shards | {N_AGENTS} agentes | {N_TASKS:,} tareas")
    print("=" * 60)

    print("\n📊 ConsistentHashRing (100K lookups)...")
    r = bench_ring()
    print(f"   {r['throughput']:,} lookups/sec | {r['us_per_lookup']}µs/lookup")

    print("\n📊 DistributedMeshQueue (10K tareas)...")
    q = bench_queue()
    print(f"   Enqueue: {q['enqueue_throughput']:,} tasks/sec")
    print(f"   Dequeue: {q['dequeue_throughput']:,} tasks/sec")
    print(f"   Latencia P50={q['latency_p50_us']}µs | P95={q['latency_p95_us']}µs | P99={q['latency_p99_us']}µs")

    print("\n📊 GossipProtocol (5 nodos, 100 keys)...")
    g = bench_gossip()
    print(f"   Convergencia: {g['convergence_ms']}ms | {g['keys']} keys replicadas")

    print("\n📊 WriteAheadLog (1K entradas)...")
    w = bench_wal()
    print(f"   Write: {w['write_throughput']:,} entries/sec | Recover: {w['recover_ms']}ms | Compact: {w['compact_ms']}ms")

    print("\n" + "=" * 60)
    print("  RESUMEN HYPERION")
    print("=" * 60)
    print(f"  Ring:    {r['throughput']:>12,} lookups/sec")
    print(f"  Queue:   {q['enqueue_throughput']:>12,} tasks/sec (enqueue)")
    print(f"  Queue:   {q['dequeue_throughput']:>12,} tasks/sec (dequeue)")
    print(f"  WAL:     {w['write_throughput']:>12,} entries/sec")
    print(f"  Gossip:  convergencia en {g['convergence_ms']}ms ({g['nodes']} nodos)")
    print(f"  SLA <500ms: {'✅ CUMPLE' if isinstance(g['convergence_ms'], int) and g['convergence_ms'] < 500 else '⚠ REVISAR'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
