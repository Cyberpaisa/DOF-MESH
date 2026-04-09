# Reporte de Arquitectura Comparativo — Agent Harness Analysis
> Generado: 2026-04-04 | DOF-MESH v0.5.1 | Solo lectura

## Repos analizados

| Repo | Path | Stack | LOC | Status |
|---|---|---|---|---|
| `claw-code-agent` (HarnessLab) | `/tmp/claw-harness` | Python (zero deps) | 12,929 | Alpha 0.1.0 |
| `claw-code-parity` (ultraworkers) | `/tmp/claw-ultraworkers` | Rust (tokio) | 61,637 | Active (9-lane merge) |

---

## Estructura de directorios

### claw-harness (Python)

```
src/
├── main.py                     # CLI entry point & arg parsing
├── agent_runtime.py            # LocalCodingAgent — core loop
├── agent_tools.py              # Tool definitions & execution
├── agent_prompting.py          # System prompt assembly
├── agent_context.py            # Context building & CLAUDE.md discovery
├── agent_context_usage.py      # Context usage estimation
├── agent_session.py            # Session state management
├── agent_slash_commands.py     # Local slash command processing
├── agent_manager.py            # Nested agent lineage tracking
├── agent_types.py              # Shared dataclasses & types
├── openai_compat.py            # OpenAI-compatible API client
├── plugin_runtime.py           # Plugin manifest & hooks
├── permissions.py              # Tool permission filtering
├── cost_tracker.py             # Cost & budget tracking
├── mcp_runtime.py              # MCP resource discovery (local only)
├── hook_policy.py              # Hook policy system
├── plan_runtime.py             # Plan management
├── task_runtime.py             # Task lifecycle
├── skills/                     # Placeholder (inventory snapshot, no runtime)
├── plugins/                    # Plugin subsystem
├── hooks/                      # Hook system
├── remote/                     # Remote modes (WIP)
└── tests/                      # 12 test files
```

### claw-ultraworkers (Rust)

```
rust/crates/
├── api/                        # Anthropic API client + SSE streaming
│   └── src/{client,providers/anthropic,providers/openai_compat,sse}.rs
├── commands/                   # Slash command registry
├── compat-harness/             # Upstream compatibility extraction
├── mock-anthropic-service/     # Deterministic mock server
├── plugins/                    # Plugin management + hooks
│   └── src/{lib,hooks}.rs
├── runtime/                    # Core (mayor crate — 40+ módulos)
│   └── src/{conversation,session,permissions,permission_enforcer,
│            mcp,mcp_client,mcp_stdio,mcp_tool_bridge,
│            mcp_lifecycle_hardened,file_ops,bash,bash_validation,
│            policy_engine,compact,task_registry,task_packet,
│            team_cron_registry,recovery_recipes,sandbox,
│            oauth,worker_boot,trust_resolver,stale_branch,
│            config,hooks,plugin_lifecycle}.rs
├── rusty-claude-cli/           # CLI binary + TUI
└── tools/                      # Tool registry & execution
```

---

## Tabla comparativa por componente

| Componente | claw-harness (Python) | claw-ultraworkers (Rust) |
|---|---|---|
| **Agent loop** | `LocalCodingAgent` dataclass frozen. Build prompt → call API → parse tools → execute → recurse | `ConversationRuntime`. Streaming tokio-based. Multi-turn con `ContentBlock` variants |
| **Tool execution** | 7 core tools + plugin aliases/virtual/hooks. `ToolExecutionContext` con permissions | 7 core tools + `mcp_tool_bridge`. `ToolExecutor` trait. Bash validation submodule |
| **Context/memory** | `AgentContextSnapshot`. CLAUDE.md auto-discovery. Auto-snip + auto-compact | `ProjectContext` + `SystemPromptBuilder`. JSONL session rotation (256KB). Compaction automática |
| **Permissions** | 3 flags: `allow_file_write`, `allow_shell_commands`, `allow_destructive_shell_commands`. `ToolPermissionContext` con deny list | `PermissionMode` tiered (ReadOnly → WorkspaceWrite → DangerFullAccess → Prompt → Allow). `PolicyEngine::evaluate()`. Runtime prompting |
| **MCP** | Local resource discovery únicamente. NO stdio/HTTP/WebSocket. Inventory-only | Full transport stack: Stdio, SSE, HTTP, WebSocket, SDK, ManagedProxy. `McpLifecycleValidator`. `McpServerManager` |
| **Skills** | Placeholder. Snapshot JSON de inventory. Sin runtime de ejecución | Placeholder. Referenciado en CLI flags. Sin runtime |
| **Providers** | vLLM, Ollama, LiteLLM Proxy, OpenRouter (OpenAI-compat) | Anthropic native + OpenAI compat |
| **Tests** | 12 unit tests (`python3 -m unittest discover`) | 19+ integration tests + mock parity harness (10 scenarios) |
| **Madurez** | Alpha 0.1.0 — loop funcional, plugins working, MCP parcial | Active, 292 commits, 9-lane merge. MCP completo, bash sandbox |
| **LOC** | 12,929 | 61,637 |
| **Dependencias externas** | Zero (stdlib Python pura) | serde_json, tokio (async) |
| **Async** | Sync | Tokio-based full async |
| **Budget/cost** | `cost_tracker.py` — tokens, cost limits, tool-call caps, session-turn limits | No dedicado (gestionado vía context limits) |
| **Nested agents** | `AgentManager` — lineage tracking, nested delegation | Worker boot protocol (`worker_boot.rs`) |
| **Bash sandbox** | Basic (allow/deny flags) | `sandbox.rs` — Linux `unshare`, validation submodules |
| **Recovery** | Reactive compaction en `prompt_too_long` | `recovery_recipes.rs` — estrategias explícitas |

---

## Análisis de aplicabilidad a DOF-MESH

### 1. Patterns de harness que DOF-MESH NO tiene (y podría necesitar)

| Pattern | Repo origen | Descripción | Prioridad para DOF |
|---|---|---|---|
| **Session persistence + rotation** | claw-ultraworkers | JSONL con rotación 256KB, máx 3 archivos. Resume automático entre sesiones | Alta — equipo-de-agentes reinicia contexto entre runs |
| **Mock harness determinístico** | claw-ultraworkers | `mock-anthropic-service` + 10 scenarios de parity. Permite tests de integración sin API real | Alta — tests DOF usan `python3 -m unittest` pero sin mock de providers |
| **Policy engine explícito** | claw-ultraworkers | `policy_engine.rs` con `PolicyRule`, conditions y actions. Separado de governance | Media — DOF tiene 7 capas de governance pero el policy engine es implícito en `ConstitutionEnforcer` |
| **Recovery recipes** | claw-ultraworkers | `recovery_recipes.rs` — estrategias explícitas por tipo de error | Media — DOF tiene fallback chain de providers pero sin recovery recipes por categoría de fallo |
| **Cost tracker por sesión** | claw-harness | Tokens, cost limits, tool-call caps y session-turn limits en `cost_tracker.py` | Media — útil para el Evolution Daemon y presupuesto del Soberano |
| **Plugin manifest runtime** | claw-harness | Aliases de tools, virtual tools, tool blocking, hooks before/after. Funciona en runtime | Baja — DOF tiene hooks pero en pre-commit, no en runtime de tools |
| **Trust resolver** | claw-ultraworkers | `trust_resolver.rs` — decisiones de confianza explícitas por entidad | Baja — DOF tiene Z3 pero no un trust resolver de runtime para identidades |

### 2. Qué tiene DOF-MESH que estos repos NO tienen

| Capacidad DOF | Descripción | Relevancia |
|---|---|---|
| **Z3 Formal Verification** | 4/4 invariantes PROVEN. `z3_gate.py` como invariante arquitectónico | No existe en ningún harness conocido |
| **On-chain attestations** | `DOFProofRegistry` en 8 chains. Cada decisión de governance tiene hash keccak256 | Único en el ecosistema |
| **7-layer governance** | Constitution → AST → Supervisor → Adversarial → Memory → Z3 → Oracle. Determinístico sin LLM | Ambos repos tienen permissioning básico, no governance multicapa |
| **Adversarial testing** | `adversarial.py` (50KB) — red/blue team contra inyecciones | No presente en ninguno |
| **Enigma integration** | Trust scores + combined_trust_view + dof_trust_scores table | No presente |
| **Multi-chain support** | 8 chains, 3 mainnets, `chain_adapter.py` | No presente |
| **Autonomous daemon** | `autonomous_daemon.py` — auto-governanza con fases y ciclos | No presente |
| **Coliseum of Truth** | 12 modelos en adversarial evaluation, Model Integrity Score | No presente |
| **SOUL.md per-agent** | Personalidad agnóstica que funciona con cualquier LLM | No presente |
| **CrewAI integration** | 11 crews, 8 agentes, Process.sequential orchestration | No presente |

### 3. Archivos más valiosos para estudiar y aplicar

#### De claw-harness (Python):

| Archivo | Por qué es valioso | Aplicación en DOF |
|---|---|---|
| `src/agent_context.py` | Pattern de `AgentContextSnapshot` — captura estado del entorno de forma reproducible | `ProviderManager` podría adoptar snapshot de estado para debugging |
| `src/agent_types.py` | `UsageStats`, `ModelConfig`, `AgentPermissions` — dataclasses limpios para budget tracking | `EvolveEngine` podría rastrear costo por ciclo evolutivo |
| `src/cost_tracker.py` | Budget enforcement por tokens, cost, tool-calls, turns | Útil para el Sovereign Vault y límites del Evolution Daemon |
| `src/plugin_runtime.py` | Plugin manifest con aliases, virtual tools, blocking, hooks. Funcional sin deps | Modelo para DOF Tool Hook Gate PRE en runtime |

#### De claw-ultraworkers (Rust):

| Archivo | Por qué es valioso | Aplicación en DOF |
|---|---|---|
| `runtime/src/recovery_recipes.rs` | Catálogo explícito de recuperación por tipo de error | `autonomous_executor.py` podría tener recovery recipes por categoría de fallo de LLM |
| `runtime/src/session.rs` | JSONL rotation pattern — sesiones persistentes y resumibles | `StorageFactory` ya tiene JSONL, pero el patrón de rotación + resume automático es superior |
| `mock-anthropic-service/src/lib.rs` | Mock determinístico para testing sin API real | Eliminaría dependencia de Groq/DeepSeek en los 4,157 tests |
| `mock_parity_scenarios.json` | 10 scenarios de integración end-to-end estructurados | Modelo para un `parity_scenarios.json` DOF que cubra governance + attestation |
| `runtime/src/policy_engine.rs` | `PolicyRule` separado de la governance — composable | `ConstitutionEnforcer` podría exponer una policy engine separada para herramientas externas |

### 4. Integración directa posible

**Sin riesgos, valor inmediato:**

1. **Pattern de `AgentContextSnapshot`** (de claw-harness `agent_context.py`):
   Portar el dataclass de snapshot de entorno a Python puro. Útil para `claude_commander.py` y el debugging del Citadel.

2. **`mock_parity_scenarios.json`** como template de estructura:
   Crear `equipo-de-agentes/tests/parity_scenarios.json` con los 10 casos DOF equivalentes (governance pass, governance reject, Z3 violation, on-chain attestation, adversarial block, etc.). Corre contra un mock DeepSeek local.

3. **Cost tracker pattern** de `cost_tracker.py`:
   Añadir budget enforcement por ciclo al `EvolveEngine`. `budget_usd=0.0` ya existe, pero token caps y tool-call caps no.

---

## Recomendación final

### ¿Cuál repo es más útil para DOF-MESH?

**`claw-ultraworkers` (Rust)** es más maduro y completo (292 commits, MCP full stack, policy engine, recovery recipes). Pero para DOF-MESH el stack es Python — la brecha de lenguaje hace la integración directa no viable.

**`claw-harness` (Python)** es más pequeño (12,929 LOC, zero deps) y directamente portable. Los patterns de context snapshot, cost tracking y plugin manifest son los más aplicables al stack actual.

**Recomendación: estudiar claw-ultraworkers como referencia arquitectónica, portar patterns específicos de claw-harness al codebase Python de DOF-MESH.**

### 3 patterns específicos a adoptar

| Prioridad | Pattern | Fuente | Acción concreta |
|---|---|---|---|
| 1 | **Mock determinístico de providers** | claw-ultraworkers `mock-anthropic-service` | Crear `tests/mock_provider.py` que simule DeepSeek/Groq responses. Eliminar dependencia de API real en CI |
| 2 | **Session persistence + resume** | claw-ultraworkers `session.rs` | Refactorizar `StorageFactory` para soportar resume automático de sesiones entre runs del daemon |
| 3 | **Cost tracker por ciclo** | claw-harness `cost_tracker.py` | Añadir `TokenBudget` al `EvolveEngine` con caps de tokens, tool-calls y turns por ciclo evolutivo |

### ¿Hay riesgo legal en usar alguna parte?

| Repo | Licencia detectada | Riesgo |
|---|---|---|
| `claw-harness` | No se detectó LICENSE en el shallow clone | **REVISAR** antes de portar código. Si no tiene licencia, el código es "all rights reserved" por defecto |
| `claw-ultraworkers` | No se detectó LICENSE en el shallow clone | **REVISAR** igualmente |

**Recomendación:** Para ambos repos, los patterns arquitectónicos (dataclass shapes, module structure, algorithm ideas) son reutilizables sin restricción legal. El código literal requiere confirmación de licencia. Implementar como reimplementación original inspirada en el análisis, no como copia.

---

## Archivos generados por este análisis

- Este documento: `equipo-de-agentes/docs/02_research/HARNESS_ANALYSIS.md`
- Repos temporales: `/tmp/claw-harness`, `/tmp/claw-ultraworkers` (pueden eliminarse)

*DOF-MESH v0.5.1 · Mathematics, not promises.*
