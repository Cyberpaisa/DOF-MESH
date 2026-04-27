# DOF-MESH v0.8.0 — Complete System Architecture

> Deterministic Observability Framework — Autonomous governance system for AI agents
> Cyber Paisa — Enigma Group — 2026

---

## System Numbers

> Última auditoría: 2026-04-16 (sesión 12 — Deuda Técnica Cero)

| Metric | Value |
|---|---|
| Core modules | 173 |
| Test files | 215 |
| Total tests | 4,800 (discovered via unittest, 0 load errors) |
| Lines of code | 65,360 (core + dof) |
| Documentation | 223 .md files |
| Interfaces | 4 (Dashboard, Telegram, Voice, Realtime Voice) |
| Scripts | 79 |
| CI Workflows | 4 (Tests, DOF CI, Z3 Verify, Lint) |
| SDK | dof-sdk 0.8.0 (PyPI) |
| On-chain | 30+ attestations across 9 chains |
| CrewAI Agents | 20 |
| Mesh LLM Nodes | 11+ |
| Governance layers | 7 |

---

## Layered Architecture

```
+================================================================+
|                    INTERFACES (entry)                           |
|  CLI (main.py)  | Telegram Bot | Dashboard | Voice | A2A Server |
+========|================|=============|==========|=============+
         |                |             |          |
+========v================v=============v==========v=============+
|              LAYER 1 -- GOVERNANCE (deterministic)             |
|                                                                |
|  governance.py ----> Constitution (HARD + SOFT rules)          |
|  ast_verifier.py ----> Static analysis of generated code       |
|  supervisor.py ----> Meta-supervisor Q(0.4)+A(0.25)+C(0.2)+F  |
|  adversarial.py ----> Red-team + prompt injection detection    |
|  memory_governance.py ----> Memory control                     |
|  security_hierarchy.py ----> SYSTEM > USER > ASSISTANT         |
|  entropy_detector.py ----> Anomalous output detection          |
|  compliance_framework.py ----> Regulatory framework            |
|                                                                |
|  * enforce_with_proof() ----> Governance + automatic ZK proof  |
+============================|===================================+
                             |
+============================v===================================+
|              LAYER 2 -- FORMAL VERIFICATION (Z3)               |
|                                                                |
|  z3_verifier.py ----> 4 formal theorems PROVEN                 |
|  z3_gate.py ----> Neurosymbolic gate (APPROVED/REJECTED)       |
|  hierarchy_z3.py ----> 42 hierarchy patterns PROVEN            |
|  z3_proof.py ----> Proof storage + verification                |
|  z3_test_generator.py ----> Automatic Z3 test generator        |
+============================|===================================+
                             |
+============================v===================================+
|              LAYER 3 -- CRYPTOGRAPHIC PROOFS                   |
|                                                                |
|  zk_governance_proof.py ----> keccak256 hash per decision      |
|  zk_batch_prover.py ----> Merkle tree + batch attestation      |
|  proof_hash.py ----> Hash primitives                           |
|  proof_storage.py ----> Proof persistence                      |
|  merkle_tree.py ----> Merkle tree implementation               |
+============================|===================================+
                             |
+============================v===================================+
|              LAYER 4 -- SENTINEL LITE (external validation)    |
|                                                                |
|  sentinel_lite.py ----> 7 checks for external agents           |
|    |-- health (25%) ----> GET /health, response <5s            |
|    |-- identity (20%) ----> Valid ERC-8004 format              |
|    |-- metadata (15%) ----> agent.json with required fields    |
|    |-- a2a (15%) ----> /.well-known/agent.json accessible      |
|    |-- response_time (10%) ----> Endpoint latency              |
|    |-- mcp_tools (10%) ----> Number of exposed tools           |
|    +-- x402 (5%) ----> Payment capability                     |
|                                                                |
|  Verdicts: PASS (>=60) | WARN (>=40) | FAIL (<40)             |
|  validate_offline() ----> Works without network                |
+============================|===================================+
                             |
+============================v===================================+
|              LAYER 5 -- MESH (multi-LLM coordination)          |
|                                                                |
|  +-- NODES (11 active) ----------------------------------+     |
|  | Claude Code (orchestrator) | Claude Workers x3        |     |
|  | DeepSeek V3 | SambaNova | Q-AION Local | Cerebras     |     |
|  | Kimi K2.5 | MiMo-V2 | MiniMax | GLM-4.7 | Arena AI   |     |
|  +-------------------------------------------------------+     |
|                                                                |
|  node_mesh.py ----> NodeRegistry + MessageBus                  |
|  mesh_orchestrator.py ----> Task routing + scaling             |
|  mesh_router_v2.py ----> Smart routing by task type            |
|  mesh_scheduler.py ----> Priority queue                        |
|  mesh_load_balancer.py ----> Load distribution                 |
|  mesh_circuit_breaker.py ----> CLOSED/OPEN/HALF_OPEN           |
|  mesh_firewall.py ----> Message filtering                      |
|  mesh_guardian.py ----> Mesh security                          |
|  mesh_federation.py ----> Peer registration + heartbeats       |
|  mesh_consensus.py ----> Distributed consensus                 |
|  mesh_p2p.py ----> Peer-to-peer communication                 |
|  mesh_metrics_collector.py ----> Mesh metrics                  |
|  web_bridge.py ----> Captures AIs without API (Playwright)     |
|                                                                |
|  * threshold_consensus.py ----> N-of-M voting (FROST sim)     |
+============================|===================================+
                             |
+============================v===================================+
|              LAYER 6 -- BLOCKCHAIN (on-chain)                  |
|                                                                |
|  avalanche_bridge.py ----> Attestations on-chain (C-Chain)     |
|  chain_adapter.py ----> Multi-chain abstraction                |
|  contract_scanner.py ----> Contract analysis                   |
|  oracle_bridge.py ----> Oracle data feed                       |
|  revenue_tracker.py ----> x402 micropayments                   |
|                                                                |
|  * cross_chain_identity.py ----> Bridge Avalanche/Base/Celo/ETH|
|                                                                |
|  Contracts:                                                    |
|    ERC-8004 Identity: 0x8004A169FB4a3325136EB29fA0ceB6D2e...  |
|    Reputation Registry: 0x8004B663056A597Dffe9eCcC1965A19...  |
|    USDC: 0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E          |
+============================|===================================+
                             |
+============================v===================================+
|              LAYER 7 -- AGENTS (execution)                     |
|                                                                |
|  17 CrewAI Agents (config/agents.yaml):                        |
|    Orchestrator Lead    | File Organizer                       |
|    Product Manager      | Operations Director                 |
|    BizDev & Strategy    | Software Architect                  |
|    Full-Stack Dev       | QA Engineer                         |
|    Research Lead        | DevOps Engineer                     |
|    Blockchain Security  | Ideation Expert                     |
|    Multi-Chain Expert   | Quantum Expert                      |
|    Cybersecurity        | Methodologies Expert                |
|    BPM Expert           |                                      |
|                                                                |
|  crew_runner.py ----> crew_factory rebuild + retry x3          |
|  providers.py ----> TTL backoff (5->10->20 min) + chains       |
|  autonomous_daemon.py ----> Perceive->Decide->Execute->Evaluate|
|  claude_commander.py ----> 5 modes: SDK/Spawn/Team/Debate/Peers|
+================================================================+

+================================================================+
|              SECURITY (cross-cutting across all layers)         |
|                                                                |
|  cerberus.py ----> 3-headed guardian                           |
|  icarus.py / icarus_v2.py ----> Containment protocol          |
|  dlp.py ----> Data Loss Prevention                             |
|  e2e_encryption.py ----> Encrypted comms                       |
|  kms.py ----> Key Management                                  |
|  honeypot.py ----> Trap for attackers                          |
|  opsec_shield.py ----> Operational security                    |
|  agentleak_benchmark.py ----> PII detection benchmark          |
|  loop_guard.py ----> Infinite loop prevention                  |
|  pqc_analyzer.py ----> Post-quantum crypto analysis            |
+================================================================+
```

---

## Decision Flow (start to finish)

```
1. INPUT arrives (CLI, Telegram, A2A, Voice)
         |
2. +-----v-----+
   | Sentinel   | If interacting with external agent:
   | Lite       | -> 7 checks -> PASS/WARN/FAIL
   +-----+-----+ -> If FAIL, rejects interaction
         |
3. +-----v-----+
   | Governance | Constitutional rules (HARD blocks, SOFT warns)
   | Pipeline   | -> AST verification of generated code
   |            | -> Override detection (6 patterns)
   |            | -> Language compliance
   +-----+-----+
         |
4. +-----v-----+
   | Z3 Formal | 4 mathematically verified theorems
   | Verifier   | -> Gate: APPROVED / REJECTED / TIMEOUT / FALLBACK
   +-----+-----+
         |
5. +-----v-----+
   | ZK Proof  | keccak256 hash of the decision
   | Generator | -> GovernanceProof with input_hash + verdict
   |            | -> Accumulated in Merkle batch
   +-----+-----+
         |
6. +-----v-----+
   | Supervisor| Composite score: Q(0.4)+A(0.25)+C(0.2)+F(0.15)
   |            | -> Evaluates execution quality
   +-----+-----+
         |
7. +-----v-----+
   | Mesh      | Routes task to optimal LLM (11 nodes)
   | Router    | -> Threshold consensus if critical decision
   |            | -> Circuit breaker if provider fails
   +-----+-----+
         |
8. +-----v-----+
   | LLM       | Executes the task (Claude/DeepSeek/MiMo/etc)
   | Execution | -> crew_factory rebuild if retry needed
   +-----+-----+
         |
9. +-----v-----+
   | On-Chain  | Merkle root -> Avalanche C-Chain attestation
   | Attestation| -> Cross-chain bridge if needed (Base/Celo)
   +-----+-----+
         |
10.+-----v-----+
   | OUTPUT    | Result + proof hash + attestation tx
   |            | -> JSONL log for audit
   +-----------+
```

---

## Technology Stack

| Layer | Technology | Status |
|---|---|---|
| Language | Python 3.10+ | Production |
| Formal Verification | Z3 Theorem Prover | 4/4 PROVEN |
| Crypto Proofs | SHA3-256 (keccak256) + Merkle | Implemented |
| Blockchain | Avalanche C-Chain, Base, Celo, ETH | Multi-chain |
| Agents | CrewAI (17 agents) | Configured |
| LLM Routing | LiteLLM + custom router | 8+ providers |
| Memory | ChromaDB + HuggingFace embeddings | Active |
| Storage | JSONL (default) + PostgreSQL (prod) | Dual |
| CLI | dof-sdk (PyPI) | Published |
| CI/CD | GitHub Actions (3 workflows) | Green |
| Dashboard | Streamlit | localhost:8501 |
| Bots | Telegram (2 bots) | Active |
| Deploy | Oracle Cloud VPS + Railway | Configured |

---

## Key Files by Function

| Function | File | Approx LOC |
|---|---|---|
| Governance | `core/governance.py` | 440 |
| Z3 Verification | `core/z3_verifier.py` | 620 |
| Z3 Gate | `core/z3_gate.py` | 340 |
| ZK Proofs | `core/zk_governance_proof.py` | 290 |
| Merkle Batch | `core/zk_batch_prover.py` | 264 |
| Sentinel Lite | `core/sentinel_lite.py` | 827 |
| Cross-chain | `core/cross_chain_identity.py` | 272 |
| Threshold | `core/threshold_consensus.py` | 334 |
| Supervisor | `core/supervisor.py` | 480 |
| Mesh Orchestrator | `core/mesh_orchestrator.py` | ~500 |
| Providers | `core/providers.py` | 720 |
| Crew Runner | `core/crew_runner.py` | 580 |
| Commander | `core/claude_commander.py` | 820 |
| Daemon | `core/autonomous_daemon.py` | 750 |
| Session Resume | `core/session_resume.py` | 286 |
| Cost Tracker | `core/cost_tracker.py` | 368 |
| Mock Provider | `tests/mocks/mock_provider.py` | 205 |
| Competition Bible | `docs/COMPETITION_BIBLE.md` | 397 |

---

## Design Principles

1. **Zero-LLM governance** — Every governance decision is deterministic (regex, AST, Z3). No LLM judges another LLM.
2. **Zero external dependencies** — DOF works standalone, without Enigma or any external service.
3. **Proofs, not logs** — Every decision generates a verifiable cryptographic hash, not just a log.
4. **Multi-chain portable** — Identity and attestations on Avalanche, Base, Celo, Tempo, Ethereum.
5. **Heterogeneous mesh** — 11 distinct coordinated LLMs. Stronger than any individual model.
6. **Offline-capable** — Sentinel, governance, and Z3 work without an internet connection.
7. **Test-first** — 4,800 tests. No code is merged without tests.

---

*Last updated: March 27, 2026 — Cyber Paisa, Enigma Group*
