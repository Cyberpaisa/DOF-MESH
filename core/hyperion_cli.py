"""
hyperion_cli.py — CLI para DOF Mesh Hyperion.

Uso:
    python3 -m core.hyperion_cli status
    python3 -m core.hyperion_cli status --shards 5
    python3 -m core.hyperion_cli bench
    python3 -m core.hyperion_cli raft --shards 3
    python3 -m core.hyperion_cli http --host 0.0.0.0 --port 8765
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Module-level imports so unittest.mock.patch can target them
from core.dof_sharding import DOFShardManager, ConsistentHashRing
from core.dof_distributed_queue import DistributedMeshQueue, DistributedTask
from core.hyperion_http import HyperionHTTPServer


def cmd_status(args):
    """Mostrar estado completo del mesh Hyperion."""
    from core.dof_sharding import DOFShardManager
    from core.dof_distributed_queue import DistributedMeshQueue

    machines = args.machines.split(",")
    sm = DOFShardManager(machines, shard_count=args.shards, replication_factor=3)
    q  = DistributedMeshQueue("cli-status", sm)

    s = q.status()
    print("=" * 56)
    print("  DOF MESH HYPERION — STATUS")
    print("=" * 56)
    print(f"  Nodo:        {s['node_id']}")
    print(f"  Shards:      {s['shards']}")
    print(f"  En cola:     {s['total_queued']}")
    print(f"  Encolados:   {s['enqueued_total']}")
    print(f"  Procesados:  {s['dequeued_total']}")
    print(f"  WAL activo:  {s['wal']}")
    print()
    print("  Distribución por shard:")
    for sid, count in s.get("per_shard", {}).items():
        bar = "█" * min(count, 40)
        print(f"    shard-{sid:02d}: {count:5d} {bar}")
    print("=" * 56)


def cmd_raft(args):
    """Arrancar cluster Raft demo y mostrar elección."""
    from core.dof_raft_shard import RaftShardManager

    machines = args.machines.split(",")
    print(f"Arrancando RaftShardManager: {args.shards} shards × 3 nodos Raft...")
    rsm = RaftShardManager(machines, shard_count=args.shards, raft_nodes_per_shard=3)
    rsm.start()

    print("Esperando elecciones...")
    ok = rsm.wait_all_leaders(timeout=5.0)
    s  = rsm.status()

    print("=" * 56)
    print("  RAFT CONSENSUS — RESULTADO")
    print("=" * 56)
    print(f"  Shards:          {s['shard_count']}")
    print(f"  Líderes electos: {s['leaders_elected']}/{s['shard_count']}")
    print(f"  Nodos Raft:      {s['raft_nodes_total']}")
    print()
    for sid, ss in s["shards"].items():
        status_icon = "✅" if ss["leader"] else "⚠ "
        print(f"  Shard {sid}: {status_icon} leader={ss['leader']} term={ss['term']}")
    print("=" * 56)
    print(f"  SLA: {'✅ TODOS LOS SHARDS TIENEN LÍDER' if ok else '⚠  ALGUNOS SHARDS SIN LÍDER'}")
    print("=" * 56)

    rsm.stop()


def cmd_bench(args):
    """Benchmark rápido del stack."""
    from core.dof_sharding import DOFShardManager, ConsistentHashRing
    from core.dof_distributed_queue import DistributedMeshQueue, DistributedTask
    import statistics

    machines = args.machines.split(",")
    N = args.tasks

    print(f"Benchmark: {N} tareas | {args.shards} shards | {len(machines)} máquinas")
    print("─" * 56)

    # Ring
    ring = ConsistentHashRing(replication_factor=3)
    for m in machines:
        ring.add_node(m)
    t0 = time.perf_counter()
    for i in range(N):
        ring.get_node(f"task-{i}")
    ring_ms = (time.perf_counter() - t0) * 1000
    print(f"  Ring:    {N/(ring_ms/1000):>10,.0f} lookups/sec  ({ring_ms:.1f}ms)")

    # Queue enqueue
    sm = DOFShardManager(machines, shard_count=args.shards)
    q  = DistributedMeshQueue("bench-cli", sm)
    t0 = time.perf_counter()
    for i in range(N):
        q.enqueue(DistributedTask(f"t{i}", f"agent-{i%10}", f"task {i}"))
    enq_ms = (time.perf_counter() - t0) * 1000
    print(f"  Enqueue: {N/(enq_ms/1000):>10,.0f} tasks/sec    ({enq_ms:.1f}ms)")

    # Queue dequeue + latency
    lats = []
    t0 = time.perf_counter()
    while q.qsize() > 0:
        ts = time.perf_counter()
        t  = q.dequeue_any(timeout=0.001)
        if t:
            lats.append((time.perf_counter() - ts) * 1e6)
    deq_ms = (time.perf_counter() - t0) * 1000
    print(f"  Dequeue: {len(lats)/(deq_ms/1000):>10,.0f} tasks/sec    ({deq_ms:.1f}ms)")

    if lats:
        s = sorted(lats)
        print(f"  P50={statistics.median(s):.1f}µs  P95={s[int(len(s)*0.95)]:.1f}µs  P99={s[int(len(s)*0.99)]:.1f}µs")
    print("─" * 56)
    print("  ✅ Benchmark completado")


def cmd_http(args):
    """Arrancar el HTTP Bridge."""
    from core.hyperion_http import HyperionHTTPServer
    srv = HyperionHTTPServer(
        host=args.host,
        port=args.port,
        machines=args.machines.split(","),
        shard_count=args.shards,
    )
    srv.run()


def main():
    parser = argparse.ArgumentParser(
        description="DOF Mesh Hyperion CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Comandos:
  status   — estado del queue y shards
  raft     — demo de leader election Raft
  bench    — benchmark del stack
  http     — arrancar HTTP Bridge
        """,
    )
    parser.add_argument(
        "--machines",
        default="machine-a,machine-b,machine-c,machine-d,machine-e",
        help="Máquinas del cluster (csv)",
    )
    parser.add_argument("--shards", type=int, default=5)

    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("status", help="Estado del mesh")
    sub.add_parser("raft", help="Demo Raft consensus")

    bench_p = sub.add_parser("bench", help="Benchmark")
    bench_p.add_argument("--tasks", type=int, default=10_000)

    http_p = sub.add_parser("http", help="HTTP Bridge")
    http_p.add_argument("--host", default="0.0.0.0")
    http_p.add_argument("--port", type=int, default=8765)

    args = parser.parse_args()

    if args.cmd == "status":
        cmd_status(args)
    elif args.cmd == "raft":
        cmd_raft(args)
    elif args.cmd == "bench":
        cmd_bench(args)
    elif args.cmd == "http":
        cmd_http(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
