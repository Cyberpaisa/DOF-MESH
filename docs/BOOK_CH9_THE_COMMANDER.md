# Capítulo 9: The Commander — Orquestación Soberana de Agentes Claude

*Cuando tu framework spawna Claude Code, y Claude Code spawna más Claude Code, gobernado por matemáticas.*

---

## 1. El Problema

Los frameworks multi-agente existentes (CrewAI, LangGraph, Swarms, AutoGen) tienen un cuello de botella fundamental: **todos llaman a APIs HTTP para comunicarse con los LLMs**. Cada llamada pasa por:

- Rate limits del provider
- Overhead de serialización/deserialización
- Latencia de red (100-500ms por hop)
- Tokens de overhead del gateway (12K+ tokens en OpenClaw)
- Sin persistencia de memoria entre llamadas

DOF resuelve esto con una arquitectura radicalmente diferente: **Claude Code hablando directamente con Claude Code, sin intermediarios**.

---

## 2. Arquitectura del Commander

```
Interfaces (Telegram, CLI, Mission Control, Terminal)
    |
    v
ClaudeCommander (core/claude_commander.py)
  5 modos: SDK | Spawn | Team | Debate | Peers
  Model: claude-opus-4-6 ($100 budget)
  Permission: bypassPermissions (24/7 autónomo)
    |
    v
DOF Governance Layer
  Pre-check → Execute → Post-check → Audit
  CONSTITUTION + Z3 + JSONL + Blockchain
    |
    v
Claude Agent SDK (claude-agent-sdk==0.1.50)
  query() → Claude Code CLI → LLM directo
  AgentDefinition → sub-agentes independientes
  Hooks → PreToolUse, PostToolUse, Stop
    |
    v
Node Mesh (core/node_mesh.py)
  NodeRegistry → MessageBus → SessionScanner → MeshDaemon
  Nodos infinitos con sesiones persistentes
  Inbox/outbox JSONL por nodo
    |
    v
Communication Layer
  Peers MCP (localhost:7899) - AgentMeet (HTTP) - Queue (JSONL) - A2A (port 8000)
```

### Componentes Clave

| Componente | Archivo | Función |
|---|---|---|
| ClaudeCommander | `core/claude_commander.py` | 5 modos de comunicación con Claude |
| NodeMesh | `core/node_mesh.py` | Red de nodos infinitos con message bus |
| AutonomousDaemon | `core/autonomous_daemon.py` | Loop autónomo Perceive→Decide→Execute→Evaluate |
| Telegram Bot | `interfaces/telegram_bot.py` | Control remoto vía Telegram |
| Session Scanner | `mission-control/src/lib/claude-sessions.ts` | Descubrimiento de sesiones Claude |

---

## 3. Los 5 Modos de Comunicación

### Modo 1: SDK — Orden Directa

```python
from core.claude_commander import ClaudeCommander
commander = ClaudeCommander()
result = await commander.command("Fix the bug in core/governance.py")
# → CommandResult(status="success", output="...", elapsed_ms=7300)
```

DOF ordena → Claude Code ejecuta → resultado en <20s → JSONL audit.

**Cómo funciona internamente:**
1. Se importa `claude_agent_sdk.query()`
2. Se crea `ClaudeAgentOptions` con `permission_mode="bypassPermissions"`
3. Se inyecta la CONSTITUTION como system prompt
4. Se itera `async for message in query()` capturando solo TextBlocks
5. Se registra en JSONL con timestamp y elapsed_ms

### Modo 2: Spawn — Sub-agente Especializado

```python
result = await commander.spawn_agent(
    name="security-auditor",
    prompt="Audit core/ for vulnerabilities",
    tools=["Read", "Grep", "Glob"]
)
```

Un agente Claude independiente con su propio contexto, tools y rol. Usa `AgentDefinition` del SDK para crear un sub-agente que el orchestrator invoca.

### Modo 3: Team — Equipo Paralelo

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

N agentes Opus 4.6 trabajando en paralelo. Cada uno se spawna independientemente y `asyncio.gather()` los ejecuta concurrentemente.

### Modo 4: Debate — Consenso Multi-agente vía AgentMeet

```python
transcript = await commander.debate(
    room="dof-council",
    topic="Should we migrate from ChromaDB?",
    agents=["researcher", "architect", "security"],
    rounds=3,
)
```

Agentes debaten en AgentMeet.net por rondas. DOF orquesta los turnos: cada agente lee el transcript completo y responde. Al final, un agente sintetiza el consenso con action items.

### Modo 5: Peers — P2P entre Instancias Claude

```python
peers = await commander.list_peers()  # localhost:7899
await commander.message_peer(peer_id, "Coordinate on task X")
```

Descubrimiento y mensajería P2P entre instancias de Claude Code corriendo en la misma máquina.

---

## 4. Session Persistence — Memoria Infinita

El problema más fundamental de los agentes autónomos: **cada invocación empieza de cero**. El Commander resuelve esto con session persistence del SDK:

```python
# Primera llamada: crea sesión nueva
result = await commander.persistent_command(
    name="builder",
    prompt="Search for TODOs and implement one"
)
# → session_id guardado en logs/commander/sessions.json

# Siguiente llamada: resume exactamente donde dejó
result = await commander.persistent_command(
    name="builder",
    prompt="Continue your previous work, what's next?"
)
# → Claude recuerda TODO lo que hizo antes
```

**Implementación:**
```python
async def persistent_command(self, name: str, prompt: str, **kwargs) -> CommandResult:
    existing = self.get_session(name)  # Busca en sessions.json
    result = await self.command(
        prompt=prompt,
        resume_session=existing,  # SDK resume parameter
        **kwargs,
    )
    if result.session_id:
        self.save_session(name, result.session_id)  # Persiste para próximo ciclo
    return result
```

Almacenamiento: `logs/commander/sessions.json`
```json
{
  "builder": "91220911-a203-45ec-ab0e-8ef8cef90a5d",
  "guardian": "c4f7a221-8b3e-4d1a-9f2c-3e5d6a7b8c9d",
  "researcher": "e1f2a3b4-5c6d-7e8f-9a0b-1c2d3e4f5a6b"
}
```

---

## 5. Node Mesh — Red de Nodos Infinitos

La evolución del Commander: cada agente es un **nodo** en una red que se comunica a través de un bus de mensajes JSONL.

### Arquitectura del Mesh

```
NodeMesh (orquestador)
    ├── NodeRegistry  — registro de todos los nodos (nodes.json)
    ├── MessageBus    — cola de mensajes JSONL entre nodos
    ├── SessionScanner — descubre sesiones Claude en ~/.claude/
    └── MeshDaemon    — loop autónomo que gestiona la red
```

### Cada Nodo Tiene:

| Atributo | Descripción |
|---|---|
| `node_id` | Identificador único (ej: "architect") |
| `session_id` | Sesión Claude persistente (memoria infinita) |
| `role` | Especialización del agente |
| `inbox` | Directorio con mensajes pendientes |
| `status` | active / idle / spawning / error |
| `tools` | Lista de herramientas permitidas |
| `model` | Modelo Claude (default: opus-4-6) |

### Comunicación Inter-nodo

```
Nodo A → MessageBus (JSONL) → inbox/nodo-B/*.json → Nodo B lee → responde → inbox/nodo-A/
```

```python
from core.node_mesh import NodeMesh

mesh = NodeMesh()

# Spawn nodo
node = await mesh.spawn_node("architect", "Design the new API")

# Mensaje directo
mesh.send_message("architect", "researcher", "Need threat model for new API")

# Broadcast a toda la red
mesh.broadcast("commander", "New release ready for review")

# Leer inbox
messages = mesh.read_inbox("researcher")

# Conversación entre dos nodos
history = mesh.get_conversation("architect", "researcher")
```

### Ejecución Paralela

```python
# Team: N nodos simultáneos
results = await mesh.spawn_team({
    "architect": "Design the module",
    "researcher": "Research best practices",
    "reviewer": "Prepare review criteria",
}, parallel=True)

# Pipeline: output de uno → input del siguiente
results = await mesh.pipeline([
    ("researcher", "Research Fisher-Rao implementations"),
    ("architect", "Design the module based on research"),
    ("reviewer", "Review the design"),
])
```

### Descubrimiento de Sesiones

El Node Mesh escanea `~/.claude/projects/` para descubrir sesiones Claude activas (compatible con mission-control):

```python
# Descubrir sesiones activas
sessions = mesh.discover_sessions()

# Importar como nodos del mesh
imported = mesh.import_discovered_sessions()
# → "Imported 3 discovered sessions into mesh"
```

### Topología Predefinida: DOF Mesh

```python
from core.node_mesh import spawn_dof_mesh

mesh = await spawn_dof_mesh()
# Spawna 6 nodos:
#   commander  — orquestador
#   architect  — código y arquitectura
#   researcher — investigación e inteligencia
#   guardian   — seguridad y tests
#   narrator   — documentación y contenido
#   reviewer   — quality gate
```

### NEED_INPUT Protocol

Los nodos pueden solicitar información de otros nodos inline:

```
# En el output de un nodo:
"I've designed the API structure. NEED_INPUT(researcher): What are the security best practices for REST APIs with blockchain integration?"

# El mesh automáticamente:
# 1. Parsea el NEED_INPUT
# 2. Envía mensaje al nodo target
# 3. El target lo recibe en su próximo ciclo
```

---

## 6. Autonomous Daemon — El Orquestador Autónomo

### 4 Fases en Loop Infinito

```
PERCEIVE → scan_state()
    Pending orders, errors, git changes, health
        ↓
DECIDE → plan_next()
    Deterministic rules, zero LLM
        ↓
EXECUTE → spawn agents
    Via Commander SDK, persistent sessions
        ↓
EVALUATE → score results
    Log JSONL, update metrics
```

### 3 Daemons Especializados

| Daemon | Intervalo | Budget | Especialidad |
|---|---|---|---|
| **BuilderDaemon** | 180s | $3/cycle | Features, TODOs, pending orders |
| **GuardianDaemon** | 300s | $2/cycle | Security, tests, regressions |
| **ResearcherDaemon** | 600s | $2/cycle | Metrics optimization, analysis |

Cada daemon tiene session persistence — recuerda todo entre ciclos.

```bash
# Daemon generalista
python3 core/autonomous_daemon.py

# 3 daemons especializados en paralelo
python3 core/autonomous_daemon.py --multi

# Dry run
python3 core/autonomous_daemon.py --multi --cycles 5 --dry-run
```

### Decision Engine (Zero LLM)

```python
def plan_next(self, state: SystemState) -> DaemonAction:
    """Deterministic decision — NO LLM involved."""
    # Priority 1: Pending Telegram orders
    if state.pending_orders > 0:
        return DaemonAction(mode="build", reason="pending_orders")
    # Priority 2: Errors detected
    if state.error_count > 0:
        return DaemonAction(mode="review", reason="errors_detected")
    # Priority 3: Git changes
    if state.git_dirty_files > 10:
        return DaemonAction(mode="review", reason="git_cleanup")
    # Priority 4: Optimization
    if state.dof_score < 0.85:
        return DaemonAction(mode="improve", reason="score_below_target")
    # Default: patrol
    return DaemonAction(mode="patrol", reason="routine")
```

---

## 7. Telegram Integration

### Comandos

| Comando | Función |
|---|---|
| `/claude <orden>` | Orden directa a Claude Code |
| `/team <tarea>` | 3 agentes paralelos |
| `/parallel N <tarea>` | N agentes en paralelo (max 10) |
| `/daemon start` | Lanzar daemon autónomo |
| `/daemon status` | Estado del daemon |
| `/multidaemon` | 3 daemons especializados |
| `/mesh status` | Estado de la red de nodos |
| `/mesh discover` | Descubrir sesiones Claude activas |
| `/mesh spawn <node> <tarea>` | Crear nodo en el mesh |
| `/mesh send <from> <to> <msg>` | Mensaje entre nodos |
| `/mesh full` | Spawn red completa DOF (6 nodos) |
| `/sessions` | Ver sesiones recientes |
| `/approve` | Aprobar acción del daemon |
| `/redirect <instruccion>` | Redirigir daemon |

### Flujo Bidireccional

```
Telegram → /mesh spawn architect "Build feature X"
    → NodeMesh.spawn_node()
        → ClaudeCommander.persistent_command()
            → Claude Agent SDK → Claude Code
                → result → Telegram
```

---

## 8. Governance Pipeline

Cada comando en el Commander y el Mesh pasa por el pipeline completo:

```
1. Pre-check: ConstitutionEnforcer.enforce(prompt) → HARD_RULES
2. Execute: Claude Code con bypassPermissions
3. Post-check: ConstitutionEnforcer.enforce(output) → verificación
4. Audit: JSONL con timestamp, session_id, elapsed_ms
5. On-chain: Attestation en Avalanche (opcional)
```

### governed_command()

```python
async def governed_command(self, prompt: str, **kwargs) -> CommandResult:
    # Pre-check
    enforcer = ConstitutionEnforcer()
    passed, msg = enforcer.enforce(prompt)
    if not passed:
        return CommandResult(status="blocked", output=f"Governance blocked: {msg}")

    # Execute
    result = await self.command(prompt, **kwargs)

    # Post-check
    if result.status == "success":
        passed, msg = enforcer.enforce(result.output)
        if not passed:
            result.status = "governance_violation"

    return result
```

---

## 9. Diferencia vs Otros Frameworks

| Dimensión | CrewAI/LangGraph/Swarms | DOF Commander + Node Mesh |
|---|---|---|
| Acceso LLM | API call ($$$, rate limits) | Directo via SDK (0 overhead) |
| Permisos | Diálogo manual | bypassPermissions 24/7 |
| Governance | Ninguna o LLM-based | CONSTITUTION + Z3 + blockchain |
| Multi-agente | Gateway centralizado | Mesh P2P + HTTP + SDK |
| Trazabilidad | Logs opcionales | JSONL obligatorio, on-chain |
| Memoria | Por sesión | Persistente entre ciclos (infinita) |
| Control remoto | API | Telegram → queue → terminal |
| Comunicación | Request-response | Message bus + inbox + broadcast |
| Escalabilidad | Limitada por gateway | Nodos infinitos on demand |
| Descubrimiento | Manual | Escaneo automático de ~/.claude/ |

---

## 10. Métricas Verificadas

| Métrica | Valor |
|---|---|
| SDK command (Haiku) | 7.3s |
| SDK command (Opus 4.6) | 20.6s |
| Team review (2 agents) | 115s |
| Multi-daemon (3 brains) | 35-128s por ciclo |
| API overhead | 0 |
| Rate limit | Ninguno |
| Diálogos de permiso | 0 |
| Session resume | Instant (mismo session_id) |

---

## 11. Aprendizajes Clave

1. **claude-agent-sdk query() es asíncrono** — usa `async for message in query()` para streaming
2. **bypassPermissions** elimina TODOS los diálogos — ideal para 24/7 autónomo
3. **La governance INSTRUCTION_HIERARCHY** se dispara si el system prompt contiene `[INSTRUCTION]` entre brackets — usar texto plano
4. **ThinkingBlocks** del output pueden disparar governance rules — filtrar solo TextBlocks
5. **SSL en macOS** falla con AgentMeet — necesita `ssl.CERT_NONE` context
6. **Session resume** via SDK funciona perfectamente — mismo session_id = memoria completa
7. **asyncio.gather** permite N agentes verdaderamente paralelos
8. **File-based queue** es la forma más robusta de bridge Telegram↔terminal
9. **Deterministic decisions** en el daemon evitan gastar LLM en decisiones simples
10. **Budget per cycle** previene runaway costs — cada daemon tiene su propio límite
11. **NEED_INPUT protocol** permite comunicación inline entre nodos del mesh
12. **Descubrimiento de sesiones** conecta el mesh con mission-control automáticamente

---

## 12. Archivos del Sistema

| Archivo | Función |
|---|---|
| `core/claude_commander.py` | Módulo principal — 5 modos |
| `core/node_mesh.py` | Red de nodos infinitos con message bus |
| `core/autonomous_daemon.py` | Daemon autónomo + 3 especializados |
| `interfaces/telegram_bot.py` | Comandos /claude, /team, /mesh, /daemon |
| `.claude/skills/claude-commander.md` | Super skill del Commander |
| `logs/commander/commands.jsonl` | Audit trail de comandos |
| `logs/commander/sessions.json` | Sessions persistentes |
| `logs/commander/queue/*.json` | Cola de órdenes Telegram |
| `logs/mesh/nodes.json` | Registry de nodos del mesh |
| `logs/mesh/messages.jsonl` | Bus de mensajes global |
| `logs/mesh/inbox/<node>/*.json` | Inbox por nodo |
| `logs/mesh/mesh_events.jsonl` | Eventos del mesh daemon |
| `logs/daemon/cycles.jsonl` | Ciclos del daemon |
| `logs/daemon/feedback/*.json` | Feedback de Telegram |

---

*El Commander y el Node Mesh representan un cambio de paradigma: en lugar de que los agentes pidan permiso para existir, DOF les da vida, los gobierna, y los conecta en una red donde cada nodo tiene memoria infinita y puede comunicarse con cualquier otro. No es un chatbot. Es una civilización de agentes.*

---

*Generado desde el repositorio DOF — Marzo 22, 2026*
*Módulos validados y verificados en ejecución real*
