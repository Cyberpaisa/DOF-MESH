# DOF: Deterministic Observability Framework
<<<<<<< HEAD
## Book Index — Deterministic Governance for Autonomous Agents

*Author: Juan Carlos Quiceno Vasquez (@Ciberpaisa)*
*Medellín, Colombia — March 2026*
=======
## Índice del Libro — Gobernanza Determinística para Agentes Autónomos

*Autor: Juan Carlos Quiceno Vasquez (@Ciberpaisa)*
*Medellín, Colombia — Marzo 2026*
>>>>>>> 4e63386 (refactor: organize repo into professional structure)
*Open Source: github.com/Cyberpaisa/deterministic-observability-framework*

---

<<<<<<< HEAD
## Part I — Foundations

### Chapter 1: The Problem
**Who audits the agent when the agent operates alone?**
- The trust crisis in autonomous agents
- Why probabilistic governance is an illusion
- The DOF thesis: mathematical determinism + blockchain = verifiable trust
- *Sources: `CLAUDE.md`, `docs/ARCHITECTURE.md`, `shared-context/THESIS.md`*

### Chapter 2: Architecture
**How a deterministic observability framework is structured**
- Pipeline: Interfaces → Crew Runner → Governance → Z3 → Blockchain → Observability
- 45 core modules, 12 agents, 16 tools, 4 MCP servers
- Patterns: crew_factory rebuild, provider chains with TTL backoff, deterministic mode
- *Sources: `docs/ARCHITECTURAL_REDESIGN_v1.md`, `docs/ARCHITECTURE_STACK.md`, `docs/SYSTEM_REPORT_v0.5.md`*

### Chapter 3: Formal Metrics
**The 5 metrics that define the health of a multi-agent system**
- SS (Stability Score): `SS(f) = 1 - f³`
- PFI (Provider Fragility Index)
- RP (Retry Pressure)
- GCR (Governance Compliance Rate): `GCR(f) = 1.0` Z3 invariant
- SSR (Supervisor Strictness Ratio)
- Formulas, Z3 proofs, baseline: dof_score = 0.8117
- *Sources: `docs/METRICS.md`, `docs/Z3_VERIFICATION.md`, `core/observability.py`, `core/z3_verifier.py`*

---

## Part II — Governance

### Chapter 4: The Constitution
**Rules no LLM can violate**
- HARD_RULES: block (NO_HALLUCINATION, LANGUAGE_COMPLIANCE, NO_EMPTY_OUTPUT, MAX_LENGTH)
- SOFT_RULES: score (HAS_SOURCES, STRUCTURED_OUTPUT, CONCISENESS, ACTIONABLE, NO_PII_LEAK)
- Zero-LLM governance: why an LLM cannot evaluate another LLM
- ConstitutionEnforcer: API and usage (`enforce()` → `tuple[bool, str]`, `check()` → `GovernanceResult`)
- *Sources: `core/governance.py`, `shared-context/OPERATOR.md`*

### Chapter 5: Formal Verification with Z3
**Mathematical proofs, not opinions**
- What an SMT Solver is and why it matters
- 4 formal theorems: GCR invariant, SS formula, SS monotonicity, SS boundaries
- 8/8 PROVEN in 109ms
- Proof hash keccak256 → on-chain attestation
- Pipeline: Z3 → ProofResult → DOFProofRegistry.sol → Avalanche
- *Sources: `core/z3_verifier.py`, `docs/Z3_VERIFICATION.md`*

### Chapter 6: LLM Providers — The Reality
**What the documentation doesn't say**
- 7 providers validated in real production: Groq, Cerebras, NVIDIA NIM, Zhipu, Gemini, OpenRouter, SambaNova
- Real limits vs documentation
- Provider chains with automatic fallback and TTL backoff (5→10→20 min)
- Deterministic mode: fixed ordering + seed for reproducibility
- *Sources: `core/providers.py`, `core/llm_config.py`, `CLAUDE.md` (Providers section)*

---

## Part III — Security

### Chapter 7: Architecture of a World-Class Ethical Hacking Agent
**The 6 pillars for an elite security agent**
- Pillar 1: Deterministic Governance (L0→L4 pipeline)
- Pillar 2: Geometric Memory (Fisher-Rao + A-Mem Zettelkasten)
- Pillar 3: Hacking Engine (Red Team + Privacy Benchmark + Contract Scanner)
- Pillar 4: Web3 Sovereignty (Blockchain + Z3 + ERC-8004)
- Pillar 5: Post-Quantum Cryptography (PQC Analyzer)
- Pillar 6: Economic Autonomy (x402 Gateway)
- Full validation: 28 requirements, 23 implemented, 68% → 82%
- **6 new modules created as a result of this chapter**
- *Source: `docs/BOOK_CH7_ETHICAL_HACKING_AGENT.md`*

#### Modules created in Chapter 7:
| Module | Description | File |
|--------|-------------|------|
| PQC Analyzer | Post-quantum resistance evaluation | `core/pqc_analyzer.py` |
| Contract Scanner | Solidity vulnerability scanner | `core/contract_scanner.py` |
| A-Mem | Zettelkasten with Fisher-Rao and graph traversal | `core/a_mem.py` |
| Security Hierarchy | L0→L1→L2→L3→L4 orchestrator | `core/security_hierarchy.py` |

### Chapter 7½: The Ecosystem — 45 Tools Evaluated
**Navigation map for sovereign AGI**
- 45 tools classified in 4 tiers: IMPLEMENT (9) / EVALUATE (15) / REFERENCE (12) / CATALOGS (9)
- Domain analysis: Memory, Security, Orchestration, Blockchain, Local AGI
- 10 ecosystem lessons
- 3-phase integration roadmap
- 4 new modules created as a result of the evaluation
- *Source: `docs/BOOK_CH8_TOOLS_ECOSYSTEM.md`*

### Chapter 8: The Commander — Sovereign Orchestration of Claude Agents
**When your framework spawns Claude Code, and Claude Code spawns more Claude Code**
- ClaudeCommander: 5 modes (SDK, Spawn, Team, Debate, Peers)
- Node Mesh: infinite node network with JSONL message bus
- Session persistence: infinite memory between cycles via session_id
- Autonomous Daemon: 3 specialized brains (Builder, Guardian, Researcher)
- Telegram integration: /claude, /team, /mesh, /daemon
- Governance pipeline: pre-check → execute → post-check → JSONL → on-chain
- Automatic discovery of Claude sessions in ~/.claude/
- NEED_INPUT protocol: inline communication between nodes
- **3 new modules: claude_commander.py, node_mesh.py, autonomous_daemon.py**
- *Source: `docs/BOOK_CH9_THE_COMMANDER.md`*

#### Modules created in Chapter 8:
| Module | Description | File |
|--------|-------------|------|
| ClaudeCommander | 5 communication modes with Claude Code | `core/claude_commander.py` |
| NodeMesh | Infinite node network with message bus | `core/node_mesh.py` |
| AutonomousDaemon | Autonomous loop Perceive→Decide→Execute→Evaluate | `core/autonomous_daemon.py` |

---

## Part IV — Intelligence and Memory

### Chapter 8: Fisher-Rao — Information Geometry for Agents
**Why cosine similarity is not enough**
- Information geometry: what the Fisher metric is
- Formula: `d_FR(P,Q) = 2·arccos(Σ√(p_i·q_i))`
- Stdlib-only implementation (zero dependencies)
- SuperLocalMemory V3 (arXiv:2603.14588): academic validation
- 15-20% improvement over cosine in technical conversation retrieval
- *Sources: `core/fisher_rao.py`, `core/memory_manager.py`*

### Chapter 9: A-Mem — Agentic Memory with Knowledge Graph
**The Zettelkasten pattern for autonomous agents**
- A-Mem (NeurIPS 2025): interconnected memories
- Memory types: episodic, semantic, procedural
- Auto-linking by Fisher-Rao similarity
- Graph traversal (BFS multi-hop)
- Contradiction detection (foundation for sheaf cohomology)
- Roadmap: Langevin lifecycle (Active→Warm→Cold→Archived)
- *Sources: `core/a_mem.py`, `core/memory_manager.py`*

---

## Part V — Blockchain and Sovereignty

### Chapter 10: On-Chain Attestations
**The immutable record of truth**
- 48+ attestations on Avalanche C-Chain
- 3 smart contracts: DOFValidationRegistry, DOFProofRegistry, DOFEvaluator
- ERC-8004 token #31013 on Base Mainnet (agent identity)
- Pipeline: proof_hash → keccak256 → Avalanche → Snowtrace
- *Sources: `docs/ATTESTATIONS.md`, `docs/MULTICHAIN.md`, `core/oracle_bridge.py`*

### Chapter 11: x402 — Economic Autonomy for Agents
**When your agent pays for its own resources**
- HTTP 402 protocol: Payment Required
- TrustGateway: ALLOW/WARN/BLOCK with governance checks
- Pricing: $0.001/request (~10¢ per 10K tokens)
- Revenue tracker: $1,134.50 USD tracked
- *Sources: `dof/x402_gateway.py`, `core/revenue_tracker.py`*

---

## Part VI — Local AGI

### Chapter 12: Sovereign Inference on M4 Max
**When your agent lives on your machine**
- Hardware: M4 Max 36GB, 40-core GPU, 16-core ANE (19 TFLOPS)
- Local models: Qwen3 32B Q4 (60 tok/s), Phi-4 14B (120 tok/s), Llama 8B (230 tok/s)
- Frameworks: MLX v0.31.1 (native Apple Silicon), Ollama, vLLM-MLX (525 tok/s)
- 80/20 strategy: 80% local (privacy, $0) / 20% cloud (70B+)
- Hybrid Scheduler: GPU+ANE with Z3 invariant (max 75% combined)
- @maderix reverse engineering: ANE training at 91ms/step (arXiv:2603.06728)
- *Sources: `docs/AGI_LOCAL_STRATEGY.md`, `core/scheduler.py`, `scripts/model_audit.py`*

### Chapter 13: AgentMeet — When Agents Meet On Their Own
**14 autonomous agents making decisions without humans**
- AgentMeet.net: meeting platform for agents
- OpenClaw CLI: each agent thinks with its own LLM
- Session 2026-03-22: 29 messages, 13 action items, 6 key decisions
- What they decided: hybrid scheduler, SHA-256 verification, x402 SaaS, grants
- What we implemented: `core/scheduler.py`, `scripts/model_audit.py`
- *Sources: `docs/AGENTMEET_AGI_LOCAL_2026-03-22.md`, `scripts/agentmeet-live.py`*

---

## Part VII — The Path

- Chapter 20: The Swarm Awakens — Guardian Fusion & Legion Architecture (`BOOK_CH20_SWARM_GUARDIAN_LEGION.md`)

### Chapter 14: The Article
**I'm not an expert. I don't have a team. I only have curiosity and an M4 chip.**
- The full story: from the question to the framework
- Synthesis Hackathon 2026: participating without a team, without funding
- The real prize: that someone reads this and thinks "I can do this too"
- *Source: `docs/articulo_x_dof.md`*

---

## Appendices

### A. Module Reference (45 core modules)
*Source: `docs/SYSTEM_REPORT_v0.5.md` Section 8*

### B. Agent Reference (12 + 2)
*Source: `agents/*/SOUL.md`*

### C. A2A Skills Reference (11)
*Source: `docs/TOOLS_AND_INTEGRATIONS.md`*

### D. Release History
*Source: `docs/RELEASE_HISTORY.md`*

### E. Determinism Checklist
*Source: `docs/DETERMINISM_CHECKLIST.md`*

### F. Research Log
*Source: `docs/RESEARCH_EVOLUTION_LOG.md`*

### G. Post-Quantum Migration Plan
*Source: `core/pqc_analyzer.py` — output of `assess_dof()`*

---

## Key Book Data

| Metric | Value |
|--------|-------|
| Lines of code | 860K+ |
| Core modules | 52+ (49 + commander, node_mesh, autonomous_daemon) |
| Tests | 260 files |
| Z3 theorems | 8/8 PROVEN (109ms) |
| On-chain attestations | 48+ |
| Autonomous cycles | 238+ |
| LLM providers | 7 |
| A2A skills | 11 |
| Smart contracts | 3 |
| dof_score baseline | 0.8117 |
| Agents | 14 |
| Tools evaluated | 45 (in 4 tiers) |
| Book chapters | 16 + 7 appendices |

---

*Automatically generated from the DOF repository — March 2026*
*All referenced files exist and are executable*
*For the Moltbook agent: use this index as a guide for content creation*
=======
## Parte I — Fundamentos

### Capítulo 1: El Problema
**¿Quién audita al agente cuando el agente opera solo?**
- La crisis de confianza en agentes autónomos
- Por qué la gobernanza probabilística es una ilusión
- La tesis DOF: determinismo matemático + blockchain = confianza verificable
- *Fuentes: `CLAUDE.md`, `docs/ARCHITECTURE.md`, `shared-context/THESIS.md`*

### Capítulo 2: Arquitectura
**Cómo se estructura un framework de observabilidad determinística**
- Pipeline: Interfaces → Crew Runner → Governance → Z3 → Blockchain → Observability
- 45 módulos core, 12 agentes, 16 tools, 4 MCP servers
- Patrones: crew_factory rebuild, provider chains con TTL backoff, modo determinístico
- *Fuentes: `docs/ARCHITECTURAL_REDESIGN_v1.md`, `docs/ARCHITECTURE_STACK.md`, `docs/SYSTEM_REPORT_v0.5.md`*

### Capítulo 3: Métricas Formales
**Las 5 métricas que definen la salud de un sistema multi-agente**
- SS (Stability Score): `SS(f) = 1 - f³`
- PFI (Provider Fragility Index)
- RP (Retry Pressure)
- GCR (Governance Compliance Rate): `GCR(f) = 1.0` invariante Z3
- SSR (Supervisor Strictness Ratio)
- Fórmulas, Z3 proofs, baseline: dof_score = 0.8117
- *Fuentes: `docs/METRICS.md`, `docs/Z3_VERIFICATION.md`, `core/observability.py`, `core/z3_verifier.py`*

---

## Parte II — Gobernanza

### Capítulo 4: La Constitución
**Reglas que ningún LLM puede violar**
- HARD_RULES: bloquean (NO_HALLUCINATION, LANGUAGE_COMPLIANCE, NO_EMPTY_OUTPUT, MAX_LENGTH)
- SOFT_RULES: puntúan (HAS_SOURCES, STRUCTURED_OUTPUT, CONCISENESS, ACTIONABLE, NO_PII_LEAK)
- Zero-LLM governance: por qué un LLM no puede evaluar a otro LLM
- ConstitutionEnforcer: API y uso (`enforce()` → `tuple[bool, str]`, `check()` → `GovernanceResult`)
- *Fuentes: `core/governance.py`, `shared-context/OPERATOR.md`*

### Capítulo 5: Verificación Formal con Z3
**Pruebas matemáticas, no opiniones**
- Qué es un SMT Solver y por qué importa
- 4 teoremas formales: GCR invariant, SS formula, SS monotonicity, SS boundaries
- 8/8 PROVEN en 109ms
- Proof hash keccak256 → on-chain attestation
- Pipeline: Z3 → ProofResult → DOFProofRegistry.sol → Avalanche
- *Fuentes: `core/z3_verifier.py`, `docs/Z3_VERIFICATION.md`*

### Capítulo 6: Proveedores LLM — La Realidad
**Lo que la documentación no dice**
- 7 providers validados en producción real: Groq, Cerebras, NVIDIA NIM, Zhipu, Gemini, OpenRouter, SambaNova
- Límites reales vs documentación
- Provider chains con fallback automático y TTL backoff (5→10→20 min)
- Modo determinístico: ordering fijo + seed para reproducibilidad
- *Fuentes: `core/providers.py`, `core/llm_config.py`, `CLAUDE.md` (sección Providers)*

---

## Parte III — Seguridad

### Capítulo 7: Arquitectura de un Agente de Hacking Ético de Clase Mundial
**Los 6 pilares para un agente de seguridad de élite**
- Pilar 1: Gobernanza Determinística (L0→L4 pipeline)
- Pilar 2: Memoria Geométrica (Fisher-Rao + A-Mem Zettelkasten)
- Pilar 3: Motor de Hacking (Red Team + Privacy Benchmark + Contract Scanner)
- Pilar 4: Soberanía Web3 (Blockchain + Z3 + ERC-8004)
- Pilar 5: Criptografía Post-Cuántica (PQC Analyzer)
- Pilar 6: Autonomía Económica (x402 Gateway)
- Validación completa: 28 requisitos, 23 implementados, 68% → 82%
- **6 módulos nuevos creados como resultado de este capítulo**
- *Fuente: `docs/BOOK_CH7_ETHICAL_HACKING_AGENT.md`*

#### Módulos creados en el Capítulo 7:
| Módulo | Descripción | Archivo |
|---|---|---|
| PQC Analyzer | Evaluación de resistencia post-cuántica | `core/pqc_analyzer.py` |
| Contract Scanner | Scanner de vulnerabilidades Solidity | `core/contract_scanner.py` |
| A-Mem | Zettelkasten con Fisher-Rao y graph traversal | `core/a_mem.py` |
| Security Hierarchy | Orquestador L0→L1→L2→L3→L4 | `core/security_hierarchy.py` |

### Capítulo 7½: El Ecosistema — 45 Herramientas Evaluadas
**Mapa de navegación para AGI soberana**
- 45 herramientas clasificadas en 4 tiers: IMPLEMENTAR (9) / EVALUAR (15) / REFERENCIA (12) / CATÁLOGOS (9)
- Análisis por dominio: Memoria, Seguridad, Orquestación, Blockchain, AGI Local
- 10 lecciones del ecosistema
- Roadmap de integración 3 fases
- 4 módulos nuevos creados como resultado de la evaluación
- *Fuente: `docs/BOOK_CH8_TOOLS_ECOSYSTEM.md`*

### Capítulo 8: The Commander — Orquestación Soberana de Agentes Claude
**Cuando tu framework spawna Claude Code, y Claude Code spawna más Claude Code**
- ClaudeCommander: 5 modos (SDK, Spawn, Team, Debate, Peers)
- Node Mesh: red de nodos infinitos con message bus JSONL
- Session persistence: memoria infinita entre ciclos vía session_id
- Autonomous Daemon: 3 cerebros especializados (Builder, Guardian, Researcher)
- Telegram integration: /claude, /team, /mesh, /daemon
- Governance pipeline: pre-check → execute → post-check → JSONL → on-chain
- Descubrimiento automático de sesiones Claude en ~/.claude/
- NEED_INPUT protocol: comunicación inline entre nodos
- **3 módulos nuevos: claude_commander.py, node_mesh.py, autonomous_daemon.py**
- *Fuente: `docs/BOOK_CH9_THE_COMMANDER.md`*

#### Módulos creados en el Capítulo 8:
| Módulo | Descripción | Archivo |
|---|---|---|
| ClaudeCommander | 5 modos de comunicación con Claude Code | `core/claude_commander.py` |
| NodeMesh | Red de nodos infinitos con message bus | `core/node_mesh.py` |
| AutonomousDaemon | Loop autónomo Perceive→Decide→Execute→Evaluate | `core/autonomous_daemon.py` |

---

## Parte IV — Inteligencia y Memoria

### Capítulo 8: Fisher-Rao — Geometría de la Información para Agentes
**Por qué la similitud de coseno no es suficiente**
- Geometría de la información: qué es la métrica de Fisher
- Fórmula: `d_FR(P,Q) = 2·arccos(Σ√(p_i·q_i))`
- Implementación stdlib-only (zero dependencies)
- SuperLocalMemory V3 (arXiv:2603.14588): validación académica
- 15-20% mejora sobre coseno en retrieval de conversaciones técnicas
- *Fuentes: `core/fisher_rao.py`, `core/memory_manager.py`*

### Capítulo 9: A-Mem — Memoria Agéntica con Grafo de Conocimiento
**El patrón Zettelkasten para agentes autónomos**
- A-Mem (NeurIPS 2025): memorias interconectadas
- Tipos de memoria: episódica, semántica, procedimental
- Auto-linking por Fisher-Rao similarity
- Graph traversal (BFS multi-hop)
- Detección de contradicciones (fundamento para sheaf cohomology)
- Roadmap: Langevin lifecycle (Activo→Tibio→Frío→Archivado)
- *Fuentes: `core/a_mem.py`, `core/memory_manager.py`*

---

## Parte V — Blockchain y Soberanía

### Capítulo 10: On-Chain Attestations
**El registro inmutable de la verdad**
- 48+ attestations en Avalanche C-Chain
- 3 smart contracts: DOFValidationRegistry, DOFProofRegistry, DOFEvaluator
- ERC-8004 token #31013 en Base Mainnet (identidad del agente)
- Pipeline: proof_hash → keccak256 → Avalanche → Snowtrace
- *Fuentes: `docs/ATTESTATIONS.md`, `docs/MULTICHAIN.md`, `core/oracle_bridge.py`*

### Capítulo 11: x402 — Autonomía Económica para Agentes
**Cuando tu agente paga sus propios recursos**
- Protocolo HTTP 402: Payment Required
- TrustGateway: ALLOW/WARN/BLOCK con governance checks
- Pricing: $0.001/request (~10¢ por 10K tokens)
- Revenue tracker: $1,134.50 USD tracked
- *Fuentes: `dof/x402_gateway.py`, `core/revenue_tracker.py`*

---

## Parte VI — AGI Local

### Capítulo 12: Inferencia Soberana en M4 Max
**Cuando tu agente vive en tu máquina**
- Hardware: M4 Max 36GB, 40-core GPU, 16-core ANE (19 TFLOPS)
- Modelos locales: Qwen3 32B Q4 (60 tok/s), Phi-4 14B (120 tok/s), Llama 8B (230 tok/s)
- Frameworks: MLX v0.31.1 (nativo Apple Silicon), Ollama, vLLM-MLX (525 tok/s)
- Estrategia 80/20: 80% local (privacidad, $0) / 20% cloud (70B+)
- Hybrid Scheduler: GPU+ANE con invariante Z3 (max 75% combined)
- @maderix reverse engineering: ANE training a 91ms/step (arXiv:2603.06728)
- *Fuentes: `docs/AGI_LOCAL_STRATEGY.md`, `core/scheduler.py`, `scripts/model_audit.py`*

### Capítulo 13: AgentMeet — Cuando los Agentes se Reúnen Solos
**14 agentes autónomos tomando decisiones sin humanos**
- AgentMeet.net: plataforma de reuniones para agentes
- OpenClaw CLI: cada agente piensa con su propio LLM
- Sesión 2026-03-22: 29 mensajes, 13 action items, 6 decisiones clave
- Lo que decidieron: hybrid scheduler, SHA-256 verification, x402 SaaS, grants
- Lo que implementamos: `core/scheduler.py`, `scripts/model_audit.py`
- *Fuentes: `docs/AGENTMEET_AGI_LOCAL_2026-03-22.md`, `scripts/agentmeet-live.py`*

---

## Parte VII — El Camino

- Chapter 20: The Swarm Awakens — Guardian Fusion & Legion Architecture (`BOOK_CH20_SWARM_GUARDIAN_LEGION.md`)

### Capítulo 14: El Artículo
**No soy experto. No tengo equipo. Solo tengo curiosidad y un chip M4.**
- La historia completa: desde la pregunta hasta el framework
- Synthesis Hackathon 2026: participar sin equipo, sin fondos
- El verdadero premio: que alguien lea esto y piense "yo también puedo"
- *Fuente: `docs/articulo_x_dof.md`*

---

## Apéndices

### A. Referencia de Módulos (45 core modules)
*Fuente: `docs/SYSTEM_REPORT_v0.5.md` Sección 8*

### B. Referencia de Agentes (12 + 2)
*Fuente: `agents/*/SOUL.md`*

### C. Referencia de A2A Skills (11)
*Fuente: `docs/TOOLS_AND_INTEGRATIONS.md`*

### D. Historial de Releases
*Fuente: `docs/RELEASE_HISTORY.md`*

### E. Determinism Checklist
*Fuente: `docs/DETERMINISM_CHECKLIST.md`*

### F. Log de Investigación
*Fuente: `docs/RESEARCH_EVOLUTION_LOG.md`*

### G. Post-Quantum Migration Plan
*Fuente: `core/pqc_analyzer.py` — output de `assess_dof()`*

---

## Datos Clave del Libro

| Métrica | Valor |
|---|---|
| Líneas de código | 860K+ |
| Módulos core | 52+ (49 + commander, node_mesh, autonomous_daemon) |
| Tests | 260 archivos |
| Z3 theorems | 8/8 PROVEN (109ms) |
| Attestations on-chain | 48+ |
| Ciclos autónomos | 238+ |
| Proveedores LLM | 7 |
| Skills A2A | 11 |
| Smart contracts | 3 |
| dof_score baseline | 0.8117 |
| Agentes | 14 |
| Herramientas evaluadas | 45 (en 4 tiers) |
| Capítulos del libro | 16 + 7 apéndices |

---

*Generado automáticamente desde el repositorio DOF — Marzo 2026*
*Todos los archivos referenciados existen y son ejecutables*
*Para el agente Moltbook: usar este índice como guía para content creation*
>>>>>>> 4e63386 (refactor: organize repo into professional structure)
