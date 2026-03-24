# DOF — Deterministic Observability Framework

> **v0.5.0** · Mesh Legion · Phase 9 Autonomous Scaling

[![Tests](https://img.shields.io/badge/tests-3115-brightgreen)](tests/)
[![Modules](https://img.shields.io/badge/core%20modules-100-blue)](core/)
[![Coverage](https://img.shields.io/badge/compliance-100%25-success)](docs/)
[![License](https://img.shields.io/badge/license-BSL--1.1-orange)](LICENSE)

Autonomous multi-LLM agent mesh that routes tasks across 8+ AI providers, enforces deterministic governance, and scales itself — at zero cloud cost during idle cycles.

---

## Architecture

```
                        ┌─────────────────────────────────┐
                        │        MeshOrchestrator          │  ← Phase 9 nervous system
                        │  route → circuit break → cost    │
                        └──────────────┬──────────────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              ▼                        ▼                        ▼
      MeshRouterV2              MeshAutoScaler           CostOptimizer
   (O(√n) routing)          (hysteresis scale)        (provider matrix)
              │                        │                        │
              └────────────────────────┼────────────────────────┘
                                       │
                             ┌─────────▼─────────┐
                             │      NodeMesh       │
                             │  filesystem inbox  │
                             └─────────┬──────────┘
              ┌──────────────┬─────────┘──────────┬────────────┐
              ▼              ▼                     ▼            ▼
      cerebras-llama   deepseek-coder       gemini-flash   local-qwen
      (868 tok/s)      ($0.27/M tok)        (free/web)     (free/local)
```

**Protocol**: Tasks are JSON files in `logs/mesh/inbox/{node_id}/*.json`. Any model joins by reading/writing this directory — no SDK required.

---

## Key Numbers (v0.5.0)

| Metric | Value |
|--------|-------|
| Core modules | **100** |
| Test files | **117** |
| Tests | **3,115** |
| Import errors | **0** |
| Security compliance | **100%** (5/5 gaps) |
| Providers | **8** (Cerebras, DeepSeek, SambaNova, NVIDIA, GLM-5, Gemini, Groq, local) |
| Security layers | **7** (MeshGuardian → Icarus → Cerberus → SecurityHierarchy → Governance → AST → Z3) |
| Formal proofs (Z3) | 8/8 PROVEN |

---

## Quick Start

```bash
# Install
pip install dof-sdk==0.5.0

# Run the mesh (all 8 providers)
python3 core/api_node_runner.py --nodes deepseek-coder cerebras-llama gemini-flash local-qwen --daemon

# Launch autonomous planner (scans repo every 60min, dispatches work)
python3 core/autonomous_planner.py --interval 60

# Live status dashboard
python3 scripts/mesh_health_dashboard.py --live

# Mesh HTTP bridge (REST API + browser dashboard on :8080)
python3 core/mesh_bridge.py --port 8080
```

---

## Core Modules

### Mesh Infrastructure
| Module | Purpose |
|--------|---------|
| `core/node_mesh.py` | NodeRegistry + MessageBus + MeshDaemon |
| `core/mesh_orchestrator.py` | Phase 9 central nervous system |
| `core/mesh_router_v2.py` | O(√n) intelligent routing |
| `core/mesh_bridge.py` | HTTP bridge + REST API |
| `core/mesh_consensus.py` | Raft consensus log |
| `core/mesh_load_balancer.py` | Round-robin / weighted / least-loaded |
| `core/mesh_dns_sd.py` | Service discovery (TTL-based) |
| `core/mesh_nat_punch.py` | NAT traversal for federation |
| `core/claude_commander.py` | SDK + Spawn + Team + Debate + Peers |
| `core/autonomous_daemon.py` | Perceive → Decide → Execute → Evaluate |
| `core/autonomous_planner.py` | Repo scanner, TODO dispatcher |
| `core/legion_orchestrator.py` | Multi-model Legion coordination |

### Scaling & Observability
| Module | Purpose |
|--------|---------|
| `core/mesh_auto_scaler.py` | Hysteresis-based scale up/down |
| `core/mesh_auto_provisioner.py` | Dynamic node provisioning |
| `core/mesh_metrics_collector.py` | Prometheus + JSONL telemetry |
| `core/mesh_cost_optimizer.py` | Provider cost matrix |
| `core/mesh_circuit_breaker.py` | Per-node CLOSED/OPEN/HALF_OPEN |
| `core/local_node_runner.py` | Ollama/MLX local runner |
| `core/api_node_runner.py` | Multi-provider cloud runner |

### Security (7-Layer Stack)
| Module | Purpose |
|--------|---------|
| `core/mesh_guardian.py` | Base message validator |
| `core/icarus.py` | Proactive threat hunter |
| `core/cerberus.py` | 3-headed guardian (syntax+semantics+policy) |
| `core/security_hierarchy.py` | L0→L4 orchestrator |
| `core/kms.py` | AES-256-GCM vault |
| `core/dlp.py` | 18-pattern DLP + entropy analysis |
| `core/honeypot.py` | 3 trap nodes, auto-block |
| `core/e2e_encryption.py` | NaCl box E2E for inbox delivery |
| `core/pqc_analyzer.py` | Post-quantum crypto assessment |
| `core/contract_scanner.py` | Solidity vulnerability scanner |

### Governance & Formal Verification
| Module | Purpose |
|--------|---------|
| `core/governance.py` | Constitution enforcer |
| `core/z3_verifier.py` | Z3 formal proofs (8/8 invariants) |
| `core/ast_verifier.py` | Static AST analysis |
| `core/z3_gate.py` | LLM output gate (APPROVED/REJECTED/TIMEOUT) |
| `core/trust_gateway.py` | Multi-layer trust evaluation |
| `core/audit_log.py` | SHA3-256 hash chain audit |

---

## Smart Routing

```python
from core.node_mesh import NodeMesh

mesh = NodeMesh()

# Classic routing
msg = mesh.send_message("commander", "deepseek-coder", "write a binary search")

# Smart routing — MeshRouterV2 picks optimal node based on latency + specialty + cost
msg = mesh.send_message("commander", "auto", "refactor this module",
                        route_task_type="code")
# → selected: cerebras-llama (868 tok/s, 0 active tasks)
```

---

## Autonomous Operations

```python
from core.mesh_orchestrator import MeshOrchestrator

orch = MeshOrchestrator()

# Orchestrate a single task
result = orch.orchestrate({"task_id": "t1", "type": "code", "content": "..."})
print(result.selected_node, result.circuit_state, result.success)

# Get full mesh status
status = orch.get_status()
# → {work_orders_processed, work_orders_completed, mesh, routing, scaling, ...}

# Evaluate scaling decision
decision = orch.evaluate_scaling()
# → ScalingDecision(action='hold', queue_depth=12, demand_score=0.24, ...)

# Run autonomous loop (non-blocking)
import threading
threading.Thread(target=orch.run, kwargs={"interval": 30}, daemon=True).start()
```

---

## Formal Verification

```bash
# Verify all Z3 state invariants
python3 -m dof verify-states
# → 8/8 PROVEN in ~110ms

# Verify hierarchy constraints
python3 -m dof verify-hierarchy
# → PROVEN (42 patterns) in ~5ms

# Full governance check
python3 -m dof health --json
```

---

## Security Compliance

| Gap | Severity | Status |
|-----|----------|--------|
| E2E Encryption | CRITICAL | ✅ NaCl box |
| NATS TLS 1.3 + mTLS | HIGH | ✅ Phase 3 |
| Key Management (KMS) | MEDIUM | ✅ AES-256-GCM |
| SHA3-256 Audit Chain | MEDIUM | ✅ Phase 3 |
| Data Loss Prevention | MEDIUM | ✅ 18 patterns + entropy |

DOF_MESH Security Score: **100%**

---

## Providers (Zero-Cost Tier)

| Provider | Speed | Cost | Best For |
|----------|-------|------|----------|
| Cerebras | 868 tok/s | Free | Fast inference |
| DeepSeek Coder | 120 tok/s | $0.27/M | Code generation |
| SambaNova | 200 tok/s | Free | Large context |
| NVIDIA NIM | 150 tok/s | Free tier | Complex reasoning |
| GLM-5 | 100 tok/s | Free | Multilingual |
| Gemini Flash | — | Free/web | Analysis |
| local-qwen | 60 tok/s | $0.00 | Sovereign compute |
| local-agi-m4max | 230 tok/s ANE | $0.00 | M4 Max local |

---

## Running Tests

```bash
python3 -m unittest discover -s . -p "test_*.py"
# Ran 3115 tests in ~23s
# FAILED (failures=3) ← 3 irresolvable generated contradictions, known
```

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## License

BSL-1.1 — Business Source License. See [LICENSE](LICENSE).

## Author

Juan Carlos Quiceno Vasquez — Medellín, Colombia
Building the first deterministic multi-model AGI mesh. Legion never sleeps.
