# SYSTEM — Kernel Source of Truth
# CrewAI Pro — Cyber Paisa / Enigma Group
# Updated: 2026-03-06

## Identity
- **Operator:** Juan Carlos Quiceno — Cyber Paisa
- **Org:** Enigma Group — Web3 Holding
- **Language:** Spanish by default

## Architecture
- 8 specialized agents (SOUL.md each)
- 11 crews (workflows)
- 7 free LLM providers (Smart Router + Zhipu GLM)
- 6 tool categories (16 native tools)
- 4 MCP servers (filesystem, web_search, fetch, memory)
- A2A Server (8 skills exposed via JSON-RPC)
- Persistent memory (ChromaDB + HuggingFace embeddings)
- Programmatic pre-research (5 searches before the crew)
- Automatic retry with backoff for rate limits
- Process: Sequential (no planning)

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

## Constitutional Rules
1. Verifiable data with URL sources
2. Structured JSON for Pydantic output
3. Spanish by default, English if context requires it
4. If no data, say "no verifiable information found"
5. Concise, without filler or repetition
6. Cite sources with URL

## LLM Providers (7 active, balanced distribution)
| Role | Primary | Provider | Fallback 1 | Fallback 2 |
|-----|----------|-----------|------------|------------|
| Code Architect | Kimi K2.5 | NVIDIA | Kimi K2 (Groq) | — |
| Research Analyst | Llama 3.3 70B | Groq | DeepSeek V3.2 (NV) | — |
| MVP Strategist | Qwen3.5-397B | NVIDIA | GLM-4.7 (Zhipu) | Groq |
| Data Engineer | GPT-OSS 120B | Cerebras | GPT-OSS 120B (Groq) | — |
| Organizer | Qwen3-32B | Groq | GLM-4.7 (Zhipu) | — |
| QA Reviewer | GPT-OSS 120B | Cerebras | Llama 3.3 (Groq) | — |
| Verifier | GPT-OSS 120B | Cerebras | Llama 3.3 (Groq) | — |
| Narrative | GLM-4.7-Flash | Zhipu | DeepSeek V3.2 (NV) | Groq |

## Web Search (fallback chain)
| Engine | Type | Limit |
|-------|------|--------|
| Serper | Google Search | 2,500/month |
| Tavily | AI Search | 1,000/month |
| DuckDuckGo | Fallback | No key, unlimited* |

## Research Crew Pipeline (8/10 score)
```
Pre-research (5 programmatic searches)
  ↓ real injected data
t1: Researcher (Groq) → analyzes data
t2: Strategist v1 (Cerebras) → MVP plan
t3: QA (Groq) → verifies with searches
t4: Verifier (Cerebras) → score + feedback
t5: Strategist v2 (Cerebras) → FINAL improved plan
```

## Rate Limits (free tier)
| Provider | Limit | Agents | Estimated runs/day |
|----------|--------|---------|-------------------|
| Groq | 12K TPM | 2 (Researcher, Organizer) | ~150 |
| Cerebras | 1M tok/day | 3 (Data, QA, Verifier) | ~200+ |
| NVIDIA | 1000 credits | 2 (Architect, Strategist) | ~500+ |
| Zhipu | Generous | Fallback (Strategy, Narrative) | ~300+ |
| Serper | 2,500/month | pre-research | ~80/day |
| Tavily | 1,000/month | backup search | ~33/day |

## Available Crews
1. research — Research and validate idea (pre-research + 5 agents)
2. code-review — Review code
3. data — Analyze Excel/CSV
4. database — Analyze database
5. full-mvp — Complete MVP (6 agents)
6. enigma-audit — Audit agent/scanner/DB
7. grant-hunt — Search for grants
8. content — Generate content
9. daily-ops — Morning routine
10. weekly-report — Weekly report
11. build — Generate project with real code

## Memory (ChromaDB + HuggingFace)
- **Short-term:** context within the crew execution
- **Long-term:** persists learnings between executions
- **Entity memory:** remembers mentioned entities
- **Embedder:** HuggingFace sentence-transformers/all-MiniLM-L6-v2 (384 dims)
- **Storage:** ChromaDB local (~/.cache/chroma/)
- **Governed Memory:** bi-temporal versioning + constitutional decay (core/memory_governance.py)

## MCP (Model Context Protocol) — 4 Servers
| Server | Command | Use |
|--------|---------|-----|
| Filesystem | @modelcontextprotocol/server-filesystem | Read/write in output/ |
| Web Search | @pskill9/web-search | Google scraping, no API key |
| Fetch | @anthropics/mcp-server-fetch | URL → markdown |
| Memory | @anthropics/mcp-server-memory | Persistent knowledge graph |

Activate MCP per agent: `create_agent(use_mcp=True)`

## DOF MCP Server (10 tools, 3 resources)
- `python -m dof mcp` — exposes governance, AST, metrics, observability via JSON-RPC 2.0
- Tools: verify, check_governance, verify_ast, get_metrics, create_attestation, etc.
- Resources: constitution, metrics, attestation_registry

## DOF REST API (14 endpoints)
- `python -m dof api` — FastAPI server
- Endpoints: /health, /verify, /governance/check, /ast/verify, /metrics, /attestation/create, etc.

## A2A (Agent-to-Agent Protocol)
- **Server:** http://localhost:8000
- **Agent Card:** /.well-known/agent-card.json
- **Exposed skills:** research, code-review, data-analysis, build-project, grant-hunt, content, daily-ops, enigma-audit
- **Protocol:** JSON-RPC + simplified REST
- **Startup:** `python main.py --mode a2a-server` or menu option 15

External usage example:
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
- **View:** combined_trust_view (Sentinel + DOF + community)
- **Agent resolution:** via token_id (oags_identity), NOT wallet address
- **Scores:** #1686 = 0.85, #1687 = 0.85 combined trust

## Security
- Execution only in output/ or ~/proyectos/
- Blocklist: rm -rf, sudo, chmod 777, dd, shutdown
- Git: no --force, no reset --hard
- Binary whitelist: npm, pip, python3, node, docker, make, etc.
- Blocked files: .env, .pem, .key
