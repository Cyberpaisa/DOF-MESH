"""
test_hyperion_load.py — Test de carga multi-agente Hyperion.

Simula 6 agentes simultáneos procesando 1000 tareas via DistributedMeshQueue.
Mide throughput, latencia P50/P95/P99 y distribución por shard.
"""
import statistics
import threading
import time
import unittest
from core.dof_sharding import DOFShardManager
from core.dof_distributed_queue import DistributedMeshQueue, DistributedTask

MACHINES = ["machine-a", "machine-b", "machine-c", "machine-d", "machine-e"]
AGENTS   = ["architect", "researcher", "guardian", "verifier", "narrator", "devops"]
N_TASKS  = 1000
SHARDS   = 10


def make_queue(node_id="load-test"):
    sm = DOFShardManager(MACHINES, shard_count=SHARDS, replication_factor=3)
    return DistributedMeshQueue(node_id, sm), sm


class TestHyperionLoad(unittest.TestCase):

    def test_enqueue_1000_tasks(self):
        """Enqueue 1000 tareas y verifica que el sistema no pierde ninguna."""
        q, _ = make_queue("load-enqueue")
        t0 = time.perf_counter()
        for i in range(N_TASKS):
            q.enqueue(DistributedTask(
                task_id=f"load-{i}",
                shard_key=AGENTS[i % len(AGENTS)],
                prompt=f"task {i}",
                priority=i % 3,
            ))
        elapsed = time.perf_counter() - t0
        throughput = N_TASKS / elapsed
        print(f"\n  Enqueue: {throughput:,.0f} tasks/sec ({elapsed*1000:.1f}ms total)")
        self.assertGreater(throughput, 10_000, "Throughput mínimo 10K tasks/sec")
        self.assertEqual(q.qsize(), N_TASKS)

    def test_dequeue_all_no_loss(self):
        """Dequeue completo: ninguna tarea se pierde."""
        q, _ = make_queue("load-dequeue")
        for i in range(N_TASKS):
            q.enqueue(DistributedTask(
                task_id=f"drain-{i}",
                shard_key=AGENTS[i % len(AGENTS)],
                prompt=f"task {i}",
            ))
        recovered = 0
        t0 = time.perf_counter()
        while q.qsize() > 0:
            t = q.dequeue_any(timeout=0.001)
            if t:
                recovered += 1
        elapsed = time.perf_counter() - t0
        throughput = recovered / elapsed
        print(f"\n  Dequeue: {throughput:,.0f} tasks/sec | {recovered}/{N_TASKS} recovered")
        self.assertEqual(recovered, N_TASKS)
        self.assertGreater(throughput, 5_000)

    def test_6_agents_parallel(self):
        """6 agentes en threads paralelos — sin deadlocks, sin pérdida."""
        q, sm = make_queue("load-parallel")
        per_agent = N_TASKS // len(AGENTS)
        results = {a: 0 for a in AGENTS}
        errors  = []

        # Enqueue: cada tarea dirigida a un agente específico
        for i in range(N_TASKS):
            agent = AGENTS[i % len(AGENTS)]
            q.enqueue(DistributedTask(
                task_id=f"par-{i}",
                shard_key=agent,
                prompt=f"parallel task {i}",
                priority=i % 2,
            ))

        def agent_worker(agent_name):
            shard = sm.get_shard_for_key(agent_name)
            count = 0
            deadline = time.time() + 5.0  # 5s timeout
            while time.time() < deadline:
                try:
                    task = q.dequeue(shard.id, timeout=0.05)
                    if task:
                        count += 1
                except Exception as e:
                    errors.append(str(e))
            results[agent_name] = count

        threads = [threading.Thread(target=agent_worker, args=(a,)) for a in AGENTS]
        t0 = time.perf_counter()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        elapsed = time.perf_counter() - t0

        total = sum(results.values())
        throughput = total / elapsed
        print(f"\n  Parallel 6 agents: {throughput:,.0f} tasks/sec")
        print(f"  Distribución: { {a: results[a] for a in AGENTS} }")
        print(f"  Total procesado: {total}/{N_TASKS}")

        self.assertEqual(errors, [], f"Errores: {errors}")
        self.assertGreaterEqual(total, N_TASKS * 0.95, "Mínimo 95% procesado")

    def test_latency_percentiles(self):
        """Mide latencia P50/P95/P99 de enqueue+dequeue."""
        q, _ = make_queue("load-latency")
        latencies = []

        for i in range(200):
            t0 = time.perf_counter()
            q.enqueue(DistributedTask(
                task_id=f"lat-{i}",
                shard_key=AGENTS[i % len(AGENTS)],
                prompt=f"latency {i}",
            ))
            task = q.dequeue_any(timeout=0.01)
            if task:
                latencies.append((time.perf_counter() - t0) * 1_000_000)

        if latencies:
            s = sorted(latencies)
            p50 = statistics.median(s)
            p95 = s[int(len(s) * 0.95)]
            p99 = s[int(len(s) * 0.99)]
            print(f"\n  Latencia P50={p50:.1f}µs | P95={p95:.1f}µs | P99={p99:.1f}µs")
            self.assertLess(p99, 50_000, "P99 debe ser < 50ms")

    def test_shard_distribution(self):
        """Verifica distribución uniforme entre shards."""
        q, sm = make_queue("load-dist")
        for i in range(N_TASKS):
            q.enqueue(DistributedTask(
                task_id=f"dist-{i}",
                shard_key=f"agent-{i % 50}",  # 50 agentes distintos
                prompt=f"distribution {i}",
            ))
        status = q.status()
        per_shard = status.get("per_shard", {})
        counts = list(per_shard.values())
        if counts:
            avg = sum(counts) / len(counts)
            mx  = max(counts)
            imbalance = (mx - avg) / avg if avg > 0 else 0
            print(f"\n  Distribución shards: avg={avg:.0f}, max={mx}, imbalance={imbalance:.1%}")
            self.assertLess(imbalance, 1.0, "Imbalance < 100% (consistent hashing, 10 shards)")


class TestHyperionConcurrentWrite(unittest.TestCase):

    def test_concurrent_enqueue_no_corruption(self):
        """N threads escribiendo simultáneamente — sin corrupción."""
        q, _ = make_queue("load-concurrent")
        N_THREADS = 8
        PER_THREAD = 125  # 8 * 125 = 1000

        def writer(tid):
            for i in range(PER_THREAD):
                q.enqueue(DistributedTask(
                    task_id=f"t{tid}-{i}",
                    shard_key=AGENTS[tid % len(AGENTS)],
                    prompt=f"thread {tid} task {i}",
                ))

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(N_THREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        total = q.qsize()
        print(f"\n  Concurrent write: {total}/{N_THREADS * PER_THREAD} tasks")
        self.assertEqual(total, N_THREADS * PER_THREAD)


if __name__ == "__main__":
    unittest.main(verbosity=2)
