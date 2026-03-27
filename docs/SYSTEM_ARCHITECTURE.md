# DOF-MESH v0.5.0 — Arquitectura Completa del Sistema

> Deterministic Observability Framework — Sistema autónomo de governance para agentes de IA
> Cyber Paisa — Enigma Group — 2026

---

## Números del Sistema

| Métrica | Valor |
|---|---|
| Módulos core | 132 |
| Archivos de test | 143 |
| Tests totales | 3,698 (100% passing) |
| Líneas de código | 119,409 |
| Documentación | 105 archivos .md |
| Interfaces | 4 (Dashboard, Telegram, Voz, Voz Realtime) |
| Scripts | 13 |
| CI Workflows | 3 (Tests, DOF CI, Z3 Verify) |
| SDK | dof-sdk 0.5.0 (PyPI) |
| On-chain | 21+ attestations (Avalanche C-Chain) |
| Agentes CrewAI | 17 |
| Nodos Mesh LLM | 11 |
| Capas de governance | 7 |

---

## Arquitectura por Capas

```
+================================================================+
|                    INTERFACES (entrada)                         |
|  CLI (main.py)  | Telegram Bot | Dashboard | Voz | A2A Server  |
+========|================|=============|==========|=============+
         |                |             |          |
+========v================v=============v==========v=============+
|              CAPA 1 -- GOVERNANCE (deterministica)             |
|                                                                |
|  governance.py ----> Constitution (HARD + SOFT rules)          |
|  ast_verifier.py ----> Analisis estatico de codigo generado    |
|  supervisor.py ----> Meta-supervisor Q(0.4)+A(0.25)+C(0.2)+F  |
|  adversarial.py ----> Red-team + prompt injection detection    |
|  memory_governance.py ----> Control de memoria                 |
|  security_hierarchy.py ----> SYSTEM > USER > ASSISTANT         |
|  entropy_detector.py ----> Deteccion de output anomalo         |
|  compliance_framework.py ----> Marco regulatorio               |
|                                                                |
|  * enforce_with_proof() ----> Governance + ZK proof automatico |
+============================|===================================+
                             |
+============================v===================================+
|              CAPA 2 -- VERIFICACION FORMAL (Z3)                |
|                                                                |
|  z3_verifier.py ----> 4 teoremas formales PROVEN               |
|  z3_gate.py ----> Gate neurosimbolico (APPROVED/REJECTED)      |
|  hierarchy_z3.py ----> 42 patrones de jerarquia PROVEN         |
|  z3_proof.py ----> Proof storage + verificacion                |
|  z3_test_generator.py ----> Generador automatico de tests Z3   |
+============================|===================================+
                             |
+============================v===================================+
|              CAPA 3 -- PROOFS CRIPTOGRAFICOS                   |
|                                                                |
|  zk_governance_proof.py ----> keccak256 hash per decision      |
|  zk_batch_prover.py ----> Merkle tree + batch attestation      |
|  proof_hash.py ----> Hash primitives                           |
|  proof_storage.py ----> Proof persistence                      |
|  merkle_tree.py ----> Merkle tree implementation               |
+============================|===================================+
                             |
+============================v===================================+
|              CAPA 4 -- SENTINEL LITE (validacion externa)      |
|                                                                |
|  sentinel_lite.py ----> 7 checks de agentes externos           |
|    |-- health (25%) ----> GET /health, respuesta <5s           |
|    |-- identity (20%) ----> Formato ERC-8004 valido            |
|    |-- metadata (15%) ----> agent.json con campos requeridos   |
|    |-- a2a (15%) ----> /.well-known/agent.json accesible       |
|    |-- response_time (10%) ----> Latencia del endpoint         |
|    |-- mcp_tools (10%) ----> Cantidad de tools expuestas       |
|    +-- x402 (5%) ----> Capacidad de pagos                     |
|                                                                |
|  Verdicts: PASS (>=60) | WARN (>=40) | FAIL (<40)             |
|  validate_offline() ----> Funciona sin red                     |
+============================|===================================+
                             |
+============================v===================================+
|              CAPA 5 -- MESH (coordinacion multi-LLM)           |
|                                                                |
|  +-- NODOS (11 activos) --------------------------------+      |
|  | Claude Code (orquestador) | Claude Workers x3        |      |
|  | DeepSeek V3 | SambaNova | Q-AION Local | Cerebras    |      |
|  | Kimi K2.5 | MiMo-V2 | MiniMax | GLM-4.7 | Arena AI  |      |
|  +-------------------------------------------------------+      |
|                                                                |
|  node_mesh.py ----> NodeRegistry + MessageBus                  |
|  mesh_orchestrator.py ----> Task routing + scaling             |
|  mesh_router_v2.py ----> Smart routing por tipo de tarea       |
|  mesh_scheduler.py ----> Priority queue                        |
|  mesh_load_balancer.py ----> Distribucion de carga             |
|  mesh_circuit_breaker.py ----> CLOSED/OPEN/HALF_OPEN           |
|  mesh_firewall.py ----> Filtrado de mensajes                   |
|  mesh_guardian.py ----> Seguridad del mesh                     |
|  mesh_federation.py ----> Peer registration + heartbeats       |
|  mesh_consensus.py ----> Consenso distribuido                  |
|  mesh_p2p.py ----> Comunicacion peer-to-peer                  |
|  mesh_metrics_collector.py ----> Metricas del mesh             |
|  web_bridge.py ----> Captura IAs sin API (Playwright)          |
|                                                                |
|  * threshold_consensus.py ----> N-of-M voting (FROST sim)     |
+============================|===================================+
                             |
+============================v===================================+
|              CAPA 6 -- BLOCKCHAIN (on-chain)                   |
|                                                                |
|  avalanche_bridge.py ----> Attestations on-chain (C-Chain)     |
|  chain_adapter.py ----> Abstraccion multi-chain                |
|  contract_scanner.py ----> Analisis de contratos               |
|  oracle_bridge.py ----> Oracle data feed                       |
|  revenue_tracker.py ----> x402 micropagos                      |
|                                                                |
|  * cross_chain_identity.py ----> Bridge Avalanche/Base/Celo/ETH|
|                                                                |
|  Contratos:                                                    |
|    ERC-8004 Identity: 0x8004A169FB4a3325136EB29fA0ceB6D2e...  |
|    Reputation Registry: 0x8004B663056A597Dffe9eCcC1965A19...  |
|    USDC: 0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E          |
+============================|===================================+
                             |
+============================v===================================+
|              CAPA 7 -- AGENTES (ejecucion)                     |
|                                                                |
|  17 Agentes CrewAI (config/agents.yaml):                       |
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
|              SEGURIDAD (transversal a todas las capas)          |
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

## Flujo de una Decision (principio a fin)

```
1. INPUT llega (CLI, Telegram, A2A, Voz)
         |
2. +-----v-----+
   | Sentinel   | Si interactua con agente externo:
   | Lite       | -> 7 checks -> PASS/WARN/FAIL
   +-----+-----+ -> Si FAIL, rechaza interaccion
         |
3. +-----v-----+
   | Governance | Constitutional rules (HARD bloquea, SOFT advierte)
   | Pipeline   | -> AST verification de codigo generado
   |            | -> Override detection (6 patrones)
   |            | -> Language compliance
   +-----+-----+
         |
4. +-----v-----+
   | Z3 Formal | 4 teoremas verificados matematicamente
   | Verifier   | -> Gate: APPROVED / REJECTED / TIMEOUT / FALLBACK
   +-----+-----+
         |
5. +-----v-----+
   | ZK Proof  | keccak256 hash de la decision
   | Generator | -> GovernanceProof con input_hash + verdict
   |            | -> Se acumula en Merkle batch
   +-----+-----+
         |
6. +-----v-----+
   | Supervisor| Score compuesto: Q(0.4)+A(0.25)+C(0.2)+F(0.15)
   |            | -> Evalua calidad de la ejecucion
   +-----+-----+
         |
7. +-----v-----+
   | Mesh      | Routea tarea al LLM optimo (11 nodos)
   | Router    | -> Threshold consensus si decision critica
   |            | -> Circuit breaker si provider falla
   +-----+-----+
         |
8. +-----v-----+
   | LLM       | Ejecuta la tarea (Claude/DeepSeek/MiMo/etc)
   | Execution | -> crew_factory rebuild si retry necesario
   +-----+-----+
         |
9. +-----v-----+
   | On-Chain  | Merkle root -> Avalanche C-Chain attestation
   | Attestation| -> Cross-chain bridge si necesario (Base/Celo)
   +-----+-----+
         |
10.+-----v-----+
   | OUTPUT    | Resultado + proof hash + attestation tx
   |            | -> JSONL log para auditoria
   +-----------+
```

---

## Stack Tecnologico

| Capa | Tecnologia | Estado |
|---|---|---|
| Language | Python 3.10+ | Produccion |
| Formal Verification | Z3 Theorem Prover | 4/4 PROVEN |
| Crypto Proofs | SHA3-256 (keccak256) + Merkle | Implementado |
| Blockchain | Avalanche C-Chain, Base, Celo, ETH | Multi-chain |
| Agents | CrewAI (17 agentes) | Configurados |
| LLM Routing | LiteLLM + custom router | 8+ providers |
| Memory | ChromaDB + HuggingFace embeddings | Activo |
| Storage | JSONL (default) + PostgreSQL (prod) | Dual |
| CLI | dof-sdk (PyPI) | Publicado |
| CI/CD | GitHub Actions (3 workflows) | Verde |
| Dashboard | Streamlit | localhost:8501 |
| Bots | Telegram (2 bots) | Activos |
| Deploy | Oracle Cloud VPS + Railway | Configurado |

---

## Archivos Clave por Funcion

| Funcion | Archivo | LOC aprox |
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
| Competition Bible | `docs/COMPETITION_BIBLE.md` | 397 |

---

## Principios de Diseno

1. **Zero-LLM governance** — Toda decision de governance es deterministica (regex, AST, Z3). Ningun LLM juzga a otro LLM.
2. **Zero dependencias externas** — DOF funciona solo, sin Enigma ni ningun servicio externo.
3. **Proofs, no logs** — Cada decision genera un hash criptografico verificable, no solo un log.
4. **Multi-chain portable** — Identidad y attestations en Avalanche, Base, Celo, Ethereum.
5. **Mesh heterogeneo** — 11 LLMs distintos coordinados. Mas fuerte que cualquier modelo individual.
6. **Offline-capable** — Sentinel, governance, y Z3 funcionan sin conexion a internet.
7. **Test-first** — 3,698 tests. No se mergea codigo sin tests.

---

*Ultima actualizacion: 27 marzo 2026 — Cyber Paisa, Enigma Group*
