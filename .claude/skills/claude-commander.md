# Skill: Claude Commander — Orquestación Soberana de Agentes Claude

## Activacion
Cuando el usuario pida: spawnar agentes, comandar Claude, lanzar daemons, sesiones paralelas, control autonomo, ordenes desde Telegram, o cualquier tarea que requiera multi-agente LLM directo.

## Que Es
DOF ClaudeCommander es el primer modulo del mundo que permite a un framework de governance deterministica ordenar directamente a Claude Code sin API, sin gateway, sin overhead. Claude Code spawneando Claude Code, gobernado por CONSTITUTION.

## Arquitectura

```
Interfaces (Telegram, CLI, Mission Control, Terminal)
    |
    v
ClaudeCommander (core/claude_commander.py)
  5 modos: SDK | Spawn | Team | Debate | Peers
  Model: claude-opus-4-6 ($100 budget)
  Permission: bypassPermissions (24/7 autonomo)
    |
    v
DOF Governance Layer
  Pre-check -> Execute -> Post-check -> Audit
  CONSTITUTION + Z3 + JSONL + Blockchain
    |
    v
Claude Agent SDK (claude-agent-sdk==0.1.50)
  query() -> Claude Code CLI -> LLM directo
  AgentDefinition -> sub-agentes independientes
  Hooks -> PreToolUse, PostToolUse, Stop
    |
    v
Communication Layer
  Peers MCP (localhost:7899) - AgentMeet (HTTP) - Queue (JSONL) - A2A (port 8000)
```

## Los 5 Modos de Comunicacion

### 1. SDK Mode — Orden directa
```python
from core.claude_commander import ClaudeCommander
commander = ClaudeCommander()
result = await commander.command("Fix the bug in core/governance.py")
# -> CommandResult(status="success", output="...", elapsed_ms=7300)
```
DOF ordena -> Claude Code ejecuta -> resultado en <20s -> JSONL audit.

### 2. Spawn Mode — Sub-agente especializado
```python
result = await commander.spawn_agent(
    name="security-auditor",
    prompt="Audit core/ for vulnerabilities",
    tools=["Read", "Grep", "Glob"]
)
```
Un agente Claude independiente con su propio contexto, tools y rol.

### 3. Team Mode — Equipo paralelo
```python
results = await commander.run_team(
    task="Review DOF v0.5 release",
    agents={
        "reviewer": "Check code quality",
        "security": "Audit for vulnerabilities",
        "tester": "Verify all tests pass",
    },
    parallel=True,  # asyncio.gather
)
```
N agentes Opus 4.6 trabajando en paralelo, cada uno con su rol.

### 4. Debate Mode — Consenso multi-agente via AgentMeet
```python
transcript = await commander.debate(
    room="dof-council",
    topic="Should we migrate from ChromaDB?",
    agents=["researcher", "architect", "security"],
    rounds=3,
)
```
Agentes debaten en AgentMeet por rondas. DOF extrae consenso al final.

### 5. Peers Mode — P2P entre instancias Claude
```python
peers = await commander.list_peers()  # localhost:7899
await commander.message_peer(peer_id, "Coordinate on task X")
```

## Session Persistence — Memoria Infinita

```python
# Primera llamada: crea sesion nueva
result = await commander.persistent_command(
    name="builder",
    prompt="Search for TODOs and implement one"
)
# -> session_id guardado en logs/commander/sessions.json

# Siguiente llamada: resume exactamente donde dejo
result = await commander.persistent_command(
    name="builder",
    prompt="Continue your previous work, what's next?"
)
# -> Claude recuerda TODO lo que hizo antes
```

Stored en: `logs/commander/sessions.json`
```json
{"builder": "91220911-a203-45ec-ab0e-8ef8cef90a5d"}
```

## Autonomous Daemon — El Orquestador Autonomo

### Modulo: `core/autonomous_daemon.py`

4 fases en loop infinito:
1. **PERCEIVE** — scan_state(): pending orders, errors, git changes, health
2. **DECIDE** — plan_next(): deterministic rules, zero LLM
3. **EXECUTE** — spawn agents, run commands, review code
4. **EVALUATE** — score results, log JSONL, update metrics

```bash
# Daemon generalista
python3 core/autonomous_daemon.py

# 3 daemons especializados en paralelo
python3 core/autonomous_daemon.py --multi

# Dry run (sin ejecutar)
python3 core/autonomous_daemon.py --multi --cycles 5 --dry-run
```

### Multi-Daemon: 3 Cerebros Especializados

| Daemon | Intervalo | Budget | Especialidad |
|--------|-----------|--------|-------------|
| **BuilderDaemon** | 180s | $3/cycle | Features, TODOs, pending orders |
| **GuardianDaemon** | 300s | $2/cycle | Security, tests, regressions |
| **ResearcherDaemon** | 600s | $2/cycle | Metrics optimization, analysis |

Cada uno con **session persistence** — recuerda todo entre ciclos.

## Telegram Integration

| Comando | Funcion |
|---------|---------|
| `/claude <orden>` | Orden directa a Claude Code |
| `/team <tarea>` | 3 agentes paralelos (reviewer, security, tester) |
| `/parallel N <tarea>` | N agentes en paralelo (max 10) |
| `/daemon start` | Lanzar daemon autonomo |
| `/daemon status` | Estado del daemon |
| `/multidaemon` | 3 daemons especializados |
| `/sessions` | Ver sesiones recientes |
| `/approve` | Aprobar accion del daemon |
| `/redirect <nueva instruccion>` | Redirigir daemon |

Flujo bidireccional:
```
Telegram -> /claude orden -> queue/*.json -> daemon -> Claude SDK -> resultado -> Telegram
```

## Governance Pipeline

Cada comando pasa por:
1. **Pre-check**: ConstitutionEnforcer.enforce(prompt) -> HARD_RULES
2. **Execute**: Claude Code con bypassPermissions
3. **Post-check**: ConstitutionEnforcer.enforce(output) -> verificacion
4. **Audit**: JSONL con timestamp, session_id, elapsed_ms
5. **On-chain**: Attestation en Avalanche (opcional)

## Diferencia vs Otros Frameworks

| Dimension | CrewAI/LangGraph/Swarms | DOF Commander |
|-----------|------------------------|---------------|
| Acceso LLM | API call ($$$, rate limits) | Directo via SDK (0 overhead) |
| Permisos | Dialogo manual | bypassPermissions 24/7 |
| Governance | Ninguna o LLM-based | CONSTITUTION + Z3 + blockchain |
| Multi-agente | Gateway centralizado | P2P + HTTP + SDK |
| Trazabilidad | Logs opcionales | JSONL obligatorio, on-chain |
| Memoria | Por sesion | Persistente entre ciclos |
| Control remoto | API | Telegram -> queue -> terminal |

## Metricas Verificadas

| Metrica | Valor |
|---------|-------|
| SDK command (Haiku) | 7.3s |
| SDK command (Opus 4.6) | 20.6s |
| Team review (2 agents) | 115s |
| Multi-daemon (3 brains) | 35-128s por ciclo |
| API overhead | 0 |
| Rate limit | Ninguno |
| Dialogos de permiso | 0 |

## Archivos Clave

| Archivo | Funcion |
|---------|---------|
| `core/claude_commander.py` | Modulo principal — 5 modos |
| `core/autonomous_daemon.py` | Daemon autonomo + 3 especializados |
| `interfaces/telegram_bot.py` | Comandos /claude, /team, /parallel, /daemon |
| `scripts/watch_orders.py` | Monitor de cola Telegram->terminal |
| `logs/commander/commands.jsonl` | Audit trail de comandos |
| `logs/commander/sessions.json` | Sessions persistentes |
| `logs/commander/queue/*.json` | Cola de ordenes Telegram |
| `logs/daemon/cycles.jsonl` | Ciclos del daemon |
| `logs/daemon/feedback/*.json` | Feedback de Telegram |

## Aprendizajes Clave

1. **claude-agent-sdk query() es asincrono** — usa `async for message in query()` para streaming
2. **bypassPermissions** elimina TODOS los dialogos — ideal para 24/7 autonomo
3. **La governance INSTRUCTION_HIERARCHY** se dispara si el system prompt contiene `[INSTRUCTION]` entre brackets — usar texto plano
4. **ThinkingBlocks** del output pueden disparar governance rules — filtrar solo TextBlocks
5. **SSL en macOS** falla con AgentMeet — necesita `ssl.CERT_NONE` context
6. **Session resume** via SDK funciona perfectamente — mismo session_id = memoria completa
7. **asyncio.gather** permite N agentes verdaderamente paralelos (no secuenciales)
8. **File-based queue** es la forma mas robusta de bridge Telegram<->terminal
9. **Deterministic decisions** en el daemon (plan_next) evitan gastar LLM en decisiones simples
10. **Budget per cycle** previene runaway costs — cada daemon tiene su propio limite

## Uso Rapido

```python
# Desde cualquier modulo DOF
from core.claude_commander import ClaudeCommander

commander = ClaudeCommander()

# Orden simple
result = await commander.command("Count Python files in core/")

# Con memoria persistente
result = await commander.persistent_command("my-agent", "Continue building the feature")

# Equipo paralelo
team = await commander.run_team("Review the system", {
    "quality": "Check code quality",
    "security": "Audit vulnerabilities",
})

# Health check
health = await commander.health_check()
# -> {"sdk": True, "peers": True, "agentmeet": True}
```
