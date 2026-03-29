# SYSTEM — Fuente de Verdad del Kernel
# CrewAI Pro — Cyber Paisa / Enigma Group
# Actualizado: 2026-03-06

## Identidad
- **Operador:** Juan Carlos Quiceno — Cyber Paisa
- **Org:** Enigma Group — Holding Web3
- **Idioma:** Español por defecto

## Arquitectura
- 8 agentes especializados (SOUL.md cada uno)
- 11 crews (flujos de trabajo)
- 7 proveedores LLM gratuitos (Smart Router + Zhipu GLM)
- 6 categorías de tools (16 tools nativos)
- 4 MCP servers (filesystem, web_search, fetch, memory)
- A2A Server (8 skills expuestas via JSON-RPC)
- Memoria persistente (ChromaDB + HuggingFace embeddings)
- Pre-research programático (5 búsquedas antes del crew)
- Retry automático con backoff para rate limits
- Process: Sequential (sin planning)

## DOF — Deterministic Observability Framework
- **SDK:** dof-sdk 0.1.0 on PyPI
- **Codebase:** 27,000+ LOC, 22 core modules, 510 tests
- **On-chain:** 21 attestations on Avalanche C-Chain mainnet
- **Contract:** DOFValidationRegistry at 0x88f6043B091055Bbd896Fc8D2c6234A47C02C052

### 7 Governance Layers
1. **Constitution** — HARD rules (block) + SOFT rules (warn) via `core/governance.py`
2. **AST Verifier** — static analysis of generated code via `core/ast_verifier.py`
3. **Meta-Supervisor** — Q(0.4)+A(0.25)+C(0.2)+F(0.15) quality gate via `core/supervisor.py`
4. **Adversarial** — Red Team + Guardian + Arbiter protocol via `core/adversarial.py`
5. **Memory Governance** — bi-temporal versioning + constitutional decay via `core/memory_governance.py`
6. **Z3 Formal Verification** — 4 SMT theorems via `core/z3_verifier.py`
7. **Oracle Attestation** — ERC-8004 certificates + on-chain via `core/oracle_bridge.py`

### Bridges
- **Avalanche Bridge** — real on-chain tx via web3.py (`core/avalanche_bridge.py`)
- **Enigma Bridge** — dof_trust_scores to Supabase (`core/enigma_bridge.py`)
- **OAGS Bridge** — BLAKE3 identity + policy conversion (`core/oags_bridge.py`)
- **Merkle Tree** — batch N attestations in 1 transaction (`core/merkle_tree.py`)

### Protocol Access
- **MCP Server:** 10 tools, 3 resources, stdio JSON-RPC 2.0 (`dof/__main__.py`)
- **REST API:** 14 FastAPI endpoints (`dof/__main__.py`)
- **Dual Storage:** JSONL (default) + PostgreSQL (production via StorageFactory)
- **Framework-Agnostic:** GenericAdapter, LangGraphAdapter, CrewAIAdapter

## Reglas Constitucionales
1. Datos verificables con fuentes URL
2. JSON estructurado para output Pydantic
3. Español por defecto, inglés si el contexto lo requiere
4. Si no hay datos, decir "no encontré información verificable"
5. Conciso, sin relleno ni repetición
6. Citar fuentes con URL

## Proveedores LLM (7 activos, distribución balanceada)
| Rol | Primario | Proveedor | Fallback 1 | Fallback 2 |
|-----|----------|-----------|------------|------------|
| Code Architect | Kimi K2.5 | NVIDIA | Kimi K2 (Groq) | — |
| Research Analyst | Llama 3.3 70B | Groq | DeepSeek V3.2 (NV) | — |
| MVP Strategist | Qwen3.5-397B | NVIDIA | GLM-4.7 (Zhipu) | Groq |
| Data Engineer | GPT-OSS 120B | Cerebras | GPT-OSS 120B (Groq) | — |
| Organizer | Qwen3-32B | Groq | GLM-4.7 (Zhipu) | — |
| QA Reviewer | GPT-OSS 120B | Cerebras | Llama 3.3 (Groq) | — |
| Verifier | GPT-OSS 120B | Cerebras | Llama 3.3 (Groq) | — |
| Narrative | GLM-4.7-Flash | Zhipu | DeepSeek V3.2 (NV) | Groq |

## Búsqueda Web (fallback chain)
| Motor | Tipo | Límite |
|-------|------|--------|
| Serper | Google Search | 2,500/mes |
| Tavily | AI Search | 1,000/mes |
| DuckDuckGo | Fallback | Sin key, ilimitado* |

## Pipeline Research Crew (8/10 score)
```
Pre-research (5 búsquedas programáticas)
  ↓ datos reales inyectados
t1: Researcher (Groq) → analiza datos
t2: Strategist v1 (Cerebras) → plan MVP
t3: QA (Groq) → verifica con búsquedas
t4: Verifier (Cerebras) → score + feedback
t5: Strategist v2 (Cerebras) → plan FINAL mejorado
```

## Rate Limits (free tier)
| Provider | Límite | Agentes | Runs/día estimado |
|----------|--------|---------|-------------------|
| Groq | 12K TPM | 2 (Researcher, Organizer) | ~150 |
| Cerebras | 1M tok/día | 3 (Data, QA, Verifier) | ~200+ |
| NVIDIA | 1000 credits | 2 (Architect, Strategist) | ~500+ |
| Zhipu | Generoso | Fallback (Strategy, Narrative) | ~300+ |
| Serper | 2,500/mes | pre-research | ~80/día |
| Tavily | 1,000/mes | backup search | ~33/día |

## Crews Disponibles
1. research — Investigar y validar idea (pre-research + 5 agentes)
2. code-review — Revisar código
3. data — Analizar Excel/CSV
4. database — Analizar base de datos
5. full-mvp — MVP completo (6 agentes)
6. enigma-audit — Auditar agente/scanner/DB
7. grant-hunt — Buscar grants
8. content — Generar contenido
9. daily-ops — Rutina matutina
10. weekly-report — Reporte semanal
11. build — Generar proyecto con código real

## Memoria (ChromaDB + HuggingFace)
- **Short-term:** contexto dentro de la ejecución del crew
- **Long-term:** persiste aprendizajes entre ejecuciones
- **Entity memory:** recuerda entidades mencionadas
- **Embedder:** HuggingFace sentence-transformers/all-MiniLM-L6-v2 (384 dims)
- **Storage:** ChromaDB local (~/.cache/chroma/)
- **Governed Memory:** bi-temporal versioning + constitutional decay (core/memory_governance.py)

## MCP (Model Context Protocol) — 4 Servers
| Server | Comando | Uso |
|--------|---------|-----|
| Filesystem | @modelcontextprotocol/server-filesystem | Leer/escribir en output/ |
| Web Search | @pskill9/web-search | Google scraping, sin API key |
| Fetch | @anthropics/mcp-server-fetch | URL → markdown |
| Memory | @anthropics/mcp-server-memory | Knowledge graph persistente |

Activar MCP por agente: `create_agent(use_mcp=True)`

## DOF MCP Server (10 tools, 3 resources)
- `python -m dof mcp` — expone governance, AST, metrics, observability via JSON-RPC 2.0
- Tools: verify, check_governance, verify_ast, get_metrics, create_attestation, etc.
- Resources: constitution, metrics, attestation_registry

## DOF REST API (14 endpoints)
- `python -m dof api` — FastAPI server
- Endpoints: /health, /verify, /governance/check, /ast/verify, /metrics, /attestation/create, etc.

## A2A (Agent-to-Agent Protocol)
- **Server:** http://localhost:8000
- **Agent Card:** /.well-known/agent-card.json
- **Skills expuestas:** research, code-review, data-analysis, build-project, grant-hunt, content, daily-ops, enigma-audit
- **Protocolo:** JSON-RPC + REST simplificado
- **Arranque:** `python main.py --mode a2a-server` o menú opción 15

Ejemplo de uso externo:
```bash
curl -X POST http://localhost:8000 \
  -H "Content-Type: application/json" \
  -d '{"skill": "research", "input": "DeFi lending protocols"}'
```

## On-Chain (Avalanche C-Chain)
- **Contract:** DOFValidationRegistry at 0x88f6043B091055Bbd896Fc8D2c6234A47C02C052
- **Chain ID:** 43114 (Avalanche C-Chain mainnet)
- **Deployer:** 0xB529f4f99ab244cfa7a48596Bf165CAc5B317929
- **Agents:** Apex #1687 (0xcd59...a983), AvaBuilder #1686 (0x29a4...E71a)
- **Attestations:** 21 on-chain
- **Explorer:** https://snowtrace.io

## Enigma Integration
- **Table:** dof_trust_scores (DOF governance metrics, append-only)
- **View:** combined_trust_view (Centinela + DOF + community)
- **Agent resolution:** via token_id (oags_identity), NOT wallet address
- **Scores:** #1686 = 0.85, #1687 = 0.85 combined trust

## Seguridad
- Ejecución solo en output/ o ~/proyectos/
- Blocklist: rm -rf, sudo, chmod 777, dd, shutdown
- Git: sin --force, sin reset --hard
- Binarios whitelist: npm, pip, python3, node, docker, make, etc.
- Archivos bloqueados: .env, .pem, .key
