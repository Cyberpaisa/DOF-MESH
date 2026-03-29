"""
DOF Mesh — Legion Orchestrator v2.0 (Mano Derecha)
====================================================
El cerebro autónomo del DOF Mesh. Corre para siempre.
Aprende, evoluciona, y mantiene toda la legión trabajando.

Capacidades:
    ✓ Despacha tareas a 10 providers API en paralelo
    ✓ Memoria persistente — aprende de cada ciclo
    ✓ Modo evolución — mejora su backlog automáticamente
    ✓ Skills integradas — KMS, DLP, Honeypot, Federation, Firewall
    ✓ Fallback inteligente — si un provider falla, usa el siguiente
    ✓ Rate limiting awareness — espera y reintenta
    ✓ Auto-genera Phase N+1 cuando termina Phase N
    ✓ Métricas en tiempo real — velocidad, éxito, costo

Usage:
    python3 core/legion_orchestrator.py --run
    python3 core/legion_orchestrator.py --status
    python3 core/legion_orchestrator.py --memory
"""

import json
import logging
import os
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("legion.orchestrator")

# ═══════════════════════════════════════════════
# PATHS
# ═══════════════════════════════════════════════
BASE       = Path(__file__).parent.parent
MESH       = BASE / "logs/mesh"
INBOX      = MESH / "inbox"
ORCH_LOG   = MESH / "orchestrator.jsonl"
MEMORY_FILE = MESH / "orchestrator_memory.json"
LAST_READ  = MESH / "orchestrator_last_read.txt"

for p in [MESH, INBOX / "commander"]:
    p.mkdir(parents=True, exist_ok=True)

CYCLE_SEC = 25   # faster than before

# ═══════════════════════════════════════════════
# SKILLS REGISTRY — todas las capacidades del mesh
# ═══════════════════════════════════════════════

SKILLS = {
    "security":    ["core/honeypot.py", "core/mesh_firewall.py", "core/kms.py", "core/dlp.py"],
    "federation":  ["core/mesh_federation.py", "core/mesh_firewall.py"],
    "mesh":        ["core/node_mesh.py", "core/mesh_router.py", "core/mesh_guardian.py"],
    "local_agi":   ["core/local_model_node.py"],
    "remote":      ["core/remote_node_adapter.py"],
    "governance":  ["core/governance.py", "core/z3_gate.py", "core/supervisor.py"],
    "observability": ["core/observability.py", "core/audit_log.py"],
    "session":     ["core/session_worker.py"],
}

# ═══════════════════════════════════════════════
# PHASE 7 TASK BACKLOG
# ═══════════════════════════════════════════════

INITIAL_BACKLOG = [
    {"id": "P7-01", "priority": 10, "retries": 0, "done": False, "assigned": False,
     "title": "Write tests/test_mesh_firewall.py",
     "description": "30+ unittest tests para core/mesh_firewall.py. Clases: IPBlocklist, RateLimiter, ConnectionThrottle, MeshFirewall. No network. Mock file I/O. Return complete Python test file."},

    {"id": "P7-02", "priority": 9, "retries": 0, "done": False, "assigned": False,
     "title": "Write examples/federation_demo.py",
     "description": "Demo de dos instancias FederationManager en localhost. Puertos 7892/7893. Muestra start(), add_seed(), send_to_peer(), broadcast_to_federation(). 80+ líneas. Ejecutable directamente."},

    {"id": "P7-03", "priority": 9, "retries": 0, "done": False, "assigned": False,
     "title": "Write core/mesh_stun.py — NAT traversal",
     "description": "STUN client. STUNClient.discover_public_endpoint() -> (ip, port). Usa stun.l.google.com:19302. NATType enum (OPEN/RESTRICTED/SYMMETRIC). Fallback si STUN inalcanzable. Singleton get_stun_client()."},

    {"id": "P7-04", "priority": 8, "retries": 0, "done": False, "assigned": False,
     "title": "Write scripts/bench_mesh.py",
     "description": "Benchmark de rendimiento del mesh. Mide: throughput (msgs/seg), overhead encryption (ms), latencia broadcast. 1000 iteraciones. Solo stdlib. Imprime tabla de resultados."},

    {"id": "P7-05", "priority": 8, "retries": 0, "done": False, "assigned": False,
     "title": "Write core/mesh_tunnel.py — encrypted tunnel",
     "description": "Túnel cifrado Phase 7. TunnelManager: create_tunnel(peer_host, peer_port), send(data), recv(). NaCl SecretBox encryption. Wraps socket. Singleton get_tunnel_manager()."},

    {"id": "P7-06", "priority": 7, "retries": 0, "done": False, "assigned": False,
     "title": "Write docs/03_book/BOOK_CH15_INTERNET_FEDERATION.md",
     "description": "Cap 15 del libro DOF. 400+ líneas. Secciones: Problema NAT/firewalls, STUN/TURN, UDP hole punching, túneles cifrados, DNS-SD, topología, seguridad escala internet, roadmap, business value."},

    {"id": "P7-07", "priority": 7, "retries": 0, "done": False, "assigned": False,
     "title": "Write core/federation_seed.py",
     "description": "Seed node server para descubrimiento internet. SeedServer: HTTP puerto 7893, registra peers, retorna lista. SeedClient: register(my_id, host, port), get_peers(). Singleton."},

    {"id": "P7-08", "priority": 6, "retries": 0, "done": False, "assigned": False,
     "title": "Write core/mesh_monitor.py",
     "description": "Monitor en tiempo real. MeshMonitor: salud de nodos, tasas de mensaje, tasas de error. Alerta cuando nodo offline o error > 10%. Escribe a logs/mesh/monitor.jsonl. CLI --dashboard."},

    {"id": "P7-09", "priority": 6, "retries": 0, "done": False, "assigned": False,
     "title": "Write tests/test_integration_phase7.py",
     "description": "Tests integración end-to-end Phase 7. mesh_firewall + mesh_federation trabajando juntos. Firewall bloquea atacante antes de que federation procese. 20+ tests."},

    {"id": "P7-10", "priority": 5, "retries": 0, "done": False, "assigned": False,
     "title": "Add round-robin fallback to RemoteNodeAdapter",
     "description": "Modifica core/remote_node_adapter.py dispatch() para round-robin: si provider falla, intenta siguiente. Añade _fallback_chain dict. Retorna método dispatch() modificado."},

    {"id": "P7-11", "priority": 5, "retries": 0, "done": False, "assigned": False,
     "title": "Write core/mesh_health.py",
     "description": "Health checker para todos los nodos. MeshHealth.check_all() -> Dict[node_id, status]. Verifica providers API, local Ollama, federation bridge. CLI: --check imprime tabla. Integra con mesh_monitor."},

    {"id": "P7-12", "priority": 4, "retries": 0, "done": True, "assigned": True,
     "title": "Implement DeepSeek node in remote_node_adapter.py",
     "description": "COMPLETED — DeepSeek integrated with $0.27/1M tokens."},

    # NEW Phase 7 tasks — use DeepSeek for heavy work
    {"id": "P7-13", "priority": 9, "retries": 0, "done": False, "assigned": False,
     "title": "Write core/mesh_stun.py — NAT traversal",
     "description": "STUN client for Phase 7 internet federation. Class STUNClient with discover_public_endpoint()->(ip,port). Use stun.l.google.com:19302 via UDP. NATType enum: OPEN/RESTRICTED/SYMMETRIC/BLOCKED. Cache result 60s. Singleton get_stun_client(). ~120 lines, stdlib only."},

    {"id": "P7-14", "priority": 8, "retries": 0, "done": False, "assigned": False,
     "title": "Write core/mesh_tunnel.py — encrypted WireGuard-style tunnel",
     "description": "Encrypted mesh tunnel. TunnelSession: encrypt/decrypt with AES-GCM (cryptography lib). TunnelManager: open_tunnel(peer_host, peer_port)->TunnelSession, close_tunnel(session_id). Uses HMAC-SHA256 for key derivation. Singleton get_tunnel_manager(). 150+ lines."},

    {"id": "P7-15", "priority": 8, "retries": 0, "done": False, "assigned": False,
     "title": "Write core/federation_seed.py — seed server for internet discovery",
     "description": "Seed node for internet-scale federation. SeedServer: HTTP on port 7893, endpoint POST /register (node_id, host, port), GET /peers returns list. SeedClient: register(my_id, host, port), get_peers()->list. TTL 5min per registration. Singleton. ~120 lines."},

    {"id": "P7-16", "priority": 7, "retries": 0, "done": False, "assigned": False,
     "title": "Write tests/test_mesh_stun.py",
     "description": "20+ unittest tests for core/mesh_stun.py. Mock UDP socket. Test: discover_public_endpoint returns (ip, port), NATType detection, cache works, timeout handled gracefully, fallback when STUN unreachable. No real network calls."},

    {"id": "P7-17", "priority": 7, "retries": 0, "done": False, "assigned": False,
     "title": "Write tests/test_mesh_tunnel.py",
     "description": "20+ unittest tests for core/mesh_tunnel.py. Test: encrypt/decrypt roundtrip, wrong key fails, open_tunnel creates session, close_tunnel removes it, concurrent sessions isolated, HMAC key derivation deterministic."},

    {"id": "P7-18", "priority": 6, "retries": 0, "done": False, "assigned": False,
     "title": "Write examples/deepseek_mesh_demo.py",
     "description": "Demo showing DeepSeek as a mesh node. Sends 3 tasks in parallel to deepseek-coder: code review, documentation, test generation. Uses RemoteNodeAdapter. Prints results side-by-side. Shows cost estimate at the end ($0.27/1M tokens)."},
]

# ═══════════════════════════════════════════════
# NODE STATE
# ═══════════════════════════════════════════════

@dataclass
class NodePerf:
    node_id:      str
    tasks_done:   int   = 0
    tasks_failed: int   = 0
    avg_time_s:   float = 0.0
    last_active:  float = field(default_factory=time.time)
    busy:         bool  = False
    current_task: str   = ""
    errors:       List  = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        total = self.tasks_done + self.tasks_failed
        return self.tasks_done / total if total > 0 else 1.0

    def record_result(self, success: bool, duration: float):
        if success:
            self.tasks_done += 1
            n = self.tasks_done
            self.avg_time_s = (self.avg_time_s * (n-1) + duration) / n
        else:
            self.tasks_failed += 1
        self.last_active = time.time()
        self.busy = False
        self.current_task = ""


# ═══════════════════════════════════════════════
# MEMORY — aprendizaje persistente
# ═══════════════════════════════════════════════

class OrchestratorMemory:
    """
    Memoria persistente entre reinicios.
    Aprende qué providers son rápidos, qué tareas fallan, qué patrones funcionan.
    """

    def __init__(self, path: Path = MEMORY_FILE):
        self._path = path
        self._data = self._load()

    def _load(self) -> dict:
        if self._path.exists():
            try:
                return json.loads(self._path.read_text())
            except Exception:
                pass
        return {
            "cycles_total": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "provider_stats": {},
            "failed_tasks": [],
            "learned_patterns": [],
            "phase": 7,
            "evolution_log": [],
        }

    def save(self):
        self._path.write_text(json.dumps(self._data, indent=2))

    def record_cycle(self, completed: int, failed: int):
        self._data["cycles_total"] += 1
        self._data["tasks_completed"] += completed
        self._data["tasks_failed"] += failed

    def record_provider(self, node_id: str, success: bool, duration: float):
        stats = self._data["provider_stats"].setdefault(node_id, {
            "done": 0, "fail": 0, "avg_s": 0.0
        })
        if success:
            stats["done"] += 1
            n = stats["done"]
            stats["avg_s"] = round((stats["avg_s"] * (n-1) + duration) / n, 2)
        else:
            stats["fail"] += 1

    def best_providers(self) -> List[str]:
        """Returns providers sorted by success rate."""
        stats = self._data["provider_stats"]
        def score(nid):
            s = stats.get(nid, {})
            done = s.get("done", 0)
            fail = s.get("fail", 0)
            total = done + fail
            rate = done / total if total > 0 else 0.5
            speed = 1 / max(s.get("avg_s", 10), 0.1)
            return rate * 0.7 + speed * 0.3
        return sorted(stats.keys(), key=score, reverse=True)

    def evolve(self, insight: str):
        """Record an evolutionary insight."""
        self._data["evolution_log"].append({
            "ts": time.time(),
            "insight": insight,
            "cycle": self._data["cycles_total"]
        })
        if len(self._data["evolution_log"]) > 100:
            self._data["evolution_log"] = self._data["evolution_log"][-100:]
        logger.info(f"EVOLUTION: {insight}")

    def get_phase(self) -> int:
        return self._data.get("phase", 7)

    def set_phase(self, phase: int):
        self._data["phase"] = phase

    def get_stats(self) -> dict:
        return {
            "cycles": self._data["cycles_total"],
            "completed": self._data["tasks_completed"],
            "failed": self._data["tasks_failed"],
            "phase": self._data["phase"],
            "evolutions": len(self._data["evolution_log"]),
            "best_providers": self.best_providers()[:3],
        }


# ═══════════════════════════════════════════════
# LEGION ORCHESTRATOR v2
# ═══════════════════════════════════════════════

class LegionOrchestrator:

    _instance = None
    _class_lock = __import__("threading").Lock()

    def __new__(cls):
        if getattr(cls, '_instance', None) is None:
            with cls._class_lock:
                if getattr(cls, '_instance', None) is None:
                    inst = super().__new__(cls)
                    cls._instance = inst
        return cls._instance

    API_NODES = [
        "gpt-legion", "gemini-web", "qwen-coder-480b",
        "sambanova-llama", "kimi-web", "minimax",
        "deepseek-coder", "deepseek-r1",   # BEST VALUE — $0.27/1M tokens
    ]

    # Fallback chains: si falla el primero, usa el siguiente
    FALLBACK = {
        "gemini-web":      "deepseek-coder",   # Cerebras 429 → DeepSeek
        "qwen-coder-480b": "deepseek-coder",   # Cerebras → DeepSeek (code)
        "kimi-web":        "deepseek-coder",   # NVIDIA → DeepSeek
        "sambanova-llama":  "deepseek-r1",     # SambaNova → DeepSeek R1
        "minimax":         "deepseek-coder",
        "gpt-legion":      "deepseek-coder",
        "deepseek-coder":  "gpt-legion",       # DeepSeek fallback → NVIDIA
        "deepseek-r1":     "sambanova-llama",
    }

    def __init__(self):
        self._backlog  = [dict(t) for t in INITIAL_BACKLOG]
        self._nodes    = {n: NodePerf(node_id=n) for n in self.API_NODES}
        self._memory   = OrchestratorMemory()
        self._lock     = threading.Lock()
        self._cycle    = 0
        self._running  = False
        self._adapter  = None
        self._rate_wait: Dict[str, float] = {}  # node → retry_after

        # Load previously completed tasks from memory
        done_ids = set(self._memory._data.get("completed_task_ids", []))
        for t in self._backlog:
            if t["id"] in done_ids:
                t["done"] = True

    def _adapter_(self):
        if self._adapter is None:
            from core.remote_node_adapter import RemoteNodeAdapter
            self._adapter = RemoteNodeAdapter()
        return self._adapter

    # ──────────────────────────────────────────
    # MAIN LOOP
    # ──────────────────────────────────────────

    def run(self):
        self._running = True
        mem = self._memory.get_stats()
        print(f"""
╔══════════════════════════════════════════════════╗
║   LEGION ORCHESTRATOR v2.0 — MANO DERECHA        ║
║   Phase {mem['phase']} | {mem['cycles']} cycles previos | {mem['completed']} tareas completadas  ║
╚══════════════════════════════════════════════════╝
Skills: {list(SKILLS.keys())}
Nodes:  {self.API_NODES}
Cycle:  every {CYCLE_SEC}s
""")
        while self._running:
            try:
                self._cycle += 1
                self._run_cycle()
                time.sleep(CYCLE_SEC)
            except KeyboardInterrupt:
                print("\nOrchestrator stopped.")
                self._memory.save()
                break
            except Exception as e:
                logger.error(f"Cycle error: {e}")
                time.sleep(5)

    def _run_cycle(self):
        t0 = time.time()
        print(f"\n{'─'*55}")
        print(f" CYCLE {self._cycle} | {time.strftime('%H:%M:%S')} | Phase {self._memory.get_phase()}")

        # 1. Read completions
        completions = self._read_completions()
        if completions:
            for c in completions:
                print(f"  ✓ {c['node']:18s} — {c['task'][:45]}")
            self._memory.record_cycle(len(completions), 0)
            self._memory.evolve(f"Cycle {self._cycle}: {len(completions)} tasks done by {[c['node'] for c in completions]}")

        # 2. Check for rate-limited nodes (reset after 60s)
        now = time.time()
        for node in list(self._rate_wait.keys()):
            if now > self._rate_wait[node]:
                del self._rate_wait[node]
                print(f"  ↺ {node} rate limit cleared")

        # 3. Assign + dispatch
        assignments = self._assign()
        if assignments:
            print(f"  → Dispatching {len(assignments)} tasks...")
            self._dispatch(assignments)
        else:
            done  = sum(1 for t in self._backlog if t["done"])
            total = len(self._backlog)
            busy  = sum(1 for n in self._nodes.values() if n.busy)
            print(f"  ↻ {done}/{total} done | {busy} busy | waiting...")

        # 4. Evolution check
        self._evolve()

        # 5. Save memory
        self._memory.save()

        dt = time.time() - t0
        done = sum(1 for t in self._backlog if t["done"])
        print(f"  ⏱  {dt:.1f}s | {done}/{len(self._backlog)} tasks done")

    # ──────────────────────────────────────────
    # COMPLETIONS
    # ──────────────────────────────────────────

    def _read_completions(self) -> List[dict]:
        found = []
        inbox = INBOX / "commander"
        last_ts = float(LAST_READ.read_text()) if LAST_READ.exists() else 0.0

        for f in sorted(inbox.glob("*.json"), key=lambda x: x.stat().st_mtime):
            if f.stat().st_mtime <= last_ts:
                continue
            try:
                d = json.loads(f.read_text())
                from_node = d.get("from_node", "")
                is_completion = (
                    "DONE" in f.name or "RESULT" in f.name or "ORCH-RESULT" in f.name or
                    d.get("msg_type") in ("task_complete", "phase6_deliverable") or
                    d.get("status") == "COMPLETED"
                )
                if is_completion and from_node in self._nodes:
                    # Mark matching task as done
                    task_id = d.get("task_id", "")
                    for t in self._backlog:
                        if t["id"] == task_id or t["title"] in d.get("task", ""):
                            t["done"] = True
                            break
                    self._nodes[from_node].busy = False
                    self._nodes[from_node].current_task = ""
                    found.append({"node": from_node, "task": d.get("task", f.name[:40])})
                    # Learn provider performance
                    self._memory.record_provider(from_node, True, d.get("duration_s", 5.0))
            except Exception:
                pass

        LAST_READ.write_text(str(time.time()))
        return found

    # ──────────────────────────────────────────
    # ASSIGNMENT
    # ──────────────────────────────────────────

    def _assign(self) -> List[Tuple[str, dict]]:
        assignments = []
        with self._lock:
            # Sort nodes: best performers first (from memory)
            best = self._memory.best_providers()
            node_order = best + [n for n in self.API_NODES if n not in best]

            free = [n for n in node_order
                    if n in self._nodes
                    and not self._nodes[n].busy
                    and n not in self._rate_wait]

            pending = sorted(
                [t for t in self._backlog if not t["assigned"] and not t["done"]],
                key=lambda t: -t["priority"]
            )

            for node, task in zip(free, pending):
                task["assigned"] = True
                self._nodes[node].busy = True
                self._nodes[node].current_task = task["id"]
                assignments.append((node, task))

        return assignments

    # ──────────────────────────────────────────
    # DISPATCH — parallel, with fallback
    # ──────────────────────────────────────────

    def _dispatch(self, assignments: List[Tuple[str, dict]]):
        adapter = self._adapter_()
        threads = []

        def run_one(node_id: str, task: dict):
            order = {
                "msg_id": f"ORCH2-{task['id']}-{node_id[:5]}",
                "task": {
                    "title":       task["title"],
                    "description": task["description"],
                    "timeline":    "NOW"
                }
            }
            t0 = time.time()
            r = adapter.dispatch(node_id, order)
            dt = round(time.time() - t0, 1)

            with self._lock:
                if r and r.status == "COMPLETED":
                    task["done"] = True
                    self._nodes[node_id].record_result(True, dt)
                    self._memory.record_provider(node_id, True, dt)

                    # Save result
                    out = INBOX / "commander" / f"ORCH2-{task['id']}-{node_id}.json"
                    out.write_text(json.dumps({
                        "from_node": node_id, "task_id": task["id"],
                        "task": task["title"], "status": "COMPLETED",
                        "response": r.response_text[:6000], "duration_s": dt,
                        "timestamp": time.time(),
                    }, indent=2))
                    print(f"    ✓ {node_id:20s} {task['id']} ({dt}s)")

                else:
                    # Check if rate limited
                    err = (r.error if r else "") or ""
                    is_rate = "429" in err or "rate" in err.lower() or "queue" in err.lower() or "traffic" in err.lower()

                    if is_rate:
                        self._rate_wait[node_id] = time.time() + 60
                        print(f"    ⏳ {node_id:20s} rate limited — wait 60s")
                    else:
                        task["retries"] = task.get("retries", 0) + 1
                        print(f"    ✗ {node_id:20s} {task['id']} fail ({err[:40]})")

                    # Fallback: try another node
                    fallback = self.FALLBACK.get(node_id)
                    if fallback and not self._nodes.get(fallback, NodePerf("x")).busy and fallback not in self._rate_wait:
                        task["assigned"] = False  # will be picked up next cycle
                        self._memory.evolve(f"Fallback {node_id}→{fallback} for {task['id']}")

                    self._nodes[node_id].record_result(False, dt)
                    self._memory.record_provider(node_id, False, dt)

        for node_id, task in assignments:
            t = threading.Thread(target=run_one, args=(node_id, task), daemon=True)
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=90)

    # ──────────────────────────────────────────
    # EVOLUTION — auto-mejora
    # ──────────────────────────────────────────

    def _evolve(self):
        done  = sum(1 for t in self._backlog if t["done"])
        total = len(self._backlog)

        # Phase complete → generate next phase
        if done == total:
            next_phase = self._memory.get_phase() + 1
            self._memory.set_phase(next_phase)
            new_tasks = self._generate_phase(next_phase)
            self._backlog = new_tasks
            self._memory.evolve(f"Phase {next_phase-1} COMPLETE → Phase {next_phase} generated ({len(new_tasks)} tasks)")
            print(f"\n  🚀 PHASE {next_phase-1} DONE → Phase {next_phase} STARTED ({len(new_tasks)} tasks)")
            return

        # Learn from failures: demote consistently failing tasks
        for t in self._backlog:
            if t.get("retries", 0) >= 3 and not t["done"]:
                t["priority"] = max(1, t["priority"] - 1)
                self._memory.evolve(f"Demoted {t['id']} (3+ retries) to priority {t['priority']}")

        # Learn from provider performance
        best = self._memory.best_providers()
        if best:
            top = best[0]
            self._memory.evolve(f"Best provider this session: {top}")

    def _generate_phase(self, phase: int) -> List[dict]:
        """Auto-generate tasks for the next phase."""
        phase_tasks = {
            8: [
                {"id": f"P8-01", "priority": 10, "retries": 0, "done": False, "assigned": False,
                 "title": "Implement mesh_tunnel.py full WireGuard-style",
                 "description": "Full encrypted P2P tunnel. AES-256-GCM. Key exchange via X25519. Handshake protocol. Routing table. CLI --connect HOST PORT."},
                {"id": f"P8-02", "priority": 9, "retries": 0, "done": False, "assigned": False,
                 "title": "Deploy federation_seed.py as HTTP server",
                 "description": "Global seed node. REST API: POST /register, GET /peers, DELETE /leave. Persistence to JSON. Docker-ready Dockerfile."},
                {"id": f"P8-03", "priority": 8, "retries": 0, "done": False, "assigned": False,
                 "title": "Write BOOK_CH16_PHASE8_TUNNEL.md",
                 "description": "Chapter 16: encrypted tunnels and global mesh. 400+ lines. WireGuard comparison, implementation, deployment."},
                {"id": f"P8-04", "priority": 7, "retries": 0, "done": False, "assigned": False,
                 "title": "Write tests/test_mesh_tunnel.py",
                 "description": "30+ tests for mesh_tunnel.py. Mock socket. Test encryption/decryption, handshake, error handling."},
            ],
            9: [
                {"id": "P9-01", "priority": 10, "retries": 0, "done": False, "assigned": False,
                 "title": "Build DOF Mesh web dashboard",
                 "description": "Single-page HTML dashboard showing mesh topology, node status, message rates, security alerts. Pure HTML+JS+CSS. No dependencies. Reads logs/mesh/*.json"},
                {"id": "P9-02", "priority": 9, "retries": 0, "done": False, "assigned": False,
                 "title": "Implement mesh_consensus.py",
                 "description": "Byzantine fault tolerant consensus for federated mesh. Nodes vote on shared state. Simple BFT protocol. Works with 3+ nodes."},
            ]
        }
        return phase_tasks.get(phase, [
            {"id": f"P{phase}-01", "priority": 10, "retries": 0, "done": False, "assigned": False,
             "title": f"Phase {phase} — Auto-generated research task",
             "description": f"Research and implement the next evolution of DOF Mesh for Phase {phase}. Analyze current state and propose improvements."}
        ])

    # ──────────────────────────────────────────
    # STATUS
    # ──────────────────────────────────────────

    def get_status(self) -> dict:
        done  = sum(1 for t in self._backlog if t["done"])
        total = len(self._backlog)
        return {
            "cycle": self._cycle,
            "running": self._running,
            "phase": self._memory.get_phase(),
            "progress": f"{done}/{total}",
            "memory": self._memory.get_stats(),
            "nodes": {n: {"busy": s.busy, "done": s.tasks_done, "fail": s.tasks_failed,
                          "rate": round(s.success_rate, 2), "avg_s": round(s.avg_time_s, 1)}
                      for n, s in self._nodes.items()},
            "backlog": [{"id": t["id"], "title": t["title"][:50], "done": t["done"],
                         "priority": t["priority"]} for t in self._backlog],
            "rate_limited": list(self._rate_wait.keys()),
        }


# ═══════════════════════════════════════════════
# SINGLETON + CLI
# ═══════════════════════════════════════════════

_orch: Optional[LegionOrchestrator] = None

def get_orchestrator() -> LegionOrchestrator:
    global _orch
    if _orch is None:
        _orch = LegionOrchestrator()
    return _orch


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.WARNING,
                        format="%(asctime)s %(message)s")

    orch = get_orchestrator()

    if "--status" in sys.argv:
        print(json.dumps(orch.get_status(), indent=2))
    elif "--memory" in sys.argv:
        print(json.dumps(orch._memory._data, indent=2))
    elif "--run" in sys.argv:
        orch.run()
    else:
        # Single test cycle
        print("Running single cycle...")
        orch._run_cycle()
        print(json.dumps(orch.get_status(), indent=2))
