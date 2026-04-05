# STACK_HERRAMIENTAS.md — DOF-MESH

> Inventario real del stack. Auditado el 05 Apr 2026.
> Solo lo que REALMENTE existe — no lo que debería existir.

---

## Python packages (instalados)

| Paquete | Versión | Estado |
|---|---|---|
| markitdown | 0.0.2 | ⚠️ desactualizado — última es 0.1.x |
| groq | 1.1.2 | ✓ |
| web3 | 7.14.1 | ✓ |
| z3-solver | 4.16.0.0 | ✓ |
| dof_z3_gate | 0.1.0 | ✓ |

**Ausentes notables:** `crewai`, `opentelemetry`, `dof-sdk` (no aparece como paquete pip instalado).

---

## Binarios globales

| Binario | Ruta | Estado |
|---|---|---|
| markitdown | `/opt/homebrew/bin/markitdown` | ✓ |
| bun | `~/.bun/bin/bun` | ✓ |
| node | `~/.nvm/versions/node/v22.16.0/bin/node` | ✓ v22.16.0 |
| npm | `~/.nvm/versions/node/v22.16.0/bin/npm` | ✓ |
| python3 | `/opt/homebrew/bin/python3` | ✓ |
| ollama | `/opt/homebrew/bin/ollama` | ✓ |

---

## Skills Claude instaladas (35 total)

### Activas DOF
- `dof-skill-creator` — **constructor oficial de skills DOF** · triggers: "crea una skill", "nueva skill", "construye una skill"
- `anthropic-ecosystem` — base de conocimiento repos/quickstarts/SDKs Anthropic · triggers: "qué repo de anthropic", "quickstart", "claude api", "sdk"
- `dof-session-report` — reporte HTML de cierre de sesión
- `markitdown-converter` — conversión de documentos a MD · triggers: "convierte", "pasa a markdown", "ingesta"
- `sovereign-funding` — capa financiera nativa DOF Mesh
- `super-sentinel` — Trust Layer ERC-8004
- `erc8004-avalanche` — registro de agentes Avalanche
- `erc8004-celo` — registro de agentes Celo
- `deploy-to-skale` — deploy contratos SKALE
- `conflux-integration` — ecosistema Conflux
- `x402-on-skale` — pagos x402 en SKALE

### Tododeia Community (30 skills — Sesiones 7a + 7b)

#### Batch 1 — Sesión 7a (10 skills)
- `ruflo-cloud` — orquestación multi-agente, topologías hierarchical/mesh/ring/star · triggers: "ruflo", "multi-agente ruflo"
- `apis-mcps-a2a` — guía protocolos API/MCP/A2A · triggers: "mcp vs a2a", "integrar mcp", "configurar a2a"
- `crea-claude-skills` — estructura SKILL.md, frontmatter YAML · triggers: "cómo crear una skill", "estructura skill.md"
- `menos-contexto-claude` — context-mode plugin, 98% reducción BM25+SQLite · triggers: "reducir contexto", "ventana contexto llena"
- `claude-code-loop` — /loop recurrente, /schedule cron · triggers: "loop claude", "tarea recurrente claude"
- `maia-skill` — 5-agente investment analysis, dashboard localhost:3420 · triggers: "análisis inversión", "maia"
- `skill-seekers-obsidian` — pipeline GitHub/YouTube/PDF → Obsidian · triggers: "skill seekers", "knowledge base obsidian"
- `claude-canales` — Telegram+Discord plugin oficial, Bun runtime · triggers: "canal telegram claude", "controlar claude telegram"
- `whatsapp-agentkit` — agentes IA en WhatsApp, FastAPI+Docker · triggers: "agente whatsapp", "whatsapp agentkit"
- `agencia-digital-completa` — antigravity 900+ skills · triggers: "agencia digital agentes", "antigravity skills"

#### Batch 2 — Sesión 7b (20 skills)
- `claude-token-efficient` — 8-rule CLAUDE.md reduce 63% tokens · triggers: "ahorrar tokens", "63% menos tokens"
- `cinco-errores-claude` — 5 errores que vacían la cuenta Claude · triggers: "errores cuenta claude", "5 errores claude"
- `configura-claude-ahorra` — 5 configs que duplican duración del plan · triggers: "plan claude doble", "configurar plan claude"
- `mejora-prompts-claude` — plugin prompt-improver, 31% token savings · triggers: "mejorar prompts", "prompt improver"
- `comando-de-sistema` — guía conversacional 5 fases para system prompts · triggers: "system prompt guiado", "crear system prompt"
- `the-architect-skill` — plano 16 secciones (Hainrixz) · triggers: "the architect", "plano 16 secciones"
- `arquitecto-de-ingresos` — plan monetización: KILLER_MOVE_24H, 14-day sprint · triggers: "arquitecto ingresos", "killer move 24h"
- `metodologia-v1` — metodología 5 fases para scope de v1 · triggers: "metodología v1", "construir por fases ia"
- `claude-piloto-automatico` — YOLO Mode + hooks de protección · triggers: "piloto automático claude", "yolo mode"
- `schedule-agentes-nube` — /schedule en servidores Anthropic · triggers: "schedule nube anthropic", "agentes cloud claude"
- `claude-dispatch` — asignar tareas desde móvil, ejecutar en desktop · triggers: "claude dispatch", "claude desde el móvil"
- `crea-agentes-con-claude` — 6 pasos: Plan Mode → describe → ejecuta · triggers: "crear agente claude code", "agente plan mode"
- `claude-control-remoto` — Computer Use: mouse/teclado/pantalla · triggers: "computer use claude", "control remoto claude"
- `skill-vault` — gestor biblioteca skills, 13 checkpoints seguridad · triggers: "skill vault", "gestionar biblioteca skills"
- `equipo-dev-5-skills` — 5 skills: SuperPower+Debugging+FileSearch+Optimizer+Creator · triggers: "equipo dev skills", "5 skills desarrollo"
- `vercel-skills-finder` — skills.sh + find-skills marketplace · triggers: "buscar skills vercel", "skills.sh"
- `gstack-ia` — GStack Garry Tan (YC CEO) 31 comandos · triggers: "gstack", "autoplan ship qa"
- `claude-cowork` — Claude Desktop workspaces persistentes · triggers: "cowork claude", "workspace persistente claude"
- `obsidian-claude-memoria` — Obsidian como memoria persistente entre sesiones · triggers: "obsidian memoria claude", "claude memoria permanente"
- `trucos-claude-basicos` — ultrathink+Plan Mode+sub-agentes+/init+PROGRESS.md · triggers: "ultrathink claude", "trucos claude"

### Otras instaladas
- `arquitecto-sistema-prompt`, `construye-con-estructura`, `crear-skills`
- `business-growth-skills`, `c-level-advisor`, `engineering-advanced-skills`
- `finance-skills`, `pm-skills`, `product-skills`, `marketing-skills`
- `find-skills`, `github-explorer`, `remember`, `stress-test`
- `humanizalo`, `logo-design`, `tres-herramientas-claude-code`
- `gsap-core`, `gsap-frameworks`, `gsap-performance`, `gsap-plugins`
- `gsap-react`, `gsap-scrolltrigger`, `gsap-timeline`, `gsap-utils`
- `generate`, `review`

### Pendientes instalar
- `boot` — boot de sesión DOF-MESH
- `evolve` — auditoría sistema de evolución
- `update-config` — configurar harness via settings.json
- `loop` — tareas recurrentes por intervalo
- `schedule` — agentes programados con cron
- `frontend-design` — interfaces production-grade
- `telegram:configure` — configurar canal Telegram
- `telegram:access` — gestión de acceso Telegram

---

## Scripts del sistema (25 en scripts/)

### Existen
```
a2a_manage.sh
agentmeet/
benchmarks/
check_env.js
demo_end_to_end.py
deploy/
deploy_multichain.sh
deploy_tempo.sh
evolution_daemon.py
experiments/
full_cycle_proof.py
ghost/
install_rust_gate.sh
mesh_run.sh
mimo_web_trap.json
monitoring/
paste_mimo_response.sh
phase10/
phase11/
prompt_eval_ci.py
q_aion/
run_claude_dof_bot.sh
run_mesh_agent.py
spawn_claude_worker.sh
start_voice.sh
test_voice_winston.py
```

### NO existen (pendientes)
- `release.sh` — **pendiente Sesión 7** (bump version + build + tag + PyPI + GitHub Release)
- `~/bin/dof` — arranque unificado del sistema (daemon + A2A + frontend + Telegram)

---

## MCP configurados

- `settings.json` — sin sección mcpServers activa (vacío o no configurado)
- MCPs disponibles en sesión (via claude.ai): Figma, Gmail, Google Calendar, Three.js, Vercel, Telegram, context7, brave-search, supabase, playwright, evm-mcp, sequential-thinking, tavily

---

## Pendientes de actualización

| Item | Estado actual | Acción necesaria |
|---|---|---|
| markitdown | 0.0.2 | `pip3 install --upgrade markitdown` |
| crewai | no instalado | `pip3 install crewai` |
| dof-sdk | no aparece en pip | verificar instalación local vs PyPI |
| MCP local | settings.json vacío | configurar servidores MCP en settings.json |
| release.sh | no existe | crear en Sesión 7 |
| ~/bin/dof | no existe | crear en Sesión 7 |
