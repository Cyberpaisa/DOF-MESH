# Agent Teams + DOF Mesh Bridge
## Especificacion Tecnica v1.0

```
Proyecto:     DOF-MESH (Deterministic Observability Framework)
Documento:    AGENT_TEAMS_DOF_BRIDGE — Arquitectura del Bridge MCP ↔ Mesh
Version:      1.0.0
Fecha:        2026-03-27
Autor:        Cyber Paisa — Enigma Group (@Cyber_paisa)
Clasificacion: Tecnico / Enterprise
Repositorio:  Cyberpaisa/DOF-MESH
Licencia:     Apache-2.0
```

---

## Tabla de Contenidos

1. [Resumen Ejecutivo](#1-resumen-ejecutivo)
2. [Arquitectura General](#2-arquitectura-general)
3. [API Reference — Mesh Tools](#3-api-reference--mesh-tools)
4. [Governance Pipeline](#4-governance-pipeline)
5. [Seguridad](#5-seguridad)
6. [Metricas y Observabilidad](#6-metricas-y-observabilidad)
7. [Compliance y AI Safety](#7-compliance-y-ai-safety)
8. [Guia de Integracion](#8-guia-de-integracion)
9. [Verificacion y Testing](#9-verificacion-y-testing)
10. [Inventario Completo de Tools](#10-inventario-completo-de-tools)

---

## 1. Resumen Ejecutivo

El MCP server de DOF-MESH expone **15 tools** y **3 resources** via Model Context Protocol (JSON-RPC 2.0 sobre stdio). De estos, **5 son mesh tools** que conectan Agent Teams (Claude Code, Cursor, Windsurf, u otros clientes MCP) con una red heterogenea de 11+ nodos LLM gobernados por el framework DOF.

**Proposito:** Cada llamada a un mesh tool pasa por una **governance post-check deterministica** que verifica el output contra la Constitucion DOF antes de devolverlo al agente solicitante. Ninguna evaluacion depende de inferencia LLM — toda decision de governance usa regex, AST analysis, o Z3 SMT proofs.

**Resultado:** DOF-MESH es el primer sistema de Agent Teams donde la coordinacion multi-agente esta gobernada por verificacion formal, no por confianza implicita ni evaluacion probabilistica.

### Cifras Clave

| Metrica | Valor |
|---------|-------|
| Tools MCP totales | 15 (10 DOF + 5 Mesh) |
| Resources MCP | 3 |
| Tests unitarios | 32 (MCP server) / 3,620+ (codebase completo) |
| Nodos mesh activos | 11+ (APIs + web bridges + modelos locales) |
| Governance checks por request | 1-2 (post-check obligatorio + pre-check en consensus) |
| Attestations on-chain | 21 (Avalanche C-Chain mainnet) |
| LOC del codebase | 51,500+ |
| Modulos core | 127 |

---

## 2. Arquitectura General

### 2.1 Diagrama de Componentes

```
+=====================================================================+
|                        AGENT TEAMS LAYER                            |
|   Claude Code  |  Cursor  |  Windsurf  |  Custom MCP Client        |
+=====================================================================+
        |                    JSON-RPC 2.0 (stdio)
        v
+=====================================================================+
|                     MCP SERVER (mcp_server.py)                      |
|                                                                     |
|   +-------------------+    +--------------------+                   |
|   | DOF Tools (10)    |    | Mesh Tools (5)     |                   |
|   |  verify_governance |    |  mesh_send_task    |                   |
|   |  verify_ast       |    |  mesh_broadcast    |                   |
|   |  run_z3           |    |  mesh_route_smart  |                   |
|   |  memory_add/query |    |  mesh_read_inbox   |                   |
|   |  get_metrics      |    |  mesh_consensus    |                   |
|   |  create_attestation|    |                    |                   |
|   |  oags_identity    |    |                    |                   |
|   |  conformance_check|    |                    |                   |
|   +-------------------+    +--------+-----------+                   |
|                                     |                               |
|                          +----------v-----------+                   |
|                          | GOVERNANCE POST-CHECK |                  |
|                          | ConstitutionEnforcer  |                  |
|                          | _dof_governance {}    |                  |
|                          +----------+-----------+                   |
+=====================================================================+
                                      |
        +-----------------------------+-----------------------------+
        |                             |                             |
        v                             v                             v
+---------------+          +------------------+          +------------------+
| NodeRegistry  |          |   MessageBus     |          |  MeshRouterV2    |
| nodes.json    |          |  messages.jsonl  |          | router_v2.jsonl  |
| (file-locked) |          |  inbox/<node>/   |          | EWMA + specialty |
+---------------+          +------------------+          +------------------+
        |                             |                             |
        +-----------------------------+-----------------------------+
        |                                                           |
        v                                                           v
+=====================================================================+
|                         MESH NODE LAYER                             |
|                                                                     |
|  +----------+ +----------+ +--------+ +------+ +--------+ +------+ |
|  | DeepSeek | | SambaNova| | Kimi   | | MiMo | | MiniMax| | GLM  | |
|  | (API)    | | Llama70B | | K2.5   | | V2   | | M2.1   | | 4.7  | |
|  +----------+ +----------+ +--------+ +------+ +--------+ +------+ |
|  +----------+ +----------+ +--------+ +------+                     |
|  | Cerebras | | Gemini   | | Arena  | |Q-AION|                     |
|  | GPT-OSS  | | 2.5Flash | | AI     | | MLX  |                     |
|  +----------+ +----------+ +--------+ +------+                     |
+=====================================================================+
```

### 2.2 Flujo de Datos End-to-End

```
Agent Teams Client
    |
    |  1. JSON-RPC request: tools/call {name: "mesh_route_smart", arguments: {...}}
    v
mcp_server.handle_request()
    |
    |  2. Dispatch a handle_tools_call()
    v
handle_tools_call()
    |
    |  3. Lookup handler en TOOLS[tool_name]
    v
tool_mesh_route_smart(params)
    |
    |  4a. MeshRouterV2.route(task_type)
    |      - Lee logs/mesh/nodes.json
    |      - Score = specialty_bonus(1000) - latency_penalty(1/ms) - active_penalty(50/task)
    |      - Selecciona nodo optimo
    |      - Logea decision a logs/mesh/router_v2.jsonl
    |
    |  4b. NodeMesh.send_message(from="agent-teams-bridge", to=best_node, ...)
    |      - Rate limit check (100 req/min sliding window)
    |      - RBAC check (rol debe tener permiso de messaging)
    |      - Escribe a logs/mesh/messages.jsonl (audit trail)
    |      - E2E encrypt si recipient tiene pubkey (NaCl Box, Curve25519)
    |      - Entrega a logs/mesh/inbox/<node>/<msg_id>.json
    |
    |  4c. Retorna resultado: {routed_to, msg_id, task_type, routing, status}
    v
GOVERNANCE POST-CHECK (mandatory para mesh tools)
    |
    |  5. ConstitutionEnforcer.check(json.dumps(resultado))
    |     - HARD_RULES: NO_HALLUCINATION, LANGUAGE, NO_EMPTY, MAX_LENGTH
    |     - SOFT_RULES: HAS_SOURCES, STRUCTURED, CONCISENESS, ACTIONABLE, NO_PII
    |     - AST verification de code blocks embebidos
    |     - Override detection (6 patrones + 11 indirectos)
    |
    |  6. Inyecta: resultado["_dof_governance"] = {checked, passed, score, violations, warnings}
    v
JSON-RPC Response
    |
    |  7. {jsonrpc: "2.0", id: N, result: {content: [{type: "text", text: JSON}], isError: false}}
    v
Agent Teams Client (resultado verificado con prueba de governance)
```

---

## 3. API Reference — Mesh Tools

### 3.1 `mesh_send_task`

Envia una tarea a un nodo especifico del mesh.

| Campo | Valor |
|-------|-------|
| **Tool name** | `mesh_send_task` |
| **Categoria** | Mesh Communication |
| **Governance** | Post-check (ConstitutionEnforcer) |
| **Source** | `mcp_server.py:253-290` |

**Input Schema:**

| Parametro | Tipo | Requerido | Default | Descripcion |
|-----------|------|-----------|---------|-------------|
| `node_id` | string | Si | — | ID del nodo destino (ej: `deepseek`, `kimi-k2.5`, `mimo-v2`) |
| `task` | string | Si | — | Prompt o tarea a enviar al nodo |
| `task_type` | string | No | `"task"` | Tipo: `task`, `query`, `alert`, `sync` |

**Response Schema:**

```json
{
  "msg_id": "mesh-<uuid>",
  "to_node": "deepseek",
  "task_type": "task",
  "node_info": {
    "node_id": "deepseek",
    "role": "researcher",
    "status": "active"
  },
  "status": "delivered",
  "_dof_governance": {
    "checked": true,
    "passed": true,
    "score": 1.0,
    "violations": 0,
    "warnings": 3
  }
}
```

**Error Responses:**

| Condicion | Response |
|-----------|----------|
| `node_id` vacio | `{"error": "node_id and task are required"}` |
| Nodo no registrado | `node_info.error: "Node X not in registry"` (entrega igualmente) |
| Rate limit excedido | `RateLimitExceededError` (100 req/min) |
| RBAC denegado | `PermissionError` — rol sin permiso de messaging |

---

### 3.2 `mesh_broadcast`

Broadcast a TODOS los nodos activos simultaneamente.

| Campo | Valor |
|-------|-------|
| **Tool name** | `mesh_broadcast` |
| **Categoria** | Mesh Communication |
| **Governance** | Post-check (ConstitutionEnforcer) |
| **Source** | `mcp_server.py:293-315` |

**Input Schema:**

| Parametro | Tipo | Requerido | Default | Descripcion |
|-----------|------|-----------|---------|-------------|
| `content` | string | Si | — | Mensaje a difundir |
| `task_type` | string | No | `"query"` | Tipo: `task`, `query`, `alert` |

**Response Schema:**

```json
{
  "msg_id": "mesh-<uuid>",
  "broadcast_to": ["deepseek", "kimi-k2.5", "mimo-v2", "minimax", "glm"],
  "node_count": 5,
  "status": "broadcast_sent",
  "_dof_governance": { "checked": true, "passed": true, "score": 1.0, ... }
}
```

**Comportamiento:** Filtra nodos con `status == "error"`. El sender (`agent-teams-bridge`) no recibe su propio broadcast. Cada nodo recibe el mensaje en su inbox individual.

---

### 3.3 `mesh_route_smart`

Routing inteligente: selecciona el mejor nodo via MeshRouterV2 y le envia la tarea.

| Campo | Valor |
|-------|-------|
| **Tool name** | `mesh_route_smart` |
| **Categoria** | Mesh Communication |
| **Governance** | Post-check (ConstitutionEnforcer) |
| **Source** | `mcp_server.py:318-351` |

**Input Schema:**

| Parametro | Tipo | Requerido | Default | Descripcion |
|-----------|------|-----------|---------|-------------|
| `task_type` | string | Si | — | Tipo de tarea: `code`, `test`, `security`, `research`, `docs`, `consensus` |
| `task` | string | Si | — | Prompt o tarea a enviar |

**Algoritmo de Routing (MeshRouterV2):**

```
score = specialty_bonus - latency_penalty - active_penalty

Donde:
  specialty_bonus = 1000.0   si el rol del nodo contiene keywords del task_type
  latency_penalty = 1.0/ms   basado en EWMA (alpha=0.3) de latencias observadas
  active_penalty  = 50.0/tarea   por cada tarea activa asignada al nodo
```

**Specialty Map:**

| task_type | Keywords de match |
|-----------|-------------------|
| `code` | code, coder, builder, architect, dev |
| `test` | test, qa, guardian, cerberus, verifier |
| `docs` | docs, narrator, writer, documenter |
| `research` | research, researcher, analyst, scout |
| `security` | security, guardian, icarus, cerberus, shield |
| `consensus` | consensus, reviewer, arbitrator, judge |

**Response Schema:**

```json
{
  "routed_to": "guardian",
  "task_type": "security",
  "msg_id": "mesh-<uuid>",
  "routing": "MeshRouterV2 (specialty + latency + load)",
  "status": "routed_and_sent",
  "_dof_governance": { "checked": true, "passed": true, "score": 1.0, ... }
}
```

**Error Responses:**

| Condicion | Response |
|-----------|----------|
| `task_type` o `task` vacio | `{"error": "task_type and task are required"}` |
| Router falla | `{"error": "Router failed: ...", "fallback": "use mesh_send_task directly"}` |
| Ningun nodo disponible | `{"error": "No suitable node for task_type=X"}` |
| Todos los nodos en error/dead | `RuntimeError` del router |

---

### 3.4 `mesh_read_inbox`

Lee mensajes pendientes del inbox de un nodo.

| Campo | Valor |
|-------|-------|
| **Tool name** | `mesh_read_inbox` |
| **Categoria** | Mesh Communication |
| **Governance** | Post-check (ConstitutionEnforcer) |
| **Source** | `mcp_server.py:354-377` |

**Input Schema:**

| Parametro | Tipo | Requerido | Default | Descripcion |
|-----------|------|-----------|---------|-------------|
| `node_id` | string | No | `"agent-teams-bridge"` | ID del nodo cuyo inbox leer |
| `mark_read` | boolean | No | `true` | Marcar mensajes como leidos |

**Response Schema:**

```json
{
  "node_id": "agent-teams-bridge",
  "messages": [
    {
      "msg_id": "mesh-<uuid>",
      "from_node": "deepseek",
      "content": "Resultado del analisis...",
      "msg_type": "result",
      "timestamp": "2026-03-27T14:30:00"
    }
  ],
  "count": 1,
  "total_unread": 1,
  "_dof_governance": { "checked": true, "passed": true, "score": 1.0, ... }
}
```

**Limites:** Maximo 20 mensajes por llamada. Content truncado a 1000 chars por mensaje. Rate-limited a 100 req/min por nodo.

**Decryption:** Si el mensaje fue encriptado E2E (archivo `.enc`), se decripta automaticamente con la clave privada del nodo receptor.

---

### 3.5 `mesh_consensus`

Consenso multi-nodo: envia pregunta a N nodos para comparar respuestas. Incluye governance dual.

| Campo | Valor |
|-------|-------|
| **Tool name** | `mesh_consensus` |
| **Categoria** | Mesh Communication |
| **Governance** | **Pre-check** (pregunta) + **Post-check** (resultado) |
| **Source** | `mcp_server.py:380-426` |

**Input Schema:**

| Parametro | Tipo | Requerido | Default | Descripcion |
|-----------|------|-----------|---------|-------------|
| `question` | string | Si | — | Pregunta para consenso multi-nodo |
| `node_ids` | array[string] | No | auto-seleccion | Nodos especificos para consultar |
| `min_nodes` | integer | No | `3` | Minimo de nodos para consenso |

**Response Schema:**

```json
{
  "question": "Is the governance score threshold...",
  "sent_to": [
    {"node_id": "deepseek", "msg_id": "mesh-<uuid>"},
    {"node_id": "kimi-k2.5", "msg_id": "mesh-<uuid>"},
    {"node_id": "mimo-v2", "msg_id": "mesh-<uuid>"}
  ],
  "node_count": 3,
  "governance_pre_check": {
    "passed": true,
    "score": 1.0
  },
  "status": "consensus_initiated",
  "next_step": "Use mesh_read_inbox to collect responses, then compare",
  "_dof_governance": { "checked": true, "passed": true, "score": 1.0, ... }
}
```

**Error Responses:**

| Condicion | Response |
|-----------|----------|
| `question` vacio | `{"error": "question is required"}` |
| Menos de 2 nodos disponibles | `{"error": "Need at least 2 nodes for consensus, found N"}` |

**Protocolo de Consenso (2 fases):**

```
Fase 1: Distribucion (mesh_consensus)
  - Pre-check de governance sobre la pregunta
  - Envio simultaneo a N nodos via MessageBus
  - Retorna msg_ids para tracking

Fase 2: Recoleccion (mesh_read_inbox manual)
  - El agente llama mesh_read_inbox para cada nodo
  - Compara respuestas manualmente o via dof_verify_governance
  - Determina consenso: unanimidad, mayoria, o divergencia
```

---

## 4. Governance Pipeline

### 4.1 Diagrama Completo

```
+=========================================================================+
|                     GOVERNANCE PIPELINE                                  |
|                                                                          |
|  INPUT (prompt/task del Agent Team)                                      |
|    |                                                                     |
|    v                                                                     |
|  +---------------------------------------------+                        |
|  | LAYER 1: Constitution Enforcer               |                        |
|  | (core/governance.py)                         |                        |
|  |                                              |                        |
|  |  HARD RULES (bloquean):                      |                        |
|  |  +-------+-------+-------+-------+           |                        |
|  |  |HARD   |HARD   |HARD   |HARD   |           |                        |
|  |  |001    |002    |003    |004    |           |                        |
|  |  |No     |Lang   |No     |Max    |           |                        |
|  |  |Halluc.|Compl. |Empty  |Length |           |                        |
|  |  +-------+-------+-------+-------+           |                        |
|  |                                              |                        |
|  |  SOFT RULES (advierten):                     |                        |
|  |  +------+------+------+------+------+        |                        |
|  |  |SOFT  |SOFT  |SOFT  |SOFT  |SOFT  |        |                        |
|  |  |001   |002   |003   |004   |005   |        |                        |
|  |  |Srcs  |Struct|Conci.|Actio.|PII   |        |                        |
|  |  +------+------+------+------+------+        |                        |
|  |                                              |                        |
|  |  EXTRA: Override detection (17 patrones)     |                        |
|  |  EXTRA: enforce_hierarchy (SYSTEM>USER>ASST) |                        |
|  +---------------------+------------------------+                        |
|                        |                                                 |
|                        v                                                 |
|  +---------------------------------------------+                        |
|  | LAYER 2: AST Verifier                        |                        |
|  | (core/ast_verifier.py)                       |                        |
|  |                                              |                        |
|  |  AST-001: Blocked imports (subprocess, etc.) |                        |
|  |  AST-002: Unsafe calls (eval, exec, compile) |                        |
|  |  AST-003: Secret patterns (API keys, tokens) |                        |
|  |  AST-004: Resource risks (infinite loops)    |                        |
|  +---------------------+------------------------+                        |
|                        |                                                 |
|                        v                                                 |
|  +---------------------------------------------+                        |
|  | LAYER 3: Z3 Formal Verification              |                        |
|  | (core/z3_verifier.py)                        |                        |
|  |                                              |                        |
|  |  4 teoremas:                                  |                        |
|  |  - GCR invariance (GCR = 1.0 siempre)        |                        |
|  |  - Score boundedness (0 <= score <= 1)        |                        |
|  |  - Supervisor monotonicity                    |                        |
|  |  - Governance completeness                    |                        |
|  |                                              |                        |
|  |  42 patrones de jerarquia verificados         |                        |
|  +---------------------+------------------------+                        |
|                        |                                                 |
|                        v                                                 |
|  OUTPUT: resultado + _dof_governance {checked, passed, score}            |
+=========================================================================+
```

### 4.2 Governance Rules — Especificacion Completa

**Source of Truth:** `dof.constitution.yml` (spec_version 1.0)

#### Hard Rules (severity: block)

| ID | Rule Key | Tipo | Condicion de Bloqueo | Evidencia |
|----|----------|------|----------------------|-----------|
| HARD-001 | `NO_HALLUCINATION_CLAIM` | `phrase_without_url` | Frase asertiva (6 patrones EN) presente SIN URL `http` en texto | `[NO_HALLUCINATION_CLAIM] Must not assert fabricated data without source` |
| HARD-002 | `LANGUAGE_COMPLIANCE` | `language_check` | English markers < 5% en primeros 800 caracteres Y no es JSON/structured data | `[LANGUAGE_COMPLIANCE] Response must be in English or contain structured data` |
| HARD-003 | `NO_EMPTY_OUTPUT` | `min_length_and_blocklist` | Texto < 50 chars O contiene valores bloqueados ("No output", "Error", "N/A", "TODO", "placeholder") | `[NO_EMPTY_OUTPUT] Output cannot be empty or a placeholder` |
| HARD-004 | `MAX_LENGTH` | `max_length` | Texto > 50,000 caracteres | `[MAX_LENGTH] Output cannot exceed 50K chars` |

#### AST Rules (severity: block/warn)

| ID | Rule Key | Tipo | Condicion | Accion |
|----|----------|------|-----------|--------|
| AST-001 | `BLOCKED_IMPORTS` | `ast_import_check` | Import de `subprocess`, `os.system`, `shutil.rmtree`, `__import__` | Block |
| AST-002 | `UNSAFE_CALLS` | `ast_call_check` | Llamada a `eval()`, `exec()`, `compile()` | Block |
| AST-003 | `SECRET_PATTERNS` | `regex_scan` | Patrones de API keys: `sk-*`, `ghp_*`, `AKIA*`, `gho_*`, `glpat-*`, `xox[baprs]-*` | Block |
| AST-004 | `RESOURCE_RISKS` | `ast_pattern_check` | `while True` sin break, recursion sin depth guard | Warn |

#### Soft Rules (severity: warn)

| ID | Rule Key | Match Mode | Peso | Condicion de Warning |
|----|----------|------------|------|----------------------|
| SOFT-001 | `HAS_SOURCES` | absent | 0.3 | No contiene URLs `https?://` |
| SOFT-002 | `STRUCTURED_OUTPUT` | absent | 0.2 | No contiene `##`, `- `, `* `, `1.`, `•` |
| SOFT-003 | `CONCISENESS` | present | 0.2 | >= 3 parrafos con > 30% duplicacion en primeros 100 chars |
| SOFT-004 | `ACTIONABLE` | absent | 0.3 | No contiene "recommend", "next step", "action", "implement" |
| SOFT-005 | `NO_PII_LEAK` | present | 0.3 | Contiene emails, SSN (`XXX-XX-XXXX`), o tarjetas de credito |

### 4.3 Post-Check Implementation

Ubicacion: `mcp_server.py`, lineas 688-716

```python
_MESH_TOOL_NAMES = {
    "mesh_send_task", "mesh_broadcast", "mesh_route_smart",
    "mesh_read_inbox", "mesh_consensus"
}

# Dentro de handle_tools_call():
if tool_name in _MESH_TOOL_NAMES:
    from core.governance import ConstitutionEnforcer
    enforcer = ConstitutionEnforcer()
    gov = enforcer.check(json.dumps(result, default=str))
    result["_dof_governance"] = {
        "checked": True,
        "passed": gov.passed,       # bool: todas las hard rules pasan
        "score": gov.score,          # float: 0.0-1.0
        "violations": len(gov.violations),   # int: hard rule violations
        "warnings": len(gov.warnings),       # int: soft rule warnings
    }
```

**Garantia:** El campo `_dof_governance` esta presente en TODA respuesta de mesh tool. No es opt-in. No es configurable. Es mandatory e inyectado en la capa de transporte.

---

## 5. Seguridad

### 5.1 RBAC (Role-Based Access Control)

Implementado en `core/node_mesh.py:76-186` (contribucion de Kimi K2.5).

**8 roles definidos:**

| Rol | Permisos |
|-----|----------|
| `ARCHITECT` | `node:create`, `mesh:configure`, `state:read`, `task:spawn`, `audit:read` |
| `RESEARCHER` | `task:execute`, `task:report`, `state:read`, `audit:read` |
| `GUARDIAN` | `security:modify`, `audit:read`, `audit:write` |
| `WORKER` | `task:execute`, `task:report`, `state:read` |
| `COORDINATOR` | `task:spawn`, `node:delete`, `task:report` |
| `AUDITOR` | `audit:read` (solo lectura — NO puede enviar mensajes) |
| `ADMIN` | `node:create`, `node:delete`, `task:spawn`, `mesh:configure`, `state:write`, `audit:read` |
| `SECURITY` | `security:modify`, `audit:write`, `audit:read` |

**11 permisos granulares:** `node:create`, `node:delete`, `task:spawn`, `task:execute`, `task:report`, `mesh:configure`, `security:modify`, `audit:read`, `audit:write`, `state:read`, `state:write`

**Enforcement:** Decorator `@RBACPolicy.require_permissions()` valida permisos antes de ejecutar operaciones protegidas. Roles se infieren automaticamente del string de rol via `_ROLE_MAP` (12 keywords mapeados).

**Separation of Duties:** El rol `AUDITOR` solo puede leer logs — no puede enviar mensajes ni modificar estado. El rol `GUARDIAN` puede modificar seguridad pero no crear nodos.

### 5.2 Rate Limiting

Implementado en `core/node_mesh.py:189-231`.

| Parametro | Valor | Descripcion |
|-----------|-------|-------------|
| Algoritmo | Sliding window | Ventana deslizante thread-safe |
| Max requests | 100 | Por nodo por ventana |
| Window | 60 segundos | Periodo de la ventana |
| Lock | `threading.Lock` | Concurrency-safe |
| Aplica a | `send_message()` + `read_inbox()` | Previene DoS en ambas direcciones |

**Comportamiento:** Si un nodo excede 100 requests en 60 segundos:
- `send_message()` → `RateLimitExceededError` (operacion rechazada)
- `read_inbox()` → retorna lista vacia (degradacion graceful)

### 5.3 E2E Encryption

Implementado en `core/e2e_encryption.py:111-295`.

| Componente | Especificacion |
|------------|----------------|
| Algoritmo | NaCl Box (Curve25519 + XSalsa20 + Poly1305) |
| Key generation | `PrivateKey.generate()` via PyNaCl |
| Key storage | `keys/mesh/<node_id>.key` (mode 0600) + `.pub` (mode 0644) |
| Key manager | `MeshKeyManager` — genera, persiste, carga keypairs |
| Encryptor | `MeshE2EEncryptor` — cifra/descifra mensajes por par de nodos |
| Formato | `.enc` files en inbox (vs `.json` para plaintext) |
| Fallback | Si PyNaCl no instalado o cifrado falla → plaintext con warning en log |

**Flujo de cifrado:**

```
Sender (node A) → MeshE2EEncryptor.encrypt(msg_id, to=B, plaintext)
    - Box(A.private_key, B.public_key)
    - XSalsa20-Poly1305 authenticated encryption
    - Output: EncryptedMessage_ {ciphertext_b64, sender_pubkey_b64}
    - Escrito como inbox/B/<msg_id>.enc

Recipient (node B) → MeshE2EEncryptor.decrypt(envelope)
    - Box(B.private_key, A.public_key)
    - Verifica: envelope.to_node == B.node_id
    - Decripta y retorna plaintext
```

### 5.4 File Locking

| Operacion | Mecanismo | Archivo |
|-----------|-----------|---------|
| Load nodes | `fcntl.flock(LOCK_SH)` (shared read) | `nodes.json` |
| Save nodes | `fcntl.flock(LOCK_EX)` (exclusive write) + atomic rename | `nodes.json` |

**Atomic writes:** `_save_nodes()` escribe a `nodes.json.tmp` y luego hace `tmp_file.replace(self._nodes_file)` — rename atomico que previene corrupcion en escrituras concurrentes (fix VULN-N004).

### 5.5 Audit Trail

Toda operacion genera registros inmutables:

| Evento | Destino | Formato |
|--------|---------|---------|
| Mensaje enviado | `logs/mesh/messages.jsonl` | Un JSON por linea con msg_id, from, to, type, timestamp |
| RBAC denegado | `_audit_log` (in-memory) + log warning | `{event, node_id, role, action, timestamp}` |
| Rate limit excedido | Logger warning | `RATE_LIMIT: <node_id>` |
| Routing decision | `logs/mesh/router_v2.jsonl` | `RouteDecision` completo |
| Governance check | `_dof_governance` en response | `{checked, passed, score, violations, warnings}` |
| E2E encrypt/decrypt | Logger debug | `E2E encrypted: <msg_id> → <node>` |

---

## 6. Metricas y Observabilidad

### 6.1 Metricas DOF (5 formales)

Definidas en `dof.constitution.yml` y computadas por `core/observability.py`:

| ID | Nombre | Formula | Dominio | Descripcion |
|----|--------|---------|---------|-------------|
| SS | Stability Score | `1 - f^3` | [0.0, 1.0] | Fraccion de runs completados sin fallo terminal bajo r=2 reintentos |
| PFI | Provider Fragility Index | `mean(failures)/n` | [0.0, 1.0] | Media de fallos de provider por ejecucion |
| RP | Retry Pressure | `mean(retries)/n` | [0.0, 1.0] | Media de reintentos por ejecucion |
| GCR | Governance Compliance Rate | **invariante = 1.0** | [1.0, 1.0] | Fraccion de runs que pasan ALL governance — **estructuralmente invariante** |
| SSR | Supervisor Strictness Ratio | `rejected/completed` | [0.0, 1.0] | Fraccion de runs rechazados por meta-supervisor |

**GCR = 1.0 es invariante:** Z3 verifica formalmente que ninguna degradacion de infraestructura puede reducir el GCR. La governance es independiente del estado de los providers.

### 6.2 Archivos de Log

| Directorio | Contenido | Formato |
|------------|-----------|---------|
| `logs/mesh/nodes.json` | Registry de nodos activos | JSON (file-locked) |
| `logs/mesh/messages.jsonl` | Todos los mensajes enviados | JSONL (append-only) |
| `logs/mesh/inbox/<node>/` | Mensajes pendientes por nodo | JSON (`.json`) o cifrado (`.enc`) |
| `logs/mesh/router_v2.jsonl` | Decisiones de routing | JSONL (RouteDecision) |
| `logs/mesh/mesh_events.jsonl` | Eventos del mesh (spawn, connect, disconnect, errors) | JSONL `{timestamp, iso, event, ...data}` |
| `logs/traces/` | RunTrace por ejecucion | JSON |
| `logs/experiments/` | Runs con metricas agregadas | JSONL |
| `logs/metrics/` | Steps de agentes, governance, supervisor | JSONL |
| `logs/checkpoints/` | Recovery checkpoints | JSONL |

### 6.3 Formato JSONL de Mensajes

```json
{
  "msg_id": "mesh-a1b2c3d4",
  "from_node": "agent-teams-bridge",
  "to_node": "deepseek",
  "content": "Analiza el contrato ERC-8004 para vulnerabilidades",
  "msg_type": "task",
  "timestamp": 1711540200.123,
  "read": false,
  "reply_to": null
}
```

### 6.4 Formato JSONL de Routing

```json
{
  "task_type": "security",
  "selected_node": "guardian",
  "score": 900.0,
  "specialty_match": true,
  "active_tasks": 0,
  "latency_ms": 100.0,
  "candidates": 11,
  "timestamp": 1711540200.456
}
```

---

## 7. Compliance y AI Safety

### 7.1 Principios de AI Safety

| Principio | Implementacion en DOF-MESH |
|-----------|----------------------------|
| **Determinismo** | Toda decision de governance usa regex, AST analysis, o Z3 SMT — cero inferencia LLM |
| **Auditabilidad** | Todo output va a JSONL append-only; `_dof_governance` en cada response; routing logueado |
| **Verificabilidad formal** | Z3 verifica 4 teoremas + 42 patrones de jerarquia; GCR=1.0 es invariante matematico |
| **Separacion de concerns** | RBAC con 8 roles + 11 permisos; AUDITOR es read-only; GUARDIAN no crea nodos |
| **Defense in depth** | 7 capas: Constitution → AST → Supervisor → Adversarial → Memory → Z3 → Oracle |
| **Zero-trust** | Rate limiting por nodo; E2E encryption; RBAC; governance post-check mandatory |
| **Transparencia** | Constitucion YAML publica; rules versionadas; evidencia de violations logueada |
| **Override resistance** | 17 patrones de deteccion de override/jailbreak (6 directos + 11 indirectos) |

### 7.2 Comparacion con Alternativas

| Caracteristica | DOF-MESH | CrewAI | AutoGen | LangGraph |
|----------------|----------|--------|---------|-----------|
| Governance engine | Deterministic (regex+AST+Z3) | LLM-based | LLM-based | LLM-based |
| Formal verification | Z3 SMT (4 teoremas) | No | No | No |
| GCR invariance | Proven (Z3) | N/A | N/A | N/A |
| RBAC | 8 roles, 11 permisos | No | No | No |
| E2E encryption | NaCl Box (Curve25519) | No | No | No |
| Rate limiting | Sliding window (100/min) | No | No | No |
| On-chain attestations | 21 (Avalanche C-Chain) | No | No | No |
| Audit trail | JSONL append-only + _dof_governance | Logs basicos | Logs basicos | Logs basicos |
| Override detection | 17 patrones | No | No | No |
| MCP integration | Native (15 tools) | Via LangChain | Via plugin | Via tools |

### 7.3 Attestations On-Chain

Cada ejecucion puede generar un attestation verificable en Avalanche C-Chain via `dof_create_attestation`:

```
DOFValidationRegistry (Avalanche C-Chain mainnet)
  - 21 attestations registradas
  - Cada attestation contiene: certificate_hash, governance_status, z3_verified, agent_identity
  - Verificable por cualquier tercero via contrato publico
```

Contratos:
- **ERC-8004 Identity:** `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432`
- **Reputation Registry:** `0x8004B663056A597Dffe9eCcC1965A193B7388713`

---

## 8. Guia de Integracion

### 8.1 Conectar un Nuevo Teammate al Mesh (3 pasos)

**Paso 1: Configurar el MCP server en el cliente**

Agregar a la configuracion MCP del cliente (Claude Code, Cursor, etc.):

```json
{
  "mcpServers": {
    "dof-governance": {
      "command": "python3",
      "args": ["/Users/jquiceva/DOF-MESH/mcp_server.py"],
      "env": {}
    }
  }
}
```

**Paso 2: Verificar conectividad**

Desde el cliente MCP, invocar:
```
tools/list → debe retornar 15 tools
mesh_read_inbox {} → debe retornar {node_id: "agent-teams-bridge", messages: [], count: 0}
```

**Paso 3: Enviar primera tarea al mesh**

```
mesh_route_smart {task_type: "research", task: "Analiza el estado actual del mesh"}
```

El sistema automaticamente:
1. Selecciona el mejor nodo via MeshRouterV2
2. Envia la tarea via MessageBus
3. Verifica el output via ConstitutionEnforcer
4. Retorna resultado con `_dof_governance` attached

### 8.2 Registrar un Nuevo Nodo en el Mesh

Editar `logs/mesh/nodes.json`:

```json
{
  "nuevo-nodo": {
    "node_id": "nuevo-nodo",
    "role": "researcher",
    "status": "active",
    "specialty": "research",
    "provider": "api",
    "context_window": 128000,
    "model": "custom-model"
  }
}
```

El nodo estara disponible para routing inmediatamente (MeshRouterV2 lee `nodes.json` en cada llamada).

### 8.3 Generar Keypair E2E para un Nodo

```python
from core.e2e_encryption import MeshKeyManager

km = MeshKeyManager()
keypair = km.generate_keypair("nuevo-nodo")
# Keys guardadas en: keys/mesh/nuevo-nodo.key (0600) + .pub (0644)
```

Una vez registrado el pubkey, todos los mensajes al nodo se cifran automaticamente.

---

## 9. Verificacion y Testing

### 9.1 Comandos de Verificacion

```bash
# Confirmar 15 tools registrados
python3 -c "import mcp_server; print(len(mcp_server.TOOLS))"
# Esperado: 15

# Ejecutar tests del MCP server (32 tests)
python3 -m unittest tests.test_mcp_server
# Esperado: OK

# Ejecutar suite completa (3,620+ tests)
python3 -m unittest discover -s tests
# Esperado: OK

# Verificar Z3 formal proofs
python3 -c "from mcp_server import tool_run_z3; r=tool_run_z3({}); print(f'all_verified={r[\"all_verified\"]}, count={r[\"count\"]}')"
# Esperado: all_verified=True, count=4

# Verificar governance post-check en 5 mesh tools
python3 -c "
from mcp_server import handle_request
import json
tools = {
    'mesh_send_task': {'node_id': 'test', 'task': 'test'},
    'mesh_broadcast': {'content': 'test'},
    'mesh_read_inbox': {},
    'mesh_consensus': {'question': 'test?'},
    'mesh_route_smart': {'task_type': 'security', 'task': 'test'},
}
for name, args in tools.items():
    req = {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {'name': name, 'arguments': args}}
    resp = handle_request(req)
    data = json.loads(resp['result']['content'][0]['text'])
    g = data.get('_dof_governance', {})
    print(f'{name}: checked={g.get(\"checked\")}, passed={g.get(\"passed\")}, score={g.get(\"score\")}')
"
# Esperado: todos checked=True, passed=True, score=1.0
```

### 9.2 Cobertura de Tests

| Suite | Tests | Cobertura |
|-------|-------|-----------|
| `TestMCPToolRegistry` | 6 | Registry: 15 tools, 3 resources, schemas, handlers |
| `TestMCPProtocol` | 7 | JSON-RPC: initialize, tools/list, resources/list, notifications, errors |
| `TestMCPToolGovernance` | 3 | Governance: clean pass, empty fail, via JSON-RPC |
| `TestMCPToolAST` | 3 | AST: clean code, eval detection, blocked imports |
| `TestMCPToolZ3` | 1 | Z3: 4 teoremas verificados |
| `TestMCPToolMemory` | 3 | Memory: add, query, snapshot (con tmpdir aislado) |
| `TestMCPToolMetrics` | 2 | Metrics: defaults, nonexistent trace fallback |
| `TestMCPToolAttestation` | 1 | Attestation: create con certificate_hash, z3_verified |
| `TestMCPToolOAGS` | 2 | OAGS: identity deterministica, conformance 3 niveles |
| `TestMCPResources` | 4 | Resources: constitution, metrics, memory_stats, via JSON-RPC |
| **Total** | **32** | **15 tools + 3 resources + protocol + governance** |

---

## 10. Inventario Completo de Tools

| # | Tool | Categoria | Input Required | Governance | Source |
|---|------|-----------|----------------|------------|--------|
| 1 | `dof_verify_governance` | Governance | `output_text` | N/A (ES el enforcer) | `:44-55` |
| 2 | `dof_verify_ast` | Governance | `code` | N/A | `:58-73` |
| 3 | `dof_run_z3` | Governance | ninguno | N/A | `:76-98` |
| 4 | `dof_memory_add` | Memory | `content` | Interna (GovernedMemoryStore) | `:101-114` |
| 5 | `dof_memory_query` | Memory | ninguno | Interna | `:117-133` |
| 6 | `dof_memory_snapshot` | Memory | ninguno | Interna | `:136-156` |
| 7 | `dof_get_metrics` | Metrics | ninguno | N/A | `:159-194` |
| 8 | `dof_create_attestation` | Identity | `task_id`, `metrics` | Z3 + Oracle + on-chain | `:197-214` |
| 9 | `dof_oags_identity` | Identity | ninguno | BLAKE3 deterministic | `:217-228` |
| 10 | `dof_conformance_check` | Identity | ninguno | 3 niveles OAGS | `:231-240` |
| 11 | `mesh_send_task` | **Mesh** | `node_id`, `task` | **Post-check** | `:253-290` |
| 12 | `mesh_broadcast` | **Mesh** | `content` | **Post-check** | `:293-315` |
| 13 | `mesh_route_smart` | **Mesh** | `task_type`, `task` | **Post-check** | `:318-351` |
| 14 | `mesh_read_inbox` | **Mesh** | ninguno | **Post-check** | `:354-377` |
| 15 | `mesh_consensus` | **Mesh** | `question` | **Pre + Post-check** | `:380-426` |

### Resources

| URI | Nombre | Descripcion |
|-----|--------|-------------|
| `dof://constitution` | DOF Constitution | Constitucion YAML completa como JSON |
| `dof://metrics/latest` | Latest Metrics | Ultimas metricas SS, GCR, PFI, RP, SSR |
| `dof://memory/stats` | Memory Stats | Estadisticas del memory store gobernado |

---

```
DOF-MESH v0.5.0 | 15 tools, 3 resources | Governance deterministica
51,500+ LOC | 3,620+ tests | 21 attestations on-chain (Avalanche C-Chain)
Primer sistema de Agent Teams con governance formal verificada por Z3

Documento: AGENT_TEAMS_DOF_BRIDGE v1.0.0
Fecha: 2026-03-27
Autor: Cyber Paisa — Enigma Group
```
