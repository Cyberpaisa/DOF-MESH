# DOF Mesh Architecture & Technical Specifications

This document contains the detailed technical specifications, module maps, and security protocols for the **Deterministic Observability Framework (DOF)**. For a quick start and installation, please refer to the [README.md](../README.md).

---

## Architecture Detail

```
                        ┌─────────────────────────────────┐
                        │        MeshOrchestrator          │
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
```

---

## Core Modules

### Mesh Infrastructure
| Module | Purpose |
|--------|---------|
| `core/node_mesh.py` | NodeRegistry + MessageBus + MeshDaemon |
| `core/mesh_orchestrator.py` | Central nervous system |
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

## Security Compliance

| Gap | Severity | Status |
|-----|----------|--------|
| E2E Encryption | CRITICAL | ✅ NaCl box |
| NATS TLS 1.3 + mTLS | HIGH | ✅ Phase 3 |
| Key Management (KMS) | MEDIUM | ✅ AES-256-GCM |
| SHA3-256 Audit Chain | MEDIUM | ✅ Phase 3 |
| Data Loss Prevention | MEDIUM | ✅ 18 patterns + entropy |

---

## Key Performance Indicators (v0.5.0)

| Metric | Value |
|--------|-------|
| Core modules | **100** |
| Security layers | **7** |
| Formal proofs (Z3) | 8/8 PROVEN |
| Security compliance | **100%** |
| Multi-provider support | **8** |

---

## Author & Context

**Juan Carlos Quiceno Vasquez — Medellín, Colombia**
The DOF Mesh is a sovereign infrastructure for deterministic AI operations.
*Phase 5 (Autonomous Operations) is now standard.*
