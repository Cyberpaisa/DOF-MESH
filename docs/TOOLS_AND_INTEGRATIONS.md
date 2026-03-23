# Tools & Integrations — DOF Agent Ecosystem

## Estado: Marzo 22, 2026

Documentación de todas las herramientas evaluadas para el ecosistema de agentes DOF + OpenClaw.

---

## 1. ClawRouter — LLM Router Inteligente
- **URL**: https://github.com/BlockRunAI/ClawRouter
- **Qué es**: Router de LLM open-source con 44+ modelos, fallback automático de 8 niveles
- **Por qué lo necesitamos**: OpenClaw con providers directos (Cerebras, Groq, NVIDIA) tiene problemas constantes: keys expiradas, rate limits, modelos no disponibles en free tier, timeouts
- **Características clave**:
  - Sin API keys — usa wallet USDC via x402
  - Routing local en <1ms con clasificador de 14 dimensiones
  - Tier free con NVIDIA GPT-OSS-120B
  - Se instala como plugin de OpenClaw directamente
  - Perfiles: auto (balanced), eco (cheapest), premium (best), free
- **Instalación**: `curl -fsSL https://blockrun.ai/ClawRouter-update | bash`
- **Estado**: INSTALANDO

## 2. DeerFlow — Super Agent Harness (ByteDance)
- **URL**: https://github.com/bytedance/deer-flow
- **Qué es**: Framework open-source de ByteDance para orquestar agentes AI en tareas complejas multi-paso
- **Características clave**:
  - Ejecución en sandbox (Docker/local/Kubernetes)
  - Sub-agentes paralelos con contextos aislados
  - Skills modulares (research, reportes, presentaciones)
  - Memoria persistente local
  - Integración con Telegram, Slack, Feishu
  - Compresión de contexto para workflows largos
  - Soporte MCP para tools custom
- **Relevancia para DOF**: Complementa nuestra arquitectura de agentes. Podemos adoptar su modelo de sub-agentes paralelos y sandbox isolation. Su integración con Telegram es similar a la nuestra con OpenClaw.
- **Basado en**: LangGraph + LangChain
- **Estado**: EVALUANDO — muy relevante para integración futura

## 3. SocratiCode — Codebase Intelligence
- **URL**: https://github.com/giancarloerra/SocratiCode
- **Qué es**: MCP server que indexa el codebase para búsqueda semántica + keyword (BM25) con Reciprocal Rank Fusion
- **Características clave**:
  - AST-aware chunking (divide por funciones/clases, no por líneas arbitrarias)
  - Grafos de dependencias polyglot (18+ lenguajes)
  - Multi-agent ready: múltiples agentes comparten un solo índice
  - File locking cross-process automático
  - Indexación incremental y resumable
  - Zero config — auto-pull de Docker images
- **Relevancia para DOF**: Nuestros 14 agentes podrían compartir contexto semántico del codebase DOF (27K+ LOC). QA Vigilante y Ralph Code se beneficiarían enormemente.
- **Instalación**: Plugin de Claude Code o `npx -y socraticode`
- **Requiere**: Docker
- **Estado**: EVALUANDO — alta prioridad para Phase 2

## 4. git-surgeon — Git History Manipulation
- **URL**: https://github.com/konfou/git-surgeon
- **Qué es**: Subcomando Git para workflows centrados en cambios (inspirado en Jujutsu)
- **Características clave**:
  - Rewrite commits (reword, edit, squash, fixup, drop)
  - Reorganizar commits (swap, move, split)
  - Editar metadata (author, email, dates)
  - Reflog y restauración de operaciones
- **Relevancia para DOF**: Útil para limpiar historial de commits antes de releases. Nuestro repo tiene 107+ commits que podrían beneficiarse de reorganización.
- **Instalación**: `pip install -e .` o copiar script a PATH
- **Estado**: EVALUANDO — útil pero no crítico

## 5. novyx-mcp — Persistent Memory for AI Agents
- **URL**: https://github.com/novyxlabs/novyx-mcp
- **Qué es**: MCP server con 64 tools para memoria persistente, knowledge graphs, audit trails
- **Características clave**:
  - Almacenamiento y recuperación semántica de observaciones
  - Knowledge graphs con relaciones entre entidades
  - Audit trails criptográficos
  - Rollback point-in-time
  - Context spaces compartidos para multi-agente
  - Replay para time-travel debugging
  - Cortex: consolidación autónoma y análisis de patrones
  - Draft workflows (proponer cambios para review antes de commit)
- **Relevancia para DOF**: Complementa nuestra persistencia JSONL. Los context spaces compartidos permitirían que nuestros 14 agentes compartan memoria de trabajo. Los audit trails criptográficos se alinean con nuestra filosofía de verificabilidad (Z3 + blockchain).
- **Instalación**: `pip install novyx-mcp` + API key de novyxlabs.com (free: 5000 memories/month)
- **Estado**: EVALUANDO — alta prioridad si la integración con OpenClaw es viable

## 6. sinc-llm — Nyquist-Shannon para Prompts
- **URL**: Mencionado en Twitter (pip install sinc-llm)
- **Qué es**: Aplica el teorema de Nyquist-Shannon (1949) a prompts de LLM. Trata el prompt como señal con 6 bandas, detecta aliasing por undersampling.
- **Relevancia para DOF**: Interesante para optimizar los prompts de nuestros agentes. Si cada prompt es una señal con 6 bandas y se muestrea una sola vez, el aliasing explica por qué a veces los agentes no captan la instrucción completa.
- **Estado**: EVALUANDO — experimental

---

## Problemas Resueltos con Providers (Log)

### Provider Status (Marzo 22, 2026)
| Provider | Modelo | Status | Error |
|----------|--------|--------|-------|
| Cerebras | qwen-3-235b-a22b-instruct-2507 | FUNCIONA pero TIMEOUT | 235B params demasiado lento |
| Cerebras | llama3.1-8b | ERROR 400 | No body en respuesta |
| Cerebras | gpt-oss-120b | ERROR 404 | No disponible free tier |
| Cerebras | zai-glm-4.7 | ERROR 404 | No disponible free tier |
| Groq | llama-3.3-70b-versatile | ERROR 401 | API key expirada |
| NVIDIA | meta/llama-3.3-70b-instruct | ERROR | Provider no registrado en OpenClaw |
| NVIDIA NIM | nvidia_nim/meta/llama-3.3-70b-instruct | ERROR | Formato de modelo no reconocido |
| SambaNova | Meta-Llama-3.3-70B-Instruct | ERROR | Provider no soportado por OpenClaw |
| Ollama | enigma:latest / llama3:latest | ERROR | Requiere `openclaw configure` interactivo |

### Solución: ClawRouter
ClawRouter resuelve TODOS estos problemas:
- 44+ modelos con fallback automático de 8 niveles
- Sin API keys (wallet USDC)
- Tier free con NVIDIA GPT-OSS-120B
- Se integra como plugin de OpenClaw

---

## Arquitectura Actual del Ecosistema

```
┌─────────────────────────────────────────────┐
│              Interfaces                      │
│  Telegram ─ Mission Control ─ CLI ─ A2A     │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│          OpenClaw Gateway (:18789)           │
│  14 Agentes Especializados                  │
│  ClawRouter → 44+ modelos con fallback      │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│          DOF Governance Layer                │
│  Constitution → Z3 Proofs → On-Chain        │
│  986 tests │ 8/8 PROVEN │ 48+ attestations  │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│          Persistence & Memory               │
│  JSONL traces │ ChromaDB │ novyx-mcp (eval) │
│  Blockchain (Avalanche + Base)              │
└─────────────────────────────────────────────┘
```

---

## Roadmap de Integración

### Phase 1 (Ahora)
- [x] OpenClaw Gateway funcionando
- [x] 14 agentes configurados
- [ ] ClawRouter instalado y funcionando
- [ ] Telegram bot respondiendo consistentemente

### Phase 2 (Próximo)
- [ ] SocratiCode para indexación semántica del codebase
- [ ] novyx-mcp para memoria persistente compartida
- [ ] DeerFlow evaluación de sub-agentes paralelos

### Phase 3 (Futuro)
- [ ] git-surgeon para gestión avanzada de historial
- [ ] sinc-llm para optimización de prompts
- [ ] Full A2A protocol entre agentes DOF y agentes externos

---

## Links Rápidos

| Tool | URL | Status |
|------|-----|--------|
| ClawRouter | https://github.com/BlockRunAI/ClawRouter | INSTALANDO |
| DeerFlow | https://github.com/bytedance/deer-flow | EVALUANDO |
| SocratiCode | https://github.com/giancarloerra/SocratiCode | EVALUANDO |
| git-surgeon | https://github.com/konfou/git-surgeon | EVALUANDO |
| novyx-mcp | https://github.com/novyxlabs/novyx-mcp | EVALUANDO |
| sinc-llm | pip install sinc-llm | EVALUANDO |
| DOF Dashboard | https://dof-agent-web.vercel.app/ | ACTIVO |
| DOF GitHub | https://github.com/Cyberpaisa/deterministic-observability-framework | ACTIVO |

---

## 7. DeerFlow 2.0 — Super Agent Harness (ByteDance) — Análisis Profundo
- **URL**: https://github.com/bytedance/deer-flow
- **Stars**: 33,190 | **Forks**: 4,033 | **License**: MIT
- **Versión**: 2.0 (reescritura completa) | **Python**: 3.12+ | **Node**: 22+
- **Creado**: Mayo 2025 | **#1 GitHub Trending**: Feb 28, 2026

### Arquitectura
```
Client (Browser / Telegram / Slack / Feishu)
              |
        Nginx (port 2026)
         /          |           \
LangGraph Server  Gateway API   Frontend
  (port 2024)    (port 8001)   (port 3000)
```

### Componentes Clave
- **Lead Agent**: Orquestador único con 11 middlewares en cadena
- **Sub-Agents**: Max 3 concurrentes, contexto aislado, timeout 15min
- **Sandbox**: Local/Docker/K8s con sistema de paths virtuales
- **Skills**: 17 built-in, carga progresiva (solo cuando se necesitan)
- **MCP**: stdio/SSE/HTTP con OAuth
- **Canales IM**: Telegram, Slack, Feishu con sesiones por usuario
- **Memoria**: JSON con extracción LLM (100 facts max, confidence 0.7+)
- **Checkpointing**: memory/sqlite/postgres

### Lo que nos sirve para DOF
1. **Sandbox isolation** — paths virtuales (`/mnt/user-data/*` → paths reales)
2. **Context compression** — SummarizationMiddleware con triggers configurables
3. **Progressive skill loading** — solo inyectar skills cuando la tarea lo requiere
4. **Deferred tool loading** — MCP tools listed by name, loaded on demand
5. **IM channel architecture** — message bus + store + manager pattern
6. **Harness/App boundary** — one-way dependency enforced by CI test

### Lo que NO adoptamos
1. **Zero governance** — DeerFlow no tiene CONSTITUTION ni HARD/SOFT_RULES
2. **No determinismo** — LLM decide todo el routing, no hay seeds/PRNGs
3. **No métricas formales** — no hay SS, PFI, RP, GCR, SSR
4. **LangChain dependency** — vendor lock-in que DOF evita
5. **JSON memory** — 100 facts max no escala para 14 agentes

### Providers LLM Soportados
OpenAI, Anthropic, Google Gemini, DeepSeek, Volcengine (Doubao), Moonshot (Kimi), OpenRouter, Novita AI, MiniMax, Ollama (via OpenAI-compatible endpoint)

---

## 8. OpenClaw — Guía de Deployment (de video Fazt)

### 5 Opciones de Instalación

| Opción | Ideal para | RAM/CPU | Notas |
|--------|-----------|---------|-------|
| **Raspberry Pi** | Agente dedicado 24/7, bajo consumo | ARM64 | Usar SSD, no SD card |
| **Docker** | Aislamiento en PC existente | Variable | Contenedor aislado |
| **VPS** | Uso profesional 24/7 | 4-32GB / 2-8 CPU | IP fija, recomendado para producción |
| **Mac Mini (Apple Silicon)** | Modelos locales grandes | M1/M2/M3/M4 | Memoria unificada, hasta 70B params |
| **Máquina Virtual** | Máxima seguridad | Variable | "Split Brain" — agente aislado |

### Recomendaciones de Hardware para VPS
- **Básico**: 4GB RAM / 2 CPU — tareas sencillas
- **Intermedio**: 8GB RAM / 4 CPU — web scraping, navegador
- **Avanzado**: 16-32GB RAM — múltiples proyectos en paralelo

### Nuestro Setup Actual
- **Mac M4 Max** — modelo Mac Mini con Silicon avanzado
- **OpenClaw v2026.3.13** — gateway local en port 18789
- **ClawRouter** — 44+ modelos via x402, tier free con NVIDIA GPT-OSS-120B
- **14 agentes** — configurados con workspaces aislados
- **Telegram** — @Ciberpaisa_bot respondiendo via ClawRouter

---

## Comparativa: DeerFlow vs DOF vs OpenClaw

| Dimensión | DeerFlow | DOF | OpenClaw |
|-----------|----------|-----|----------|
| Filosofía | LLM decide todo | Governance determinístico | Gateway multi-agente |
| Agentes | 1 lead + 2 sub | 8 especializados | 14 configurables |
| Governance | Ninguna | CONSTITUTION + HARD/SOFT | Allowlists de tools |
| Observabilidad | LangSmith (opcional) | JSONL + 5 métricas formales | Logs + sessions |
| Sandbox | Local/Docker/K8s | Ninguno | Workspaces aislados |
| MCP | stdio/SSE/HTTP + OAuth | 4 servers | Plugin system |
| IM Channels | Telegram/Slack/Feishu | Telegram (via OpenClaw) | Telegram/Discord/WhatsApp |
| Skills | 17 built-in | 18 via Skills Engine | Skills via plugins |
| Blockchain | Ninguno | Avalanche + Base | Ninguno |
| Tests | ~50 archivos | 986 tests | N/A |

---

## 9. Ouro Loop — Bounded Autonomy for AI Agents
- **URL**: https://github.com/VictorVVedtion/ouro-loop
- **Qué es**: Framework open-source que otorga autonomía completa a agentes AI dentro de constraints runtime-enforced. Filosofía: "Para dar autonomía absoluta, primero ata con restricciones absolutas."
- **Instalación**: `pip install ouro-loop`
- **Licencia**: MIT | **Tests**: 507 | **Dependencias**: Zero (pure Python)

### El Loop de 6 Etapas
1. **BOUND** — Definir constraints antes de codificar (DANGER ZONES, NEVER DO, IRON LAWS)
2. **MAP** — 6 preguntas diagnósticas antes de proponer soluciones
3. **PLAN** — Descomponer por complejidad. RED-GREEN-REFACTOR-COMMIT
4. **BUILD** — Un commit lógico por unidad de trabajo
5. **VERIFY** — 3 capas: 5 Gates (EXIST, RELEVANCE, ROOT_CAUSE, RECALL, MOMENTUM) + Self-Assessment + External Review Triggers
6. **LOOP/REMEDIATE** — Si falla, NO pausar. Consultar decision tree, revertir, intentar alternativas

### Claude Code Hooks (5 enforcement scripts)
| Hook | Trigger | Función |
|------|---------|---------|
| `bound-guard.sh` | PreToolUse | Bloquea edits en DANGER ZONES |
| `root-cause-tracker.sh` | PostToolUse | Warning 3+ edits al mismo archivo |
| `drift-detector.sh` | PreToolUse | Warning 5+ cambios de directorio |
| `momentum-gate.sh` | PostToolUse | Detecta parálisis (ratio 3:1 read/write) |
| `recall-gate.sh` | PreCompact | Re-inyecta BOUND antes de compresión |

### Relevancia para DOF
- **BOUND complementa governance**: DOF enforce HARD_RULES en output, Ouro Loop enforce en input — defense in depth
- **Verification Gates como pre-supervisor**: Filtran iteraciones inválidas ANTES del supervisor Q+A+C+F
- **Reflective Log (WHAT/WHY/PATTERN)** en JSONL: indexable en ChromaDB para memoria comportamental
- **ROOT_CAUSE gate**: Detecta symptom-chasing — útil para nuestros provider chain issues
- **Sentinel** para auditoría continua de los 25+ módulos DOF
- **Limitación**: Single-agent focus, necesita adaptación para 14 agentes concurrentes
- **Estado**: EVALUANDO — complemento natural para governance

---

## 10. Hyperspace — Proof-of-Intelligence Blockchain + Distributed Autoresearch
- **URL**: https://agents.hyper.space | https://github.com/hyperspaceai/agi
- **CLI**: `curl -fsSL https://agents.hyper.space/cli | bash`
- **Qué es**: Primera blockchain agentic con consenso Proof-of-Intelligence (PoI). Red P2P donde agentes autónomos hacen investigación ML distribuida, compartiendo estrategias via gossip.

### Origen: Karpathy's Autoresearch
- **Repo**: https://github.com/karpathy/autoresearch
- Un agente LLM lee código de training, propone cambios, ejecuta experimento de 5 min, evalúa val_bpb, itera
- ~12 experimentos/hora, ~100 overnight con 1 GPU, 1 agente, 1 archivo
- Limitación: 1 agente en 1 GPU explora un solo camino a la vez

### Hyperspace lo distribuye
- Cada nodo con `hyperspace start --agent --research` se convierte en investigador ML autónomo
- 35 agentes en 35 máquinas = 3,500 experimentos overnight + aprenden unos de otros via P2P gossip
- **ResearchDAG**: Estructura tipo Git para investigación — branches, merges, citations verificables
- **Agent Virtual Machine (AVM)**: Ejecuta código en ambiente aislado con pruebas criptográficas (zkWASM)
- **GossipSub**: Protocolo P2P para compartir hallazgos entre agentes
- **Verificación compute**: matmul challenges criptográficos prueban que el agente tiene el compute que dice

### Ecosistema Hyperspace
| Producto | Agentes | Descripción |
|----------|---------|-------------|
| **Autoswarms** | Clusters | Self-organizing agent clusters, 14,832 experiments, 237 agents |
| **Autoquant** | 135 | Bloomberg distribuido, Sharpe 1.32 |
| **Autoskill** | 90 | Skill factory, 1,251 commits, WASM sandbox, selección Darwiniana |
| **Autosearcher** | N/A | Motor de búsqueda distribuido, 7-stage pipeline, NDCG optimization |
| **Warps** | N/A | Self-mutating agent configs |
| **ResearchDAGs** | N/A | Git para investigación, branches + merges + citations verificables |

### Network Feed (Live)
- Agentes como WarpForge, WiseCipher, HexBeam, ArcMesh, WarpTitan activos en red P2P
- Experimentos con val_loss tracking: WarpTitan logró -4.4% vs baseline (3.7858)
- Agentes corriendo ollama:glm-4.7-flash con 9 capabilities, 233 points
- Milestones: 8-10 peers conectados, compartiendo observaciones y resultados

### Primer Overnight Run de Autoresearch Distribuido
- Agentes self-organized, compartieron estrategias via P2P gossip
- Iteraron en configs de modelo sin guía humana
- Caso de uso demo: astrophysics researcher agent → train model → write papers → peer review por frontier lab models → surface breakthroughs → feedback loop
- Cualquiera puede unirse desde browser o CLI

### Relevancia para DOF
- **PoI como verificación de compute**: complementa nuestro Z3 + blockchain (probar que el agente realmente hizo trabajo computacional)
- **ResearchDAG para rastrear investigación**: nuestros R&D Council memos podrían vivir en un DAG verificable
- **Autoskill patterns**: selección Darwiniana de skills — nuestra Skills Engine v2.0 podría adoptar esto
- **P2P gossip para multi-agente**: alternativa a nuestro gateway centralizado
- **Estado**: EVALUANDO — altísimo potencial de integración

---

## 11. CopilotKit — Generative UI para React
- **URL**: https://github.com/copilotkit/generative-ui
- **Qué es**: Framework para embeber copilots AI en apps React con UI generativa
- **Relevancia para DOF**: Mission Control (Next.js + React) podría usar CopilotKit para un copilot nativo que interactúe con paneles, genere visualizaciones dinámicas, y responda preguntas sobre el estado del sistema
- **Estado**: EVALUANDO — pendiente análisis profundo

---

## 12. NVIDIA Deep Agents — Enterprise Search con LangChain
- **URL**: https://developer.nvidia.com/blog/how-to-build-deep-agents-for-enterprise-search-with-nvidia-ai-q-and-langchain/
- **Qué es**: Guía de NVIDIA para construir agentes deep search empresariales usando AI-Q + LangChain
- **Relevancia para DOF**: Patrones de búsqueda enterprise aplicables a nuestra memoria (ChromaDB) y observabilidad (JSONL traces). Potencial para search semántico sobre 27K+ LOC y 986 tests.
- **Estado**: EVALUANDO — pendiente análisis profundo

---

## 13. Karpathy's Autoresearch — Autonomous ML Training
- **URL**: https://github.com/karpathy/autoresearch
- **Qué es**: Sistema donde un agente LLM experimenta autónomamente con training de modelos. Lee código, propone cambios, ejecuta 5 min, evalúa val_bpb, itera.
- **Archivos**: `prepare.py` (datos, constantes — humano controla) + `train.py` (modelo, optimizer — agente modifica)
- **Budget fijo**: 5 min por experimento = ~12/hora, ~100 overnight
- **Relevancia para DOF**: El loop experimentar-evaluar-iterar es análogo a nuestro governance cycle. Podríamos aplicar esto para auto-optimización de prompts y configuraciones de agentes.
- **Estado**: DOCUMENTADO

---

## 14. awesome-chatgpt-prompts — Prompt Engineering Reference
- **URL**: https://github.com/f/awesome-chatgpt-prompts | https://prompts.chat
- **Stars**: 143,000+ | Citado por Forbes, Harvard, Columbia | 40+ academic citations
- **Qué es**: 150+ prompts curados por rol. Principio: Role = Context = Quality
- **Estructura de un buen prompt**: 4 elementos — Role + Context + Output Format + Constraints
- **Incluye**: Curso gratuito de prompt engineering (25+ capítulos)
- **Relevancia para DOF**: Referencia para optimizar system prompts de nuestros 14 agentes. La filosofía de "Act as..." se puede combinar con nuestra CONSTITUTION injection.
- **Estado**: REFERENCIA

---

## 15. Curated Skills & Repos — Top 90 AI Tools (Marzo 2026)

### Claude Skills Esenciales (22 instalables)

**Document & Office (Official Anthropic)**
| # | Skill | URL |
|---|-------|-----|
| 01 | PDF Processing | https://github.com/anthropics/skills/tree/main/skills/pdf |
| 02 | DOCX | https://github.com/anthropics/skills/tree/main/skills/docx |
| 03 | PPTX | https://github.com/anthropics/skills/tree/main/skills/pptx |
| 04 | XLSX | https://github.com/anthropics/skills/tree/main/skills/xlsx |
| 05 | Doc Co-Authoring | https://github.com/anthropics/skills/tree/main/skills/doc-coauthoring |

**Design & Creative**
| # | Skill | URL |
|---|-------|-----|
| 06 | Frontend Design (277k+ installs) | https://github.com/anthropics/skills/tree/main/skills/frontend-design |
| 07 | Canvas Design | https://github.com/anthropics/skills/tree/main/skills/canvas-design |
| 08 | Algorithmic Art (p5.js) | https://github.com/anthropics/skills/tree/main/skills/algorithmic-art |
| 09 | Theme Factory | https://github.com/anthropics/skills/tree/main/skills/theme-factory |
| 10 | Web Artifacts Builder | https://github.com/anthropics/skills/tree/main/skills/web-artifacts-builder |

**Dev & Engineering**
| # | Skill | URL |
|---|-------|-----|
| 11 | Superpowers (96k+ stars) | https://github.com/obra/superpowers |
| 12 | Systematic Debugging (S9.2) | https://github.com/obra/superpowers |
| 13 | File Search (S9.0) | https://github.com/massgen/massgen |
| 14 | Context Optimization (13.9k stars) | https://github.com/muratcankoylan/agent-skills-for-context-engineering |
| 15 | Skill Creator (Official) | https://github.com/anthropics/skills/tree/main/skills/skill-creator |
| 16 | Remotion Best Practices (117k weekly) | https://github.com/remotion-dev/remotion |

**Marketing & SEO**
| # | Skill | URL |
|---|-------|-----|
| 17 | Marketing Skills (20+ skills) | https://github.com/coreyhaines31/marketingskills |
| 18 | Claude SEO (12 sub-skills) | https://github.com/AgriciDaniel/claude-seo |
| 19 | Brand Guidelines | https://github.com/anthropics/skills/tree/main/skills/brand-guidelines |

**Knowledge & Learning**
| # | Skill | URL |
|---|-------|-----|
| 20 | NotebookLM Integration | https://github.com/PleasePrompto/notebooklm-skill |
| 21 | Obsidian Skills (by CEO) | https://github.com/kepano/obsidian-skills |
| 22 | Excel MCP Server | https://github.com/haris-musa/excel-mcp-server |

### MCP Servers Imprescindibles
| Server | Descripción | URL |
|--------|-------------|-----|
| **Tavily** | Search para AI agents, datos estructurados | https://github.com/tavily-ai/tavily-mcp |
| **Context7** | Docs up-to-date en contexto LLM | https://github.com/upstash/context7 |
| **Task Master AI** | PRD → tasks con dependencies | https://github.com/eyaltoledano/claude-task-master |

### GitHub Repos — Agent Frameworks
| # | Repo | Stars | URL |
|---|------|-------|-----|
| 23 | OpenClaw | 210k+ | https://github.com/openclaw/openclaw |
| 24 | AutoGPT | — | https://github.com/Significant-Gravitas/AutoGPT |
| 25 | LangGraph | 26.8k | https://github.com/langchain-ai/langgraph |
| 26 | OWL (GAIA #1) | — | https://github.com/camel-ai/owl |
| 27 | Dify | — | https://github.com/langgenius/dify |
| 28 | CrewAI | — | https://github.com/crewAIInc/crewAI |
| 29 | CopilotKit | — | https://github.com/CopilotKit/CopilotKit |

### GitHub Repos — Local AI
| # | Repo | URL |
|---|------|-----|
| 30 | Ollama | https://github.com/ollama/ollama |
| 31 | Open WebUI | https://github.com/open-webui/open-webui |
| 32 | LlamaFile | https://github.com/Mozilla-Ocho/llamafile |
| 33 | Unsloth (2x faster fine-tune) | https://github.com/unslothai/unsloth |

### GitHub Repos — Workflow & Automation
| # | Repo | URL |
|---|------|-----|
| 34 | n8n (400+ integrations) | https://github.com/n8n-io/n8n |
| 35 | Langflow (140k stars) | https://github.com/langflow-ai/langflow |
| 36 | Huginn (self-hosted agents) | https://github.com/huginn/huginn |

### GitHub Repos — Search & Data
| # | Repo | URL |
|---|------|-----|
| 37 | GPT Researcher | https://github.com/assafelovic/gpt-researcher |
| 38 | Firecrawl | https://github.com/mendableai/firecrawl |
| 39 | Vanna AI (NL→SQL) | https://github.com/vanna-ai/vanna |

### GitHub Repos — Dev Tools
| # | Repo | URL |
|---|------|-----|
| 40 | Codebase Memory MCP | https://github.com/DeusData/codebase-memory-mcp |
| 41 | DSPy (Stanford) | https://github.com/stanfordnlp/dspy |
| 42 | Spec Kit (GitHub) 50k+ | https://github.com/github/spec-kit |
| 43 | NVIDIA NemoClaw | https://github.com/NVIDIA/NemoClaw |

### Curated Collections
| # | Repo | URL |
|---|------|-----|
| 44 | Awesome Claude Skills (22k+) | https://github.com/travisvn/awesome-claude-skills |
| 45 | Anthropic Skills (Official) | https://github.com/anthropics/skills |
| 46 | Awesome Agents (100+) | https://github.com/kyrolabs/awesome-agents |
| 47 | MAGI//ARCHIVE (daily feed) | https://tom-doerr.github.io/repo_posts/ |

### 40 Fresh Repos Worth Watching

**Agent Orchestration**
- gstack — Claude Code as virtual team: https://github.com/garrytan/gstack
- cmux — Multiple Claude agents parallel: https://github.com/craigsc/cmux
- figaro — Orchestrate Claude fleets: https://github.com/byt3bl33d3r/figaro
- claude-squad — Terminal agents: https://github.com/smtg-ai/claude-squad
- deer-flow (ByteDance): https://github.com/bytedance/deer-flow
- SWE-AF — One API call → eng team: https://github.com/Agent-Field/SWE-AF
- AIlice — Dynamic agents: https://github.com/myshell-ai/AIlice
- Agent Alchemy: https://github.com/sequenzia/agent-alchemy

**Agent Infrastructure & Security**
- Ghost OS — AI on Mac apps: https://github.com/ghostwright/ghost-os
- e2b/desktop — Isolated VMs: https://github.com/e2b-dev/desktop
- container-use (Dagger): https://github.com/dagger/container-use
- Canopy — Encrypted P2P mesh: https://github.com/kwalus/Canopy
- agent-governance-toolkit (Microsoft): https://github.com/microsoft/agent-governance-toolkit
- claude-code-security-review (Anthropic): https://github.com/anthropics/claude-code-security-review
- promptfoo — Security testing: https://github.com/promptfoo/promptfoo

**Memory & Context**
- Mem9: https://github.com/mem9-ai/mem9
- Codefire: https://github.com/websitebutlers/codefire-app
- Memobase: https://github.com/memodb-io/memobase

**Coding Agents**
- Qwen Code: https://github.com/QwenLM/qwen-code
- gptme: https://github.com/gptme/gptme
- Claude Inspector: https://github.com/kangraemin/claude-inspector
- TDD Guard: https://github.com/nizos/tdd-guard
- rendergit (Karpathy): https://github.com/karpathy/rendergit
- autoresearch (Karpathy): https://github.com/karpathy/autoresearch
- pydantic-ai: https://github.com/pydantic/pydantic-ai
- claude-deep-research-skill: https://github.com/199-biotechnologies/claude-deep-research-skill

**MCP & Integrations**
- MCP Playwright: https://github.com/executeautomation/mcp-playwright
- stealth-browser-mcp: https://github.com/vibheksoni/stealth-browser-mcp
- fastmcp: https://github.com/jlowin/fastmcp
- markdownify-mcp: https://github.com/zcaceres/markdownify-mcp
- MCPHub: https://github.com/samanhappy/mcphub

**Search, Data & LLM Tools**
- CK (semantic code search): https://github.com/BeaconBay/ck
- ExtractThinker: https://github.com/enoch3712/ExtractThinker
- OmniRoute (44+ providers): https://github.com/diegosouzapw/OmniRoute
- dlt (5000+ sources): https://github.com/dlt-hub/dlt
- simonw/llm: https://github.com/simonw/llm
- Portkey gateway (250+ LLMs): https://github.com/Portkey-AI/gateway
- lmnr (trace agents): https://github.com/lmnr-ai/lmnr

**Video & More**
- LTX-Desktop: https://github.com/Lightricks/LTX-Desktop
- MetaClaw (evolve agents no GPU): https://github.com/aiming-lab/MetaClaw
- Vane (AI answering engine): https://github.com/ItzCrazyKns/Vane

### Dónde Encontrar Más Skills
- skillsmp.com — 80k+ skills
- aitmpl.com/skills — Templates
- skillhub.club — 31k+ skills, AI-rated
- agentskills.io — Official spec
- Install path personal: `~/.claude/skills/` | Proyecto: `.claude/skills/`

---

## 16. Polymarket — Copy Trading Intelligence

### El Mito del Win Rate
- Trader con 70% win rate **perdió $47K**
- Trader con 30% win rate **ganó $135K**
- Mismo mes, mismos mercados. La diferencia: ratio riesgo-beneficio.

### Por qué Win Rate Miente
- Comprar YES a $0.80 = arriesgar $0.80 para ganar $0.20 (ratio 3.3:1 en contra)
- 1 pérdida borra 4 victorias
- Ghost positions: posiciones perdedoras sin cerrar no cuentan contra win rate
- Ejemplo real: trader compró YES on Liverpool a $0.66, perdió $1.58M en un solo trade

### Checklist de Copy Trading (Antes de Copiar)
1. Mínimo 50+ trades resueltos
2. Ningún trade = 70%+ del PnL total
3. Position sizing consistente (no $500 → $15K → $200)
4. Entrada promedio $0.30-$0.70
5. 6+ meses de historial profitable
6. Edge específico por categoría, no aleatorio
7. Win rate AL FINAL de la evaluación (no al principio)

### Métricas que Importan
- **Realized Absolute PnL**: dólares reales en posiciones cerradas (no se puede gamear)
- **Market PnL por categoría**: politics vs sports vs crypto — edge es category-specific
- **Max Drawdown**: invisible en win rate, muestra destrucción de capital potencial
- **Position Size vs Frequency**: $10K en 1 trade ≠ $10K en 200 trades

### Datos Duros
- Solo 16.8% de wallets Polymarket tienen ganancia neta
- Wallet 0xee61... (52% win rate) → $1.34M en 7-day PnL
- Wallet 0xd218... (65% win rate) → $900K en mismo periodo (33% menos con más wins)
- Beachboy4: $6.12M single-day gain, pero $687K en pérdidas acumuladas antes

### Herramienta Recomendada
- **Kreo**: https://kreo.app — análisis masivo de wallets Polymarket

### Relevancia para DOF
- El análisis de win rate vs PnL es un caso perfecto para nuestras métricas formales
- Podríamos crear un agente DOF que aplique governance determinística a decisiones de copy trading
- La filosofía de "PnL is the only truth" se alinea con DOF: no confiar en métricas vanity, verificar matemáticamente

---

## 17. CLAUDE.md Template para Telegram Channels

Template recomendado para sesiones de Claude Code via Telegram:

```markdown
# Channel behavior

when receiving instructions via channels:

1. confirm the task before starting
2. break complex requests into phases, report after each
3. if clarification needed, ask ONE specific question, don't guess
4. on completion: what changed, what was created, one-line summary
5. if an error persists after 3 attempts, stop and report with context

# Boundaries

- can edit: content, drafts, copy, templates
- can read: everything
- never touch: credentials, published content, payment configs
- never do: delete files, overwrite without confirmation

# Response Format

keep it short, you're talking to someone on their phone
- status: one line
- done: bullet list of changes
- errors: what failed + what you tried + what you need
```

### Relevancia para DOF
- Template ideal para nuestro Telegram bot (@Ciberpaisa_bot)
- Los boundaries se alinean con DOF governance (HARD_RULES = never touch/never do)
- Response format optimizado para mobile — nuestros agentes deberían adoptar esto

---

## Roadmap de Integración (Actualizado)

### Phase 1 (Completado)
- [x] OpenClaw Gateway funcionando
- [x] 14 agentes configurados
- [x] ClawRouter instalado y funcionando (blockrun/free)
- [x] Telegram bot respondiendo consistentemente
- [x] Mission Control R&D Council panel

### Phase 2 (En Progreso)
- [ ] SocratiCode para indexación semántica del codebase
- [ ] novyx-mcp para memoria persistente compartida
- [ ] Ouro Loop BOUND integration con governance
- [ ] CopilotKit para copilot nativo en Mission Control
- [ ] Hyperspace node en testnet para PoI verification

### Phase 2.5 (Memoria — PRIORIDAD MÁXIMA)
- [ ] Supermemory ASMR — reemplazar ChromaDB vector search por agentic retrieval
- [ ] Ori Mnemos RMH — knowledge graph local con recursive navigation
- [ ] LongMemEval benchmark — medir memoria actual de nuestros agentes
- [ ] Implementar Observer Agents (3 paralelos) para ingesta de knowledge
- [ ] Implementar Search Agents (3 especializados) para retrieval activo

### Phase 3 (Futuro)
- [ ] DeerFlow context compression + progressive skill loading
- [ ] Hyperspace P2P gossip para multi-agente
- [ ] Autoskill selection Darwiniana para Skills Engine v3
- [ ] NVIDIA Deep Agents patterns para enterprise search
- [ ] Polymarket analysis agent con governance determinística
- [ ] git-surgeon para gestión avanzada de historial
- [ ] sinc-llm para optimización de prompts
- [ ] Full A2A protocol entre agentes DOF y agentes externos
- [ ] Decision Forest (12-variant parallel reasoning) para R&D Council
- [ ] Recursive Memory Harness full integration

---

## 18. Supermemory ASMR — ~99% SOTA Agent Memory System
- **URL**: https://github.com/supermemoryai
- **Benchmark**: LongMemEval (https://github.com/xiaowu0162/LongMemEval) — 115K+ tokens, multi-session, temporal reasoning
- **Resultado**: 98.60% (8-Variant Ensemble) / 97.20% (12-Variant Decision Forest)
- **Estado**: Experimental — open source completo en abril 2026

### Técnica: ASMR (Agentic Search and Memory Retrieval)
- NO requiere Vector Database NI embeddings
- Completamente in-memory — embeddable en robots y edge devices
- Reemplaza vector math con razonamiento agéntico activo

### Pipeline de 4 Etapas

**1. Data Ingestion — 3 Observer Agents Paralelos (Gemini 2.0 Flash)**
| Agent | Especialización |
|-------|----------------|
| Fact Hunter | Named Entity Recognition, explicit statements, relationship mapping |
| Context Weaver | Pattern recognition, cross-session correlation, semantic clustering |
| Timeline Tracker | Temporal sequence extraction, event chronology, knowledge update detection |

- Round-robin session distribution (Agent 1: sessions 1,4,7; Agent 2: 2,5,8; Agent 3: 3,6,9)
- Extraction en 6 vectores: Personal Info, Preferences, Events, Temporal Data, Updates, Assistant Info
- Storage structured nativo, mapeado a source sessions

**2. Knowledge Store**
- Structured Agent Findings Store (NO vector DB)
- Session-to-finding mappings
- Pure structured storage, zero embeddings

**3. Active Search Orchestration — 3 Search Agents Paralelos**
| Agent | Especialización |
|-------|----------------|
| Direct Seeker | Exact match retrieval, literal fact extraction, recent-first prioritization |
| Inference Engine | Related context discovery, implication analysis, supporting evidence retrieval |
| Temporal Reasoner | Timeline reconstruction, duration calculation, state change tracking |

- Stateful context management
- Intelligent retrieval basado en cognitive understanding (no keyword/math similarity)

**4. Decision Forest & Consensus**
- **Run 1 (98.60%)**: 8 prompt variants especializados en paralelo (Precise Counter, Time Specialist, Context Deep Dive, etc.) — si CUALQUIER path llega al ground truth, es correcto
- **Run 2 (97.20%)**: 12 agents GPT-4o-mini → Consensus Aggregator (temperature=0) con majority voting, domain trust, conflict resolution → single authoritative answer

### Resultados por Categoría
| Categoría | ASMR 8-Var | ASMR 12-Var | Supermemory Initial | Mastra | Zep |
|-----------|-----------|-------------|---------------------|--------|-----|
| Knowledge Update | 100% | 100% | 89.74% | 96.20% | 83.30% |
| Single-session Assistant | 100% | 100% | 98.21% | 94.60% | 80.40% |
| Single-session User | 100% | 98.57% | 98.57% | 95.70% | 92.90% |
| Temporal Reasoning | 98.50% | 98.50% | 81.95% | 95.50% | 62.40% |
| Multi-session | 96.99% | 96.99% | 76.69% | 87.20% | 57.90% |
| **OVERALL** | **98.60%** | **97.20%** | **85.20%** | **94.87%** | **71.20%** |

### 3 Learnings Clave
1. **Agentic Retrieval > Vector Search**: El unlock más grande. Agentes buscando activamente eliminan la "semantic similarity trap" que hace fallar RAG en temporal changes
2. **Parallelism is Critical**: 3 reading + 3 searching agents mejoran speed y granularidad
3. **Specialization > Generalization**: Agents especializados (Counter, Detail Extractor) superan cualquier single master prompt

### Relevancia para DOF — ALTA PRIORIDAD
- **Reemplazar ChromaDB**: Nuestro `core/memory_manager.py` usa ChromaDB + HuggingFace embeddings. ASMR demuestra que agentic retrieval supera vector search — podríamos migrar
- **3 Observer + 3 Search agents**: Mapeo directo a nuestros 14 agentes existentes. El Research Crew podría actuar como Observer; QA + Analysis como Search
- **Decision Forest para R&D Council**: El 12-variant ensemble con Consensus Aggregator es exactamente lo que necesitamos para las sesiones del R&D Council — 5 agents con voting + aggregation
- **Zero vector DB**: Elimina dependencia de ChromaDB — más soberanía, less infrastructure
- **Temporal Reasoning (98.5%)**: Crítico para nuestro tracking de 238+ autonomous cycles
- **Open source abril 2026**: Estar listos para integrar inmediatamente

---

## 19. Ori Mnemos — Recursive Memory Harness (RMH)
- **URL**: https://github.com/aayoawoyemi/Ori-Mnemos | https://orimnemos.com
- **Paper**: https://arxiv.org/abs/2512.24601 (MIT CSAIL — Recursive Language Models)
- **Qué es**: Primera implementación de Recursive Memory Harness — persistent memory como environment, no como database. Zero infraestructura cloud. Solo markdown files + wiki-links + git.
- **Benchmark**: HotpotQA multi-hop — iguala o supera Redis + Qdrant cloud con CERO databases

### Filosofía: "Memory is Sovereignty"
- Tu memoria de agente almacenada en TU máquina, no en servers de terceros
- Un folder de markdown files conectados por wiki-links, versionados con git, legibles por humanos
- No database. No cloud. No vendor entre tú y tu memoria
- MCP + CLI interface — cualquier modelo se conecta

### Fundamento: RLM (Recursive Language Models — MIT CSAIL, Dic 2025)
- En vez de meter todo en un context window lineal, tratas los datos como un **environment** que el modelo navega
- 8B parameter model con RLM supera su base por 28.3% y se acerca a GPT-5 en long-context
- **Analogía de la biblioteca**: RAG = un bibliotecario que trae libros por título. RLM = TÚ caminas a la biblioteca, lees el catálogo, hojeas un libro, tomas notas, vuelves al catálogo con mejor pregunta, repites

### 3 Constraints de RMH
1. **Retrieval must follow the graph**: Cuando un note se recupera, activación se propaga por edges a notes conectados. NO puede retornar resultados aislados — fuerza clusters de knowledge relacionado (spreading activation, como neuronas)
2. **Unresolved queries must recurse**: Si un retrieval pass no resuelve la query, genera sub-queries targeting lo que falta. Cada sub-query entra al graph por nuevos entry points. Acumula resultados. Para cuando no encuentra info nueva
3. **Every retrieval must reshape the graph**: Notes accedidos dan vitality boost a vecinos (2 hops, decay con distancia). Notes nunca recuperados decaen en power-law curve (Ebbinghaus forgetting curve). El graph NO puede ser estático — se fortalece con uso, se poda por negligencia

### Knowledge Graph como Prerequisito
- Notas = nodos. Cada pieza de info tiene relatividad con otras
- Similar a neuronas: activar una activa otras a distintos niveles
- Wiki-links son los edges entre nodos

### Relevancia para DOF — REVOLUCIONARIA
- **Soberanía total**: Markdown + git = auditable, versionado, sin dependencias externas. Alineado 100% con filosofía DOF (JSONL, determinístico, verificable)
- **Recursive navigation**: Nuestros agentes podrían navegar el knowledge graph en vez de hacer vector search — como caminar por la biblioteca vs pedir libros por título
- **Spreading activation**: Los 14 agentes activando diferentes zonas del graph crea un sistema de memoria compartida orgánico
- **Ebbinghaus decay**: Knowledge no usado se poda automáticamente — limpieza de contexto sin intervención humana
- **Multi-hop reasoning**: HotpotQA requiere combinar 2+ documentos — exactamente lo que necesitamos para cross-agent knowledge
- **Git versioning**: Cada cambio al graph queda en historial — auditoría temporal completa (complementa nuestro blockchain)
- **Zero infrastructure**: Sin Redis, sin Qdrant, sin cloud. Solo files en disco local del M4 Max

### Comparativa: ASMR vs RMH vs DOF Actual

| Dimensión | Supermemory ASMR | Ori Mnemos RMH | DOF Actual |
|-----------|-----------------|----------------|------------|
| Storage | Structured in-memory | Markdown + wiki-links | ChromaDB + JSONL |
| Retrieval | 3 parallel search agents | Recursive graph navigation | Vector similarity |
| Infrastructure | No vector DB | Zero (local files + git) | ChromaDB + HuggingFace |
| Benchmark | 98.6% LongMemEval | Matches Redis/Qdrant on HotpotQA | Not benchmarked |
| Multi-agent | Parallel processing native | MCP interface | Single memory_manager |
| Temporal | 98.5% temporal reasoning | Ebbinghaus decay + vitality | No temporal decay |
| Sovereignty | Cloud API (future) | 100% local, 100% owned | Local ChromaDB |
| Graph | No (structured findings) | Knowledge graph with edges | No graph |
| Open Source | April 2026 | Available now | Available |

### Estrategia de Integración para AGI Soberana
1. **Fase inmediata**: Instalar Ori Mnemos via MCP, conectar a agentes DOF existentes
2. **Fase ASMR**: Cuando se libere (abril), implementar Observer + Search agents paralelos
3. **Fusión**: RMH knowledge graph como storage + ASMR agents como retrieval layer = best of both
4. **DOF governance**: Cada retrieval pass y graph reshape pasa por governance determinística
5. **On-chain**: Hashes de graph state attestados en Avalanche/Base

---

## Links Rápidos (Actualizado)

| Tool | URL | Status |
|------|-----|--------|
| ClawRouter | https://github.com/BlockRunAI/ClawRouter | ACTIVO |
| DeerFlow | https://github.com/bytedance/deer-flow | EVALUANDO |
| SocratiCode | https://github.com/giancarloerra/SocratiCode | EVALUANDO |
| git-surgeon | https://github.com/konfou/git-surgeon | EVALUANDO |
| novyx-mcp | https://github.com/novyxlabs/novyx-mcp | EVALUANDO |
| sinc-llm | pip install sinc-llm | EVALUANDO |
| Ouro Loop | https://github.com/VictorVVedtion/ouro-loop | EVALUANDO |
| Hyperspace | https://agents.hyper.space | EVALUANDO |
| Hyperspace AGI | https://github.com/hyperspaceai/agi | EVALUANDO |
| Karpathy Autoresearch | https://github.com/karpathy/autoresearch | DOCUMENTADO |
| CopilotKit | https://github.com/copilotkit/generative-ui | EVALUANDO |
| NVIDIA Deep Agents | developer.nvidia.com/blog/deep-agents | EVALUANDO |
| awesome-chatgpt-prompts | https://github.com/f/awesome-chatgpt-prompts | REFERENCIA |
| Supermemory ASMR | https://github.com/supermemoryai | ESPERANDO (abril 2026) |
| Ori Mnemos RMH | https://github.com/aayoawoyemi/Ori-Mnemos | EVALUANDO — ALTA PRIORIDAD |
| LongMemEval | https://github.com/xiaowu0162/LongMemEval | REFERENCIA |
| Kreo (Polymarket) | https://kreo.app | REFERENCIA |
| Claude Code Agent Farm | https://github.com/Dicklesworthstone/claude_code_agent_farm | EVALUANDO |
| Kit (cased) | https://github.com/cased/kit | EVALUANDO — ALTA PRIORIDAD |
| CryptoSkill | https://cryptoskill.org | EVALUANDO |
| DOF Dashboard | https://dof-agent-web.vercel.app/ | ACTIVO |
| DOF GitHub | https://github.com/Cyberpaisa/deterministic-observability-framework | ACTIVO |

---

## 20. Claude Code Agent Farm — Parallel Agent Orchestration
- **URL**: https://github.com/Dicklesworthstone/claude_code_agent_farm
- **Qué es**: Orquestador de 20-50 agentes Claude Code trabajando en paralelo via tmux para mejora sistemática de codebases
- **Requiere**: Python 3.13+, tmux, Claude Code con alias `cc`

### 3 Workflows
1. **Bug Fixing**: Agentes trabajan chunks aleatorios de errores linter/type-checker en paralelo
2. **Best Practices**: Implementación sistemática de prácticas modernas con progress tracking
3. **Cooperating Agents** (avanzado): Equipo coordinado con identidades únicas, lock-file work claiming, conflict prevention

### Sistema de Coordinación Distribuida
- `active_work_registry.json` — tracking de trabajo activo por agente
- `completed_work_log.json` — previene trabajo duplicado
- Lock files por agente con stale detection (>2 horas)
- Atomic work units — feature completa antes de liberar lock

### Features
- 34 tech stacks pre-configurados (Next.js, Python, Rust, Go, Solana, etc.)
- Auto-recovery con adaptive idle timeouts
- Dashboard real-time en tmux con context warnings + heartbeat
- 24 tool setup scripts para verificación pre-flight
- Broadcast `/clear` a todos los agentes via Ctrl+R

### Relevancia para DOF
- **Modelo de coordinación**: El lock-based system + work registry es directamente aplicable a nuestros 14 agentes OpenClaw
- **Parallel improvement**: Podríamos correr 14 agentes mejorando DOF en paralelo (tests, docs, refactoring)
- **34 stacks**: Incluye configuración para blockchain (Solana/Cosmos) — adaptable para nuestro stack Avalanche+Base
- **Estado**: EVALUANDO — alto potencial para acelerar desarrollo

---

## 21. NVIDIA Nemotron Cascade 2 — Small Model, Big Results
- **Qué es**: Modelo de NVIDIA (~3B params) que supera modelos 20x más grandes en math y coding
- **Medallas de oro**: Pruebas más difíciles de matemáticas y programación
- **Disponible**: Gratis via Ollama — `ollama run nemotron-cascade-2` (verificar nombre exacto)
- **Capacidades**: Programar, investigar, enviar emails — se comporta como worker real
- **Relevancia para DOF**: Si corre bien en M4 Max con solo 3B params, podría ser agente local ultra-rápido para tareas de governance/validation sin API calls
- **Estado**: INVESTIGAR — verificar disponibilidad exacta en Ollama

---

## 22. Manus AI — Full Google Workspace Automation
- **Qué es**: AI que ejecuta en todo Google Workspace: Docs, Sheets, Slides, Drive, Gmail
- **Un prompt → todo hecho**: Sin cambiar tabs, sin copy-paste
- **Diferencia**: No es AI writing, es AI executing
- **Relevancia para DOF**: Patrón de "AI executing" vs "AI writing" — nuestros agentes deberían ejecutar, no solo generar texto. Manus demuestra que workspace automation completa es posible.
- **Estado**: REFERENCIA — patrón a seguir

---

## Flujo Natural de Conocimiento — Cerebro Compartido

El conocimiento en este documento fluye de forma orgánica entre todos los componentes del sistema:

```
┌──────────────────────────────────────────────────────┐
│                 KNOWLEDGE INGESTION                   │
│  User feeds → TOOLS_AND_INTEGRATIONS.md (este doc)   │
│  Repos, papers, tweets, screenshots → documentado    │
└─────────────────────┬────────────────────────────────┘
                      │
┌─────────────────────▼────────────────────────────────┐
│              AGENT SOUL DISTRIBUTION                  │
│  SOUL.md de cada agente ← extrae lo relevante        │
│  synthesis/ ← estrategia hackathon                   │
│  research/  ← papers, benchmarks                     │
│  security/  ← governance, audits                     │
│  builder/   ← tools, frameworks                      │
└─────────────────────┬────────────────────────────────┘
                      │
┌─────────────────────▼────────────────────────────────┐
│             MISSION CONTROL PANELS                    │
│  R&D Council ← memos de investigación               │
│  Agent Comms ← discusiones entre agentes             │
│  Skills      ← skills descubiertos                   │
│  Activity    ← feed de cambios                       │
└─────────────────────┬────────────────────────────────┘
                      │
┌─────────────────────▼────────────────────────────────┐
│              DOF GOVERNANCE LAYER                     │
│  Todo pasa por governance determinística              │
│  Z3 verifica invariantes                             │
│  On-chain attesta decisiones                         │
│  JSONL traza todo para auditoría                     │
└─────────────────────┬────────────────────────────────┘
                      │
┌─────────────────────▼────────────────────────────────┐
│          MEMORY EVOLUTION (PRÓXIMO)                   │
│  Ori Mnemos RMH → knowledge graph local soberano     │
│  Supermemory ASMR → agentic retrieval (abril 2026)   │
│  Spreading activation + Ebbinghaus decay              │
│  El cerebro crece con uso, se poda por negligencia   │
└──────────────────────────────────────────────────────┘
```

### Principios del Flujo
1. **Tú alimentas** → yo documento en formato estructurado
2. **Cada agente extrae** lo relevante para su dominio (SOUL.md)
3. **Mission Control visualiza** el estado del conocimiento
4. **DOF governance** verifica que las decisiones basadas en este knowledge sean correctas
5. **Memory layer** (próximo) hace que el knowledge compound — lo que se usa se fortalece, lo que no decae
6. **El conocimiento crece** de forma orgánica sin ser engorroso — cada pieza tiene su lugar

---

## 23. Kit — Code Intelligence Toolkit (cased)
- **URL**: https://github.com/cased/kit
- **Stars**: 1.3K | **License**: MIT | **Python**: 86.9%
- **Install**: `uv pip install cased-kit` o `uv pip install 'cased-kit[all]'`
- **Qué es**: Toolkit de producción para construir herramientas AI que entienden codebases. Mapping, symbol extraction, code search, LLM-powered workflows.

### Capacidades Clave
| Feature | Descripción |
|---------|-------------|
| `repo.get_file_tree()` | Estructura jerárquica de archivos |
| `repo.extract_symbols()` | Funciones, clases, constructs — AST-based |
| `repo.search_text()` | Regex search (usa ripgrep si disponible, 10x más rápido) |
| `repo.find_symbol_usages()` | Tracking de símbolos por todo el codebase |
| `repo.chunk_file_by_symbols()` | Chunking inteligente para LLM context windows |
| `repo.get_dependency_analyzer()` | Mapea import relationships |
| `ChromaPackageSearch` | Busca source code de packages populares |

### Interfaces
- **CLI**: `kit symbols /path --format table`, `kit search /path "pattern"`, `kit review PR_URL`
- **Python API**: `from kit import Repository, MultiRepo`
- **MCP Server**: kit-dev para asistentes AI
- **Claude Code Plugin**: `/plugin marketplace add cased/claude-code-plugins`

### PR Review Engine
- Calidad comparable a servicios pagados, costo solo de tokens
- PR Summarization: 5-10x más barato que full reviews (~$0.005-$0.02)
- Commit message generation desde staged changes

### Multi-Repo Support
```python
repos = MultiRepo(["~/code/frontend", "~/code/backend", "~/code/shared"])
repos.search("handleAuth")
```

### Relevancia para DOF — MUY ALTA
- **Symbol extraction**: Mapear nuestros 25+ core modules, 986 tests, exports
- **Dependency analysis**: Visualizar dependencias entre `core/governance.py`, `core/observability.py`, etc.
- **LLM chunking**: Preparar nuestro codebase (27K+ LOC) para contexto de agentes
- **PR review**: Automatizar reviews en nuestro repo con governance hints
- **Multi-repo**: Analizar DOF main + hackathon + frontend + mission-control juntos
- **MCP server**: Dar a nuestros 14 agentes capacidad de code intelligence
- **Complementa SocratiCode**: Kit para analysis + SocratiCode para semantic search = full stack
- **Estado**: EVALUANDO — ALTA PRIORIDAD para Phase 2

---

## 24. CryptoSkill — Registro de Skills para Agentes Crypto
- **URL**: https://cryptoskill.org | https://github.com/nicholasgriffintn/cryptoskill
- **Qué es**: El "App Store" para agentes AI en crypto. 477 skills, 221 oficiales.
- **Chains soportados**: Ethereum, Base, BNB Chain, Solana
- **Analogía**: Antes del App Store, developers usaban canales informales. Cada plataforma necesita un registro → el desarrollo se dispara.

### Relevancia para DOF
- **Registro de skills on-chain**: Nuestro Skills Engine v2.0 (18 skills) podría publicar skills en CryptoSkill
- **Discovery**: Otros agentes pueden descubrir y usar skills DOF
- **Multi-chain**: Soporta Base (donde tenemos ERC-8004 Token #31013) y Ethereum
- **Interoperabilidad**: DOF agents pueden consumir skills de otros agentes del ecosistema
- **Estado**: EVALUANDO — potencial para distribución de skills DOF

---

## 25. Google Stitch + Antigravity — AI UI Design → Full App Pipeline (GRATIS)
- **URL**: https://stitch.withgoogle.com
- **Blog**: [Google Blog](https://blog.google/innovation-and-ai/models-and-research/google-labs/stitch-ai-ui-design/)
- **Qué es**: Herramienta GRATUITA de Google Labs. Texto/sketch/screenshot → UI de alta fidelidad + código exportable
- **Update Marzo 19, 2026**: AI-native infinite canvas, design agent, agent manager paralelo

### Features
- **Voice Canvas**: Hablar al canvas, design critiques en real-time
- **Vibe Design**: Describe el vibe → genera UI completa
- **5 screens simultáneas** con auto-generate de next screens
- **Screen Stitching**: Conecta screens, click "Play" para preview interactivo
- **Export**: HTML/CSS → Figma, Google AI Studio, o Antigravity
- **MCP Server**: Para Claude Code y Cursor

### Antigravity — Agentic IDE de Google
- VS Code fork powered by Gemini
- No solo sugiere — planifica, ejecuta terminal, instala packages, escribe tests, itera
- Pipeline: Stitch design → MCP export → Antigravity → Flutter/Dart app (~10-12 min)

### Relevancia para DOF
- **UI para Mission Control**: Diseñar paneles en Stitch → export → implementar
- **MCP integration**: Conectar a nuestros agentes para UI generation
- **Flutter**: Apps móviles del dashboard DOF
- **Estado**: DISPONIBLE — usar inmediatamente

---

## 26. Claude Code Scheduled Tasks — Tareas Recurrentes
- **Qué es**: Claude Code puede programar tareas recurrentes que se ejecutan automáticamente
- **Versión actual**: Ejecución local (Desktop app debe estar abierta) — versión cloud anunciada
- **Nuevo**: Cloud-based scheduling — configura repo, horario, prompt → Claude ejecuta en nube sin máquina local

### Configuración (Desktop)
| Campo | Descripción |
|-------|-------------|
| Name | Identificador único |
| Prompt | Instrucciones para Claude |
| Frequency | Manual, Hourly, Daily, Weekdays, Weekly |
| Repository | Repo contra el que ejecutar |
| Model | Modelo Claude a usar |
| Permission Mode | Ask, Auto-accept, Plan mode |
| Worktree | Git worktree aislado por ejecución |

### Frecuencias
- **Manual**: Solo con click
- **Hourly**: Cada hora (con stagger de hasta 10 min)
- **Daily**: Hora específica (default 9:00 AM)
- **Weekdays**: Lunes a viernes
- **Weekly**: Día y hora específicos

### Uso para DOF — R&D Council Sessions
```
Prompt: "Run R&D Council session: 5 agents debate current research topics.
Read TOOLS_AND_INTEGRATIONS.md for latest intelligence.
Generate memo with problem, proposal, agent stances.
Save to logs/council/YYYY-MM-DD-HH.jsonl"

Frequency: Daily at 9:00 AM and 5:00 PM
Repository: /Users/jquiceva/equipo de agentes
```

### Uso para Monitoreo de Agentes
```
Prompt: "Check OpenClaw gateway health, verify 14 agents responsive,
run DOF governance health check, report anomalies"

Frequency: Hourly
```

### Uso para Auto-Evolución del Cerebro
```
Prompt: "Read TOOLS_AND_INTEGRATIONS.md, check for outdated entries,
search for new relevant repos/tools, propose updates,
run memory decay on unused knowledge"

Frequency: Weekly on Monday 8:00 AM
```

### Relevancia para DOF
- **R&D Council automático**: 2 sesiones/día sin intervención humana
- **Monitoreo continuo**: Health checks cada hora
- **Auto-evolución**: El cerebro se actualiza solo semanalmente
- **Cloud version**: Cuando esté disponible, no necesitamos M4 Max encendido 24/7
- **Estado**: IMPLEMENTAR — alta prioridad

---

## 27. AlphaEvolve + OpenEvolve — Evolutionary Coding Agent (Google DeepMind)
- **URL**: https://deepmind.google/discover/blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/
- **OpenEvolve (open source)**: https://github.com/codelion/openevolve
- **Qué es**: Agente evolutivo que usa Gemini (Flash 2.0 + Pro) para descubrir y optimizar algoritmos. No genera código de cero — evoluciona soluciones existentes mediante mutación + evaluación automática.

### Logros Verificados
| Logro | Impacto |
|-------|---------|
| Mejoró algoritmo de Strassen (multiplicación de matrices) | Primera mejora en 56 años |
| Recuperó 0.7% del compute global de Google | Optimización de kernels TPU/GPU |
| Descubrió nuevas funciones hash | Superaron heurísticas humanas de décadas |
| Mejoró sorting networks | Reducciones verificables de operaciones |

### Arquitectura
```
Population of Programs → Gemini Flash 2.0 (mutación rápida)
                       → Gemini Pro (mutación creativa)
                       → Evaluator (fitness automático)
                       → Selection (tournament) → Repeat
```

### OpenEvolve — Implementación Open Source
- **Autor**: codelion (HuggingFace)
- **Stack**: Python, usa cualquier LLM como backend (no solo Gemini)
- **Diferencia**: OpenEvolve permite usar modelos locales (Ollama, etc.)
- **Relevancia**: Podemos correr evolución de algoritmos en M4 Max con modelos locales

### Relevancia para DOF
- **Auto-evolución de governance rules**: Evolucionar reglas de governance automáticamente
- **Optimización de Z3 proofs**: Evolucionar fórmulas Z3 más eficientes
- **Skill evolution**: Skills que evolucionan basados en fitness (patrón Darwiniano de CryptoSkill)
- **Patrón complementario**: AlphaEvolve (evolución) + DOF Governance (verificación) = evolución segura
- **Estado**: EVALUAR — integrar OpenEvolve con DOF auto-evolution engine

---

## 28. Estrategia de Monetización DOF — Recursos para Crecer

### Vías de Ingreso Legítimas

| Vía | Descripción | Potencial | Timeline |
|-----|-------------|-----------|----------|
| **Hackathons** | Synthesis, ETHGlobal, Chainlink, Base | $500-$50K por premio | Inmediato |
| **Grants/Bounties** | Avalanche, Base, Optimism, Gitcoin | $1K-$100K | 1-3 meses |
| **PyPI Premium** | dof-sdk enterprise tier con soporte | $49-$499/mes | 2 meses |
| **Consulting** | AI governance audits para empresas | $150-$300/hr | 1 mes |
| **CryptoSkill** | Publicar skills DOF (pago por uso) | Variable | 1 mes |
| **Content** | YouTube/blog/newsletter sobre AI governance | $100-$5K/mes | 2-3 meses |
| **Vercel/Render** | Deploy de DOF como SaaS (governance-as-a-service) | $29-$299/mes/user | 3 meses |
| **Agent-as-a-Service** | Alquilar agentes DOF vía A2A protocol | Per-request pricing | 2 meses |

### Hackathons Activos (Marzo 2026)
1. **Synthesis Hackathon** — YA participando (branch: hackathon)
2. **ETHGlobal** — Próximos eventos con tracks de AI agents
3. **Chainlink BUILD** — Programa para proyectos blockchain
4. **Base Builder Grants** — Ya tenemos ERC-8004 en Base (#31013)
5. **Avalanche Grants** — Ya tenemos 48+ attestations en Avalanche

### Grants Relevantes
- **Gitcoin Grants** — Open source AI governance
- **Optimism RetroPGF** — Retroactive public goods funding
- **Avalanche Ecosystem Fund** — Ya estamos en el ecosistema
- **Base Ecosystem Fund** — Token registrado, podemos aplicar
- **AI Safety grants** — DOF = AI safety verificable con Z3

### Acción Inmediata
1. Completar Synthesis Hackathon con calidad máxima (en progreso)
2. Aplicar a Avalanche Grant con métricas existentes (48 attestations, 986 tests)
3. Aplicar a Base Builder Grant (ERC-8004 #31013 ya registrado)
4. Publicar 3 skills en CryptoSkill (governance_audit, z3_verify, agent_health)
5. Crear landing page con pricing para DOF-as-a-Service

- **Estado**: EJECUTAR — múltiples vías en paralelo

---

## 29. Blitz Mac — iOS Development IDE con MCP para Agentes AI
- **URL**: https://github.com/blitzdotdev/blitz-mac
- **Qué es**: IDE nativa macOS que da a los agentes AI control total sobre el ciclo de vida iOS: simuladores, bases de datos, builds, tests y envío a App Store Connect. Incluye servidores MCP integrados.
- **Requisitos**: macOS 14+, Xcode 16+, Node.js 18+, Apple Silicon
- **Licencia**: Open source
- **Seguridad**: Zero telemetry, MCP bound a 127.0.0.1, sin acceso a datos personales

### Capacidades MCP
| Capability | Descripción |
|------------|-------------|
| Simulator Management | Crear, botar y controlar iOS simulators y devices físicos |
| Database Config | Configurar y gestionar bases de datos de apps iOS |
| Build/Test Pipeline | Compilar, testear y deployar — full lifecycle |
| App Store Connect | Envío autónomo de apps para review vía Apple API |
| Asset Management | Screenshots, store listings, app details |

### Integración con asc-cli
- **URL**: https://github.com/rudrankriyam/app-store-connect-cli-skills
- **23 skills** para automatización de App Store Connect
- Domains: Build & Distribution, Metadata, Signing, Release Management, Monetization, QA
- Blitz MCP cubre ~80% de casos; asc-cli cubre el resto
- Workflow JSON-based para orquestación multi-step

### Relevancia para DOF
- **MCP nativo**: Se integra directamente con nuestros 4 MCP servers existentes (5to server)
- **M4 Max**: App nativa ligera, overhead mínimo junto a los agentes DOF
- **Agente Designer**: El Creativo puede usar Blitz para builds, simulators y App Store
- **Monetización**: Permite publicar apps iOS generadas por agentes → revenue stream
- **Estado**: EVALUAR — alta relevancia si desarrollamos apps iOS

---

## 30. HeroUI v3 — Component Library para React + Vue
- **URL React**: https://heroui.com/docs/react/releases/v3-0-0
- **URL Vue**: https://heroui-vue-docs.vercel.app/docs/vue/getting-started
- **Figma Kit**: https://figma.com/community/file/1546526812159103429/heroui-figma-kit-v3
- **Qué es**: Rewrite completo de NextUI → HeroUI. 75+ componentes React, 37 React Native, versión Vue nueva. Built on React Aria + Tailwind CSS v4.

### Key Features v3
| Feature | Detalle |
|---------|---------|
| Architecture | Compound components con lógica/estilos desacoplados |
| Performance | CSS transitions nativas (GPU-accelerated), sin Framer Motion dependency |
| Accessibility | React Aria Components, keyboard nav + ARIA built-in |
| Theming | Tailwind CSS v4 native CSS variables, OKLCH colors |
| Components | 75+ React, 37 React Native |
| Figma Kit | 1:1 match Figma ↔ código, auto-layout, variants |
| Vue Support | Versión Vue disponible (nuevo en v3) |

### Migración desde NextUI
```bash
# Codemod automático
npx @heroui/codemod@latest
```

### Stack Integration
- **Tailwind CSS v4**: Cada token = CSS variable, sin providers
- **Server Components**: Compatible con React Server Components
- **Bundle Optimization**: Import selectivo por componente
- **Data Attributes**: Custom themes via data-* attributes

### Relevancia para DOF
- **Dashboard + Mission Control**: Reemplazar componentes custom por HeroUI v3
- **Landing page**: Componentes listos para dark/light mode
- **Design System**: Figma Kit v3 = source of truth para El Creativo
- **Vue support**: Si necesitamos UIs en Vue además de React
- **Estado**: IMPLEMENTAR — adoptar como component library principal

---

## 31. Claude Peers MCP — P2P Messaging Entre Instancias Claude Code
- **URL**: https://github.com/louislva/claude-peers-mcp
- **Qué es**: MCP server que permite que múltiples instancias de Claude Code en la misma máquina se descubran y envíen mensajes en tiempo real. Broker daemon con SQLite en `localhost:7899`.
- **Requiere**: Bun runtime + Claude Code v2.1.80+
- **Licencia**: MIT

### Key Features
| Feature | Detalle |
|---------|---------|
| `list_peers` | Descubrir sesiones Claude activas por machine/directory/repo |
| `send_message` | Mensajes instantáneos via channel protocol (polling 1s) |
| `set_summary` | Cada instancia publica su contexto actual visible a peers |
| Auto-summaries | Con `OPENAI_API_KEY`, genera resumen del trabajo actual via GPT-4o mini |
| Broker auto-launch | Proceso broker arranca solo, limpia dead peers automáticamente |

### Relevancia para DOF
- **A2A nativo entre agentes Claude**: Complementa `a2a_server.py` con descubrimiento automático
- **Multi-instancia coordinada**: Dos sesiones Claude Code coordinan trabajo sobre el mismo repo DOF
- **Limitación**: Requiere web login, incompatible con API keys
- **Estado**: EVALUAR — útil para dev local multi-agente

---

## 32. Calyx — Terminal macOS con IPC Nativo Claude Code + Codex
- **URL**: https://github.com/yuuichieguchi/Calyx
- **Qué es**: App terminal nativa macOS 26+ (Swift 6.2 + Metal/Ghostty) con MCP server integrado que permite IPC directo entre Claude Code y Codex CLI en panes separados.
- **Licencia**: No especificada

### Key Features
| Feature | Detalle |
|---------|---------|
| IPC Multi-agente | `register_peer`, `list_peers`, `send_message`, `broadcast` via MCP embebido |
| Auto-config | Escribe `~/.claude.json` y `~/.codex/config.toml` al activar IPC |
| GPU-accelerated | Rendering via Metal + Ghostty v1.3.1 |
| Git sidebar | Working changes, commit graphs, inline diff comments |
| Browser scripting | 25 comandos CLI: `snapshot`, `click`, `fill`, `eval` |

### Relevancia para DOF
- **Patrón IPC embebido en terminal**: Elimina daemon externo — novedoso
- **Limitación**: Requiere macOS 26+ (beta)
- **Estado**: DOCUMENTAR — patrón interesante, no accionable aún

---

## 33. Swarms — Enterprise Multi-Agent Orchestration Framework
- **URL**: https://github.com/kyegomez/swarms
- **Qué es**: Framework Python production-ready para orquestar múltiples agentes AI con 7 patrones de orchestration. Compatible con 50+ LLM providers.
- **Instalación**: `pip install swarms`
- **Licencia**: MIT

### Orchestration Patterns
| Pattern | Descripción |
|---------|-------------|
| SequentialWorkflow | Cadena lineal: output de cada agente alimenta al siguiente |
| ConcurrentWorkflow | Ejecución simultánea de múltiples agentes |
| AgentRearrange | Mapeo dinámico via string pattern (`A -> B, A -> C`) |
| GraphWorkflow | DAG dirigido para dependencias complejas |
| MixtureOfAgents | Expertos paralelos con síntesis final |
| HierarchicalSwarm | Director + workers |
| SwarmRouter | Selección dinámica del tipo de swarm |

### Comparativa con DOF
| Dimensión | Swarms | DOF |
|-----------|--------|-----|
| Governance | Ninguna (LLM decide) | CONSTITUTION + HARD/SOFT_RULES determinístico |
| Observabilidad | LangSmith opcional | JSONL propio + 5 métricas formales |
| Determinismo | No | Sí (seeds, provider ordering, PRNGs) |
| Verificación formal | No | Z3 + on-chain attestations |

### Relevancia para DOF
- **AgentRearrange**: Relaciones dinámicas entre agentes más flexible que crew_factory fijo
- **MixtureOfAgents**: Aplicable al supervisor — 3+ expertos paralelos con síntesis
- **Riesgo**: Adoptar completo = perder governance determinístico. Inaceptable.
- **Estado**: EVALUAR — extraer patrones AgentRearrange + MixtureOfAgents como inspiración

---

## 34. Browser-Use — AI Browser Automation
- **URL**: https://github.com/browser-use/browser-use
- **Stars**: 82,000+ | **Licencia**: MIT
- **Qué es**: Librería Python que conecta agentes LLM con Chromium. El agente "ve" el DOM + screenshots e interactúa via lenguaje natural.
- **Instalación**: `pip install browser-use && playwright install`

### Key Features
| Feature | Detalle |
|---------|---------|
| Vision-based | DOM + screenshots para decisiones |
| Multi-LLM | Claude, Gemini, GPT-4o, Ollama (local) |
| CLI interface | Sesiones persistentes de browser |
| Docker deploy | Imagen oficial para producción aislada |
| Cloud API | Proxies, memoria, CAPTCHA handling |

### Relevancia para DOF
- **Web Research dinámico**: Navegar SPAs que no tienen API REST
- **On-chain monitoring**: Snowtrace, BaseScan, DeFiLlama sin API
- **Governance concern**: Requiere wrapper de governance DOF antes de cualquier acción
- **Prompt injection risk**: Páginas web pueden inyectar instrucciones — usar con PipeLock
- **Estado**: IMPLEMENTAR — como skill `browser_research` con governance wrapper read-only

---

## 35. PipeLock — Agent Firewall para Comunicación Agente-a-Agente
- **URL**: https://github.com/luckyPipewrench/pipelock
- **Qué es**: Firewall de un solo binario (zero dependencies) que se interpone entre el agente AI e internet. 11 capas de scanner. Capability separation: agente tiene secrets pero red restringida; firewall tiene red pero no secrets.

### Scanner Pipeline (11 capas)
| Capa | Función |
|------|---------|
| DLP scanning | 46 patrones: API keys, tokens, credenciales |
| Prompt injection | Normalización evasion-resistant (zero-width chars, homoglyphs, base64) |
| BIP-39 detection | Seed phrases crypto con dictionary + checksum |
| Response filtering | Filtra contenido ANTES de entregar al agente |
| MCP protection | Scanning bidireccional de MCP servers |
| Tool-call chain | 10 patrones que identifican secuencias de ataque |
| Rug-pull detection | Cambios en tool descriptions durante sesión |
| Kill-switch | 4 métodos: config, signal, file, API |
| Audit logging | Webhook + syslog, MITRE ATT&CK mapping |
| Prometheus + Grafana | Métricas operacionales |
| Blockchain protection | Anti-poisoning de wallet addresses |

### Modos de Operación
| Modo | Uso |
|------|-----|
| **Strict** | Allowlist-only — agentes con secrets críticos |
| **Balanced** | Detection-focused — entornos semi-controlados |
| **Audit** | Sin bloqueos, solo visibilidad |
| **hostile-model** | Modelos locales sin censura |

### Relevancia para DOF
- **Complemento crítico a CONSTITUTION**: Constitution = governance semántico. PipeLock = governance de red. Son ortogonales.
- **Protección API keys**: DOF usa `.env` con 5+ provider keys. PipeLock bloquea exfiltración.
- **MCP security**: Proxy de los 4 MCP servers con scanning bidireccional
- **Git pre-commit**: Complementa la regla "NEVER use git add -A"
- **Estado**: IMPLEMENTAR — modo Balanced para MCP servers, Strict para blockchain agents

---

## 36. OpenClaw ACPX — Agent Client Protocol eXtended CLI
- **URL**: https://github.com/openclaw/acpx
- **Stars**: 1,400+ | **Licencia**: MIT | Alpha
- **Qué es**: CLI headless para Agent Client Protocol (ACP). Comunicación estructurada entre tooling de orquestación y coding agents (Claude Code, Codex, Gemini, Copilot, Cursor). Sesiones persistentes por repo.

### Key Features
| Feature | Detalle |
|---------|---------|
| Sesiones persistentes | Sobreviven invocaciones separadas, scoped a repo |
| Sesiones paralelas | Workstreams concurrentes en el mismo codebase |
| Prompt queuing | Requests en cola si hay uno en vuelo |
| Auto-reconnection | Reload transparente al crash del agente |
| Output estructurado | Text, JSON, quiet mode — no ANSI parsing |

### Relevancia para DOF
- Complemento a `crew_runner.py` para spawning de sub-agentes
- JSON output pipeable a JSONL trace system
- **Estado**: EVALUAR — tracking para v1.0

---

## 37. AgentMeet — Chat Rooms para Agentes AI
- **URL**: https://www.agentmeet.net/
- **Qué es**: "Google Meet para agentes AI." Cualquier agente que haga HTTP POST puede unirse a un room y comunicarse en tiempo real. Zero SDK, zero API key, zero signup.

### API
```
GET  /api/v1/{room}/agent-join?format=json  → agent_id + transcript
POST /api/v1/{room}/message                 → {agent_id, agent_name, content}
GET  /api/v1/{room}/wait?after={id}         → long-poll 30s
POST /api/v1/{room}/leave                   → {agent_id}
```

### Relevancia para DOF
- **Debate bus para escalations**: Supervisor ESCALATE → route a AgentMeet room para consensus
- **Red-teaming testbed**: Zero-friction para probar CONSTITUTION contra ataques
- **Estado**: EVALUAR — prototipar escalation path via AgentMeet

---

## 38. AIBroker — Multi-Channel Daemon (WhatsApp + Telegram + Voice)
- **URL**: https://github.com/mnott/AIBroker
- **Qué es**: Daemon que expone Claude Code sobre WhatsApp, Telegram y PAILot (iOS) con TTS (Kokoro) + STT (Whisper) + image generation (Pollinations.ai).

### Key Features
| Feature | Detalle |
|---------|---------|
| Multi-channel | WhatsApp, Telegram, PAILot iOS |
| Voice I/O | Whisper STT + Kokoro TTS |
| Remote sessions | Ver/switch/launch Claude Code desde móvil |
| Terminal screenshots | Enviados directo al chat |
| AIBP protocol | IRC-inspired routing interno |

### Relevancia para DOF
- **Multi-canal**: Reemplazar Telegram-only con daemon multi-canal
- **Voice**: Operador puede dar instrucciones por voz desde teléfono
- **M4 Max**: Whisper + Kokoro self-hostable localmente
- **Estado**: EVALUAR — bajo star count, arquitectura sólida

---

## 39. OneTerm — Bastion Host / Jump Server Enterprise
- **URL**: https://github.com/veops/oneterm
- **Stars**: 1,300+ | **Licencia**: AGPL-3.0
- **Qué es**: Bastion host open-source con modelo 4A: Authentication, Authorization, Account, Audit. Gateway centralizado para SSH/RDP/VNC con session recording.

### Relevancia para DOF
- Hardening de infraestructura M4 Max
- Audit trail formal para acceso SSH complementando JSONL traces
- **Estado**: DOCUMENTAR — para sprint futuro de hardening

---

## 40. Perle Labs / PRL Token — Sovereign Intelligence Layer (Solana)
- **URL**: https://www.perle.ai/ | https://linktr.ee/perle_labs
- **Chain**: Solana | **Funding**: $17.5M (Framework Ventures, CoinFund)
- **Team**: Veterans de Scale AI ($29B), Meta, MIT, UC Berkeley
- **Token**: 10B PRL total, 37.5% community allocation, audited by Halborn

### Reputation-Driven Data Flywheel
```
Verified Expert Annotation → Human-Verified Model Input
        ↓                              ↓
Reputation-Weighted Task Allocation ← On-Chain Reputation Scoring
```

### Relevancia para DOF
- **Monetización**: DOF governance traces (ACCEPT/RETRY/ESCALATE) = expert-labeled AI behavior data → submit a Perle → earn PRL
- **Trust signal**: On-chain reputation scores como input para TrustGateway de DOF
- **Cross-chain**: Avalanche (DOF) ↔ Solana (Perle) attestation bridge
- **Estado**: IMPLEMENTAR (data submission) / EVALUAR (reputation import)

---

## 41. Execution.market — Universal Execution Layer (Ultravioleta DAO)
- **URL**: https://execution.market/ | https://github.com/UltravioletaDAO
- **Qué es**: Marketplace bidireccional AI↔Human. Agentes publican bounties para tasks del mundo real. Humanos ejecutan y cobran via x402. Live en Base, soporte para 9 chains.
- **Fee**: 13% en task completion

### Stack Técnico
| Componente | Detalle |
|------------|---------|
| Identity | ERC-8004 (Trustless Agents) |
| Payments | x402 protocol — HTTP 402 + gasless USDC |
| Agent protocol | A2A (Google Agent-to-Agent) |
| MCP tools | 24 tools via MCP |
| Orchestration | CrewAI |
| Blockchain | Avalanche Fuji (dev), Base (prod), 9 chains |

### Repos Ultravioleta DAO
| Repo | Descripción |
|------|-------------|
| execution-market | Core marketplace — A2H/H2A, x402, ERC-8004 |
| karmakadabra | Trustless AI economy — ERC-8004 + x402 + CrewAI en Avalanche |
| uvd-x402-sdk-python | SDK x402 multi-chain (EVM/Solana/NEAR/Stellar) |
| x402scan | Explorador del ecosistema x402 |

### Relevancia para DOF
- **Arquitectura casi idéntica**: CrewAI + Python + Avalanche + ERC-8004
- **x402 SDK**: Drop-in para micropagos en `a2a_server.py`
- **24 MCP tools**: Extienden nuestros 4 MCP servers con ejecución real-world
- **Estado**: IMPLEMENTAR — alta compatibilidad con DOF existente

---

## 42. Kioxia GP Series + CM9 — Super High IOPS SSDs para AI
- **Fuente**: Anuncio NVIDIA GTC 2026 (Marzo 16, 2026)
- **Qué es**: SSDs diseñados para "agentic AI storage" — 3-5µs latencia (8-30x más rápido que SSDs convencionales), 512-byte access granularity.

### Specs
| Producto | Flash | Latencia | Capacidad | Uso |
|----------|-------|----------|-----------|-----|
| GP Series | XL-FLASH (SLC) | 3-5µs | TBD | GPU HBM extension, AI inference |
| CM9 Series | TLC PCIe 5.0 | Standard | 25.6 TB | KV-cache storage, trillion-param models |

### Relevancia para DOF en M4 Max
| Subsistema DOF | Beneficio |
|----------------|-----------|
| `logs/traces/` RunTrace JSONL | Write latency → effectively free |
| `logs/checkpoints/` | 10M+ IOPS = JSONL append perfecto |
| ChromaDB + embeddings | 25.6TB = knowledge graph completo sin eviction |
| Model weights (local) | XL-FLASH como HBM extension = modelos más grandes sin quantization loss |
| Blockchain data | Full Avalanche node + DOF audit trails en un solo drive |
| Roadmap 2027 | 100M IOPS — storage deja de ser bottleneck para cualquier operación DOF |

- **Estado**: REFERENCIA — hardware datacenter, define dirección de storage para AGI local

---

## 43. HeroUI Pro v2 — Templates Premium para Dashboards
- **URL**: https://v2.heroui.pro/
- **Qué es**: Templates premium basados en HeroUI v3 para dashboards, admin panels, landing pages. Complementa el HeroUI v3 open source (#30).
- **Estado**: REFERENCIA — El Creativo puede inspirarse para Mission Control

---

## 44. Claude Agent Teams — Orchestration Nativa de Claude
- **URL**: https://code.claude.com/docs/en/agent-teams
- **Qué es**: Documentación oficial de Claude para crear equipos de agentes coordinados nativamente.
- **Estado**: EVALUAR — aplicar patrones para coordinar los 14+ agentes DOF

---

## 45. Prompts de Jubilación / Planificación Financiera
- **Fuente**: @Raul_IA_Prod (Twitter)
- **Qué es**: 7 prompts especializados para planificación financiera con Claude (jubilación, test de estrés, pensión, fiscalidad, cobertura sanitaria, distribución de cartera, evaluación de preparación).
- **Relevancia**: Patrones de prompt engineering para el finance-skills del equipo
- **Estado**: REFERENCIA — alimenta skills de finanzas

---

*Documento generado automáticamente — Última actualización: Marzo 22, 2026 — 45 herramientas documentadas + 100+ repos referenciados + estrategia de monetización*
