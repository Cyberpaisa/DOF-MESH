# Intel: Claude Code Architecture + Ecosystem — Abril 2026
> Análisis de mejoras para DOF-MESH (main) e ideas de nuevos proyectos.
> Generado: 2026-04-10

---

## 1. Mejoras Concretas para DOF-MESH (main)

### 1.1 Async Generator para el Agent Loop
**Qué:** Reemplazar `while True` en `core/autonomous_daemon.py` por `async def run_cycle() -> AsyncGenerator[CycleEvent, None]`
**Dónde:** `core/autonomous_daemon.py`, `core/crew_runner.py`
**Impacto:** Cancellación limpia, composabilidad entre daemons, backpressure nativo, streaming al frontend.

### 1.2 Concurrency Classification en Tools
**Qué:** Clasificar tools como `READ_ONLY` vs `WRITE`. Read-only en paralelo (hasta 10), write en serie.
**Dónde:** `core/tool_hooks.py` (agregar `tool_class` al decorador), `core/crew_runner.py` (scheduler por clase)
**Impacto:** 2-5x speedup en crews multi-tool sin race conditions.

### 1.3 StreamingToolExecutor — Ejecutar Tools Mid-Stream
**Qué:** Ejecutar tool calls mientras el modelo genera texto, no esperar al final.
**Dónde:** Nuevo `core/streaming_executor.py` + integrar en `core/providers.py`
**Impacto:** Oculta 2-5s de latencia por tool call en sesiones del daemon.

### 1.4 Tool Result Budgeting
**Qué:** Resultados > N tokens → disco. Modelo recibe referencia + preview.
**Dónde:** `core/tool_hooks.py` (hook POST), `core/memory_manager.py` (storage con ChromaDB), umbral en `dof.constitution.yml`
**Impacto:** Previene context flooding con providers de 24K (SambaNova). Extiende vida de sesiones largas.

### 1.5 System Prompt con DYNAMIC_BOUNDARY
**Qué:** Parte estática (CONSTITUTION) antes del boundary = cache global. Context dinámico → `<system-reminder>` en primer user message.
**Dónde:** `core/governance.py` (CONSTITUTION como segmento estático), `core/claude_commander.py` (mover estado dinámico)
**Impacto:** Cache hit en segmento estático = reducción directa de costos. Con 9 agentes, el ahorro es proporcional al volumen.

### 1.6 4 Estrategias de Compactación Escalonada
**Qué:** Microcompact (gratis) → Snip (cortar turns viejos) → Auto Compact (LLM barato) → Context Collapse (fresh start)
**Dónde:** `core/memory_manager.py` (agregar `compact(strategy)` method), `core/autonomous_daemon.py` (invocar si `context_usage > threshold`)
**Impacto:** Habilita `max_cycles=0` (run forever) real sin context overflow.

### 1.7 Disk-Backed Task List con File Locking
**Qué:** Cola de tareas del mesh en `~/.dof/tasks/` con `filelock` para coordinación distribuida sin corrupción.
**Dónde:** `core/mesh_scheduler.py` (reemplazar priority queue en memoria)
**Impacto:** Coordinación real entre Builder/Guardian/Researcher daemon en `--multi` flag.

### 1.8 Karpathy Second Brain para DOF Docs
**Qué:** `docs/raw/` → `docs/wiki/` → `docs/outputs/` + `scripts/knowledge_health_check.py` mensual
**Dónde:** `docs/`, `scripts/`, `core/a_mem.py` (alimentar con wiki)
**Impacto:** Los aprendizajes de sesión dejan de perderse (problema documentado en MEMORY.md).

### 1.9 Self-Correction Loop en Governance
**Qué:** Antes de las 7 capas de governance, segundo pass de auto-crítica si `score < threshold`.
**Dónde:** `core/governance.py` como pre-pass opcional
**Impacto:** 85-90% mejora en calidad del output. Reduce false positives en `core/ast_verifier.py`.

### 1.10 Git Worktree Isolation para Workers
**Qué:** Cada worker spawneado usa su propio git worktree con `node_modules` symlink al repo principal.
**Dónde:** `scripts/spawn_claude_worker.sh`
**Impacto:** Aislamiento real de filesystem entre workers concurrentes. Sin conflictos de archivos.

### 1.11 AbortSignal Cascade en Sub-Agentes
**Qué:** Cancelar commander principal → señal se propaga a todos los workers hijos.
**Dónde:** `core/claude_commander.py`
**Impacto:** Cancelación limpia del `--multi` flag. Workers dejan de correr huérfanos.

### 1.12 UI: Cost USD + Context Window Bar
**Qué:** Mostrar costo acumulado del ciclo daemon y % de context usado en el frontend.
**Dónde:** `frontend/src/app/page.tsx`
**Impacto:** Trust mechanism — usuarios que ven qué hace el agente le dan más autonomía.

---

## 2. Ideas de Nuevos Proyectos

### DOF-UltraPlan
Sistema de planificación paralela con 3 agentes (architecture mapper, file finder, risk analyzer) + reviewer. `/ultraplan` en CLI DOF. Corre en la nube, terminal libre.
**Stack:** Python + CrewAI + claude-sonnet-4-6 + GitHub API + `core/node_mesh.py`

### DOF-RunCode Fork
Wallet USDC local en Base chain integrada en DOF-MESH para pay-per-use real de LLM sin cuenta Anthropic. Costo exacto por request en terminal.
**Stack:** ethers.js + Base mainnet (ya en contratos DOF) + `core/providers.py` modificado
**Inspirado en:** https://github.com/BlockRunAI/runcode

### DOF-Router
Router que selecciona automáticamente el modelo más barato capaz de resolver cada task. Z3 gate como clasificador de complejidad.
**Stack:** Python + LiteLLM + `core/z3_gate.py` como clasificador
**Inspirado en:** https://github.com/BlockRunAI/ClawRouter

### DOF-MCP Gateway
Expone DOF-MESH como servidor MCP. Cualquier agente externo (Claude Code, Cursor, GPT) puede verificar outputs con las 7 capas de governance como tools MCP.
**Stack:** Python + FastMCP + `core/governance.py` como tool + stdio/SSE transport + attestation on-chain

### DOF-SecondBrain
Knowledge base agéntico con estructura `raw/wiki/outputs` que se auto-organiza. Health check mensual automatizado detecta contradicciones entre documentos.
**Stack:** Python + `core/a_mem.py` (ya existe) + ChromaDB + `scripts/knowledge_health_check.py`

### DOF-Adversarial Benchmark Public
Dataset público de ataques de prompt injection probados contra DOF-MESH con resultados verificados on-chain. Permite comparar resiliencia a otros proyectos.
**Stack:** `core/adversarial.py` → benchmark runner → DOFProofRegistry attestation + GitHub Pages

---

## 3. MCPs Relevantes para DOF-MESH

### Prioridad Alta
| MCP | Relevancia | Caso de uso |
|---|---|---|
| **Chroma** | Crítica | Ya usa ChromaDB en `memory_manager.py` — MCP elimina código de integración manual |
| **Qdrant** | Alta | Alternativa con mejor performance para `core/a_mem.py` |
| **GitHub** | Alta | PRs automáticos de workers, CI status, worktree management |
| **Grafana** | Alta | Visualizar 5 métricas DOF (SS, PFI, GCR, RP, SSR) en tiempo real |
| **Docker** | Alta | Gestión del Citadel Swarm desde el daemon autónomo |

### Prioridad Media
| MCP | Relevancia | Caso de uso |
|---|---|---|
| Tavily / Exa | Media | Research agent (reemplaza web_search actual) |
| Playwright | Media | Testing E2E del frontend Next.js |
| Sentry | Media | Error tracking del daemon autónomo |
| Neo4j | Media | Grafo de conocimiento más potente para `a_mem.py` |
| PostgreSQL | Media | Queries directas a Supabase desde los agentes |

> **LÍMITE RECOMENDADO: 3-5 MCPs activos.** Más quema tokens en tool descriptions antes de cada request.
> **Combinación óptima para DOF-MESH:** Chroma + GitHub + Grafana

---

## 4. Patrones de Arquitectura Adoptables

| Patrón | Estado en DOF-MESH | Prioridad |
|---|---|---|
| Async Generator Loop | FALTA — usa `while True` | Alta |
| Concurrency Classification | FALTA — tools secuenciales | Alta |
| Tool Result Budgeting | FALTA — sin límite de tamaño | Alta |
| System Prompt Caching | FALTA — CONSTITUTION se regenera | Alta |
| 4 Estrategias Compactación | FALTA — ChromaDB sin compactación | Crítica para daemon ∞ |
| File-Based Locking | PARCIAL — inbox JSON sin lock | Media |
| AbortSignal Cascade | FALTA — workers huérfanos | Media |
| StreamingToolExecutor | FALTA — espera fin de stream | Media |
| CLAUDE.md 4 niveles | PARCIAL — falta nivel "local" formal | Baja |
| UI Cost + Context Bar | FALTA — frontend sin métricas de costo | Media |

---

## 5. Links y Referencias Completos

### Repositorios GitHub
```
https://github.com/BlockRunAI/ClawRouter          # Router multi-modelo
https://github.com/BlockRunAI/runcode              # Alternativa Claude Max con wallet Base
https://github.com/jerryjliu/liteparse_samples     # Parsing de documentos
https://github.com/Anil-matcha/Open-Higgsfield-AI  # Video generation open source
https://github.com/agno-agi/dash                   # Dashboard para agentes Agno
https://github.com/eugeniughelbur/obsidian-second-brain  # Second brain Obsidian
```

### NPM
```
https://www.npmjs.com/package/@blockrun/runcode    # RunCode CLI
```

### MCP Servers — Search
```
Tavily MCP:     https://tavily.com
Exa:            https://exa.ai
Brave Search:   https://brave.com/search/api/
Perplexity:     https://www.perplexity.ai/api
Context7:       https://context7.com
```

### MCP Servers — Web Scraping
```
Firecrawl:   https://firecrawl.dev
Apify:       https://apify.com
Crawl4AI:    https://github.com/unclecode/crawl4ai
Bright Data: https://brightdata.com
```

### MCP Servers — Browser
```
Playwright:  https://github.com/microsoft/playwright-mcp
Browserbase: https://browserbase.com
```

### MCP Servers — Dev
```
GitHub MCP: https://github.com/github/github-mcp-server
Linear:     https://linear.app/integrations/mcp
Sentry:     https://sentry.io/integrations/mcp
Vercel:     https://vercel.com/integrations/mcp
```

### MCP Servers — Bases de Datos
```
Supabase:   https://supabase.com/docs/guides/getting-started/mcp
MongoDB:    https://github.com/mongodb-labs/mongodb-mcp-server
Neo4j:      https://github.com/neo4j-contrib/mcp-neo4j
```

### MCP Servers — Vector / Memory
```
Pinecone:   https://docs.pinecone.io/integrations/mcp
Qdrant:     https://github.com/qdrant/mcp-server-qdrant
Chroma:     https://github.com/chroma-core/chroma-mcp
```

### MCP Servers — Infra / Negocio
```
Cloudflare: https://developers.cloudflare.com/mcp
Docker:     https://github.com/docker/mcp-servers
Grafana:    https://grafana.com/docs/grafana/latest/developers/mcp/
Stripe:     https://docs.stripe.com/building-with-llms/mcp
HubSpot:    https://developers.hubspot.com/mcp
Zapier:     https://zapier.com/mcp
```

---

*Informe generado automáticamente — DOF Mesh Legion — 2026-04-10*
