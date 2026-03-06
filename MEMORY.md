# Long-Term Memory — Cyber Paisa Mission Control
# Actualizado: 2026-03-06

## Sistema
- 8 agentes AI especializados (CrewAI) con SOUL.md cada uno
- 11 crews (flujos de trabajo) — research, code-review, data, database, full-mvp, enigma-audit, grant-hunt, content, daily-ops, weekly-report, build-project
- 7 proveedores LLM gratuitos: Groq, NVIDIA NIM, Cerebras, Zhipu AI, Gemini, SambaNova, OpenRouter
- 6 interfaces: CLI (15 opciones), Telegram Bot, Voz (Whisper+gTTS), Streamlit Dashboard, CLI args, A2A Server
- Multi-proyecto via config/projects.yaml
- Smart Router asigna LLM por contexto (tokens, tipo de tarea, rol)

## DOF — Deterministic Observability Framework
- **SDK:** dof-sdk 0.1.0 on PyPI (`pip install dof-sdk`)
- **Codebase:** 27,000+ LOC, 76 Python files, 22 core modules, 510 tests
- **On-chain:** 21 attestations on Avalanche C-Chain mainnet (DOFValidationRegistry at 0x88f6...C052)
- **Formal verification:** Z3 SMT — 4/4 theorems verified (GCR invariant, SS formula, monotonicity, boundaries)
- **Governance:** 7 layers — Constitution, AST, Supervisor, Adversarial, Memory, Z3, Oracle
- **Merkle tree batching:** N attestations in 1 on-chain transaction
- **Dual storage:** JSONL (default) + PostgreSQL (production via StorageFactory)
- **Protocol access:** MCP Server (10 tools, 3 resources) + REST API (14 FastAPI endpoints)
- **Framework-agnostic:** GenericAdapter, LangGraphAdapter, CrewAIAdapter
- **Enigma integration:** dof_trust_scores table + combined_trust_view materialized view

## Arquitectura de Capas
- **Interfaces:** CLI, Telegram, Voz, Dashboard, A2A Server (:8000)
- **Crews:** 11 flujos con Process.sequential
- **Agentes:** 8 con CONSTITUTION + SOUL.md
- **Tools nativos:** 16 tools (code, research, data, files, execution, blockchain)
- **MCP Servers:** Filesystem, Web Search (sin API key), Fetch URL, Knowledge Graph
- **Memoria:** ChromaDB + HuggingFace embeddings (384 dims, all-MiniLM-L6-v2)
- **LLM Providers:** 7 activos con fallback chain por rol
- **Seguridad:** Blocklists, path validation, whitelist binarios
- **DOF Core:** 22 modules — governance, observability, adversarial, Z3, oracle, avalanche, enigma, merkle, memory, storage, etc.

## Distribución de LLMs por Agente
| Agente | Primario | Proveedor | Fallback |
|--------|----------|-----------|----------|
| Code Architect | Kimi K2.5 | NVIDIA | Kimi K2 (Groq) |
| Research Analyst | Llama 3.3 70B | Groq | DeepSeek V3.2 (NVIDIA) |
| MVP Strategist | Qwen3.5-397B | NVIDIA | GLM-4.7 (Zhipu) > Groq |
| Data Engineer | GPT-OSS 120B | Cerebras | GPT-OSS (Groq) |
| Project Organizer | Qwen3-32B | Groq | GLM-4.7 (Zhipu) |
| QA Reviewer | GPT-OSS 120B | Cerebras | Llama 3.3 (Groq) |
| Verifier | GPT-OSS 120B | Cerebras | Llama 3.3 (Groq) |
| Narrative | GLM-4.7-Flash | Zhipu | DeepSeek V3.2 (NVIDIA) > Groq |

## API Keys Configuradas (20)
- GROQ_API_KEY (requerida)
- NVIDIA_API_KEY + NVIDIA_NIM_API_KEY (auto-copiada)
- CEREBRAS_API_KEY
- GEMINI_API_KEY
- SAMBANOVA_API_KEY
- OPENROUTER_API_KEY
- ZHIPU_API_KEY
- HUGGINGFACE_API_KEY (embeddings para memoria)
- SERPER_API_KEY (Google Search 2,500/mes)
- TAVILY_API_KEY (AI Search 1,000/mes)
- TELEGRAM_BOT_TOKEN
- ENIGMA_DATABASE_URL (Supabase PostgreSQL)
- MINIMAX_API_KEY
- DOF_DATABASE_URL
- AVALANCHE_RPC_URL
- AVALANCHE_WALLET_ADDRESS
- AVALANCHE_PRIVATE_KEY (deployer)
- VALIDATION_REGISTRY_ADDRESS
- APEX_PRIVATE_KEY (agent #1687)
- AVABUILDER_PRIVATE_KEY (agent #1686)

## MCP Servers Disponibles
| Server | Activar con | Agentes que lo usan |
|--------|-------------|---------------------|
| Filesystem | use_mcp=True | Architect, Data, Organizer |
| Web Search (gratis) | use_mcp=True | Research, Strategist, QA, Verifier, Narrative |
| Fetch URL | use_mcp=True | Architect, Research, Narrative |
| Knowledge Graph | get_memory_mcp() | Cualquier agente |

## A2A Server (Agent-to-Agent Protocol)
- **URL:** http://localhost:8000
- **Agent Card:** /.well-known/agent-card.json
- **Protocolo:** JSON-RPC + REST
- **Skills:** research, code-review, data-analysis, build-project, grant-hunt, content, daily-ops, enigma-audit
- **Arranque:** python main.py --mode a2a-server (o menu opcion 15)

## Wallets On-Chain (Avalanche C-Chain)
| Rol | Dirección | Token ID |
|-----|-----------|----------|
| Deployer | 0xB529f4f99ab244cfa7a48596Bf165CAc5B317929 | — |
| Apex Arbitrage | 0xcd595a299ad1d5D088B7764e9330f7B0be7ca983 | 1687 |
| AvaBuilder | 0x29a45b03F07D1207f2e3ca34c38e7BE5458CE71a | 1686 |

## Decisiones Arquitecturales
- Cada agente tiene su SOUL.md en agents/{nombre}/ (personalidad agnóstica, funciona con cualquier LLM)
- CONSTITUTION corta (~50 tokens) para no gastar contexto
- Contexto compartido en shared-context/ (THESIS.md, OPERATOR.md, SIGNALS.md, FEEDBACK-LOG.md)
- Outputs en output/ o output/{proyecto}/
- Pre-research programático: 5 búsquedas web ANTES del crew para garantizar datos reales
- Memoria con ChromaDB local — short-term, long-term, entity memory
- NVIDIA usa prefijo nvidia_nim/ (no openai/) + env var NVIDIA_NIM_API_KEY
- Zhipu GLM-4.7-Flash requiere extra_body={"enable_thinking": False} para evitar respuestas vacías
- Zero LLM para governance — toda decisión determinística (ConstitutionEnforcer, MetaSupervisor, ASTVerifier, Adversarial)
- crew_factory pattern — reconstruye crew en cada retry para saltar providers agotados
- JSONL append-only para audit trail completo (nunca overwrite)
- Singletons (ProviderManager, MetricsLogger, StorageFactory) tienen reset() — llamar al inicio de run_experiment()

## Lecciones Aprendidas
- GLM-4.7-Flash es 17x más rápido que NVIDIA para texto en español → promovido a primario para Narrative
- Cerebras Qwen3-235B y Qwen3-Coder-480B están listados en API pero NO disponibles (404 free tier)
- NVIDIA Qwen3-Coder-480B retorna "DEGRADED" — no usar
- Google Gemini embeddings (text-embedding-005) NO disponible en plan gratuito → usar HuggingFace
- Groq Llama 3.3 puede fallar con search_memory tool (mal formato tool-calling) → Cerebras maneja mejor
- ONNX embedder funciona local sin API key pero HuggingFace es más confiable via API
- SambaNova tiene límite de 24K tokens contexto → solo como backup
- Enigma FK constraint: dof_trust_scores.agent_id referencia agents.address — resolver via token_id (oags_identity="1687"), NO wallet address
- GovernanceResult tiene attrs: passed, score, violations, warnings — NO hard_violations/soft_violations
- web3 tx_hash.hex() ya incluye "0x" — no agregar doble prefijo en snowtrace URLs
- pytest tiene conflicto con web3 plugin — usar python3 -m unittest
- combined_trust_view es materialized view — requiere REFRESH MATERIALIZED VIEW CONCURRENTLY después de publicar scores

## Proyectos
- Ver config/projects.yaml para lista actualizada
- Enigma Scanner: CoinMarketCap para agentes ERC-8004 en Avalanche (Next.js 15 + Prisma 5 + Supabase)

## Diagramas FigJam
- Arquitectura completa: cb645608-3503-4150-891c-b6b91e1c2b86
- Boot Sequence v2: 7971ddf2-5e4f-4f5c-9d85-3e5a51f72fa3
