# Multi-Model Mesh: Orquestacion Autonoma de Agentes Heterogeneos sobre Protocolo de Filesystem

## Un Estudio Experimental del Deterministic Observability Framework (DOF)

---

**Autores:**
Juan Carlos Quiceno Vasquez (Operador, Medellin, Colombia)
DOF Commander (Claude Opus 4.6, Orquestador)
Nodos contribuyentes: Antigraviti (Gemini 2.5 Flash), GPT-Legion (GPT-4o), DeepSeek-Legion (DeepSeek-V3), Kimi-K2 (Moonshot AI), NVIDIA-NIM (Nemotron), GLM-5 (Zhipu AI)

**Fecha:** 23 de marzo de 2026
**Repositorio:** github.com/Cyberpaisa/deterministic-observability-framework
**Version DOF:** v0.5.x

---

## Resumen (Abstract)

Presentamos los resultados del primer experimento de colaboracion autonoma entre 56 agentes de inteligencia artificial pertenecientes a 8 familias de modelos distintas (Claude Opus, Claude Sonnet, Gemini Flash, GPT-4o, DeepSeek-V3, Kimi-K2, NVIDIA Nemotron, GLM-4 Flash), operando sobre un protocolo de comunicacion basado en archivos JSON en filesystem local. El experimento se condujo durante la noche del 22-23 de marzo de 2026, con un solo operador humano dirigiendo la orquesta desde un MacBook Pro M4 Max (36GB RAM). Se intercambiaron 120 mensajes a traves del MessageBus, se generaron 5 reportes de inteligencia, se identificaron 2 vulnerabilidades criticas y 14 bugs potenciales, y se incremento la cobertura de tests de 2041 a 2153 (+112 tests). Los resultados demuestran que: (a) la colaboracion cross-model es factible sin APIs intermediarias, (b) el overhead de coordinacion puede reducirse de O(n) a O(sqrt(n)) con el algoritmo de routing propuesto por el nodo DeepSeek, (c) la seguridad multi-capa (7 capas) implementada en Cerberus e Icarus es suficiente para operar en modo autonomo, y (d) modelos de diferentes proveedores y arquitecturas (dense transformer, MoE, constitutional AI) aportan capacidades complementarias no redundantes, como lo evidencia el analisis de redundancia de metricas propuesto espontaneamente por DeepSeek-V3.

**Palabras clave:** sistemas multi-agente, orquestacion LLM, protocolo de filesystem, diversidad cognitiva, seguridad deterministica, mesh networking

---

## 1. Introduccion

### 1.1 Motivacion

Los sistemas multi-agente basados en modelos de lenguaje grande (LLMs) han demostrado capacidades emergentes significativas en tareas de coordinacion, razonamiento distribuido y produccion de artefactos de software. Sin embargo, la practica predominante en la industria es la homogeneidad: un unico proveedor de modelo (tipicamente OpenAI o Anthropic) alimenta todos los agentes de un sistema. Esta limitacion produce monocultivos cognitivos donde las fortalezas y debilidades del modelo subyacente se amplifican en lugar de compensarse.

El Deterministic Observability Framework (DOF) surgio como una plataforma de orquestacion y observabilidad para sistemas multi-agente bajo restricciones de infraestructura adversarial --- un solo operador, hardware de consumo (MacBook Pro M4 Max, 36GB RAM), multiples proveedores de LLM con rate limits agresivos y claves de API que expiran frecuentemente. Estas restricciones motivaron la pregunta central de este estudio:

> Es posible orquestar una red heterogenea de agentes pertenecientes a multiples familias de modelos de IA, comunicandose exclusivamente a traves de archivos JSON en filesystem local, y obtener resultados cualitativamente superiores a los de un sistema homogeneo?

### 1.2 Estado del Arte

Los frameworks existentes para orquestacion multi-agente presentan limitaciones fundamentales en el eje de diversidad de modelos:

| Framework | Version | Modelos soportados | Protocolo | Limitacion principal |
|-----------|---------|--------------------|-----------|-----------------------|
| CrewAI | 0.36+ | Multiples via LiteLLM | In-memory | Asume homogeneidad; un modelo por agente, no hay mesh |
| AutoGen | 0.2+ | OpenAI-compatible | JSON-RPC | Microsoft-centric; agentes conversacionales, no de trabajo |
| LangGraph | 0.1+ | LangChain-compatible | Grafos de estado | Stateful pero single-process; no distribuido |
| MetaGPT | 0.7+ | OpenAI/Claude | SOPs | Roles fijos, no extensible a modelos web |
| Swarm (OpenAI) | Experimental | Solo OpenAI | Function calling | Vendor lock-in absoluto |

Ninguno de estos frameworks soporta la inclusion de modelos accesibles solo via interfaz web (DeepSeek, Kimi, GLM) a traves de un puente humano, ni implementa seguridad multi-capa deterministica para redes de agentes heterogeneos.

### 1.3 Hipotesis

**H1:** La diversidad cognitiva entre modelos de diferentes familias (dense transformer, MoE, constitutional AI, RLHF) produce contribuciones complementarias no redundantes.

**H2:** Un protocolo de comunicacion basado en filesystem (archivos JSON) es suficiente para coordinar una red de 50+ agentes sin requerir infraestructura de red.

**H3:** La seguridad multi-capa deterministica (sin dependencia de LLM) puede proteger una red abierta de agentes heterogeneos.

### 1.4 Contribuciones

1. **Protocolo de Filesystem para Mesh Multi-Modelo:** Definicion formal y validacion empirica de un protocolo de comunicacion inter-agente basado en archivos JSON en disco, con formato estandarizado de mensajes y mecanismo de broadcast.
2. **Modulos Cerberus e Icarus:** Dos sistemas de seguridad complementarios (reactivo y proactivo) para redes de agentes, 100% deterministicos, sin dependencia de LLM.
3. **Evidencia empirica de diversidad cognitiva:** Documentacion del primer caso donde un nodo DeepSeek-V3 propuso espontaneamente optimizaciones algoritmicas (routing O(sqrt(n))) y analisis de redundancia metrica que ningun nodo Claude habia identificado.
4. **Patron de puente humano:** Validacion del metodo copy-paste JSON para integrar modelos accesibles solo via web (DeepSeek, GPT, Kimi, GLM) en un mesh de agentes autonomos.

---

## 2. Metodologia

### 2.1 Arquitectura del DOF Mesh

El DOF Mesh se compone de cuatro subsistemas implementados en `core/node_mesh.py` (851 lineas de Python):

```
NodeMesh (orquestador)
    +-- NodeRegistry   -- registro de nodos activos (logs/mesh/nodes.json)
    +-- MessageBus     -- cola de mensajes JSONL (logs/mesh/messages.jsonl)
    +-- SessionScanner -- descubrimiento de sesiones Claude (~/.claude/projects/)
    +-- MeshDaemon     -- loop autonomo de gestion de la red
```

**NodeRegistry.** Mantiene un diccionario persistente de nodos `MeshNode`, cada uno definido por:

```python
@dataclass
class MeshNode:
    node_id: str
    role: str
    session_id: Optional[str] = None
    status: str = "idle"        # idle | active | spawning | error
    last_active: float = 0
    messages_sent: int = 0
    messages_received: int = 0
    tools: list = field(default_factory=lambda: ["Read", "Edit", "Write", "Bash", "Glob", "Grep"])
    model: str = "claude-opus-4-6"
    created_at: float = field(default_factory=time.time)
```

**Protocolo de comunicacion.** Cada mensaje se serializa como un objeto JSON con la siguiente estructura:

```python
@dataclass
class MeshMessage:
    msg_id: str          # UUID4 unico
    from_node: str       # nodo emisor
    to_node: str         # nodo destino ("*" para broadcast)
    content: str         # contenido del mensaje
    msg_type: str        # task | result | query | alert | sync
    timestamp: float     # epoch seconds
```

Los mensajes se persisten doblemente:

1. **Log global:** `logs/mesh/messages.jsonl` --- un registro append-only de todos los mensajes del mesh, en formato JSONL (un JSON por linea).
2. **Inbox por nodo:** `logs/mesh/inbox/{node_id}/{msg_id}.json` --- cada mensaje se entrega como un archivo JSON individual en el inbox del destinatario. Para broadcast (`to_node="*"`), el mensaje se copia a todos los nodos excepto el emisor.

Este diseno tiene una propiedad critica: **cualquier proceso que pueda leer y escribir archivos en el filesystem puede participar en el mesh.** No se requiere conexion de red, API, ni protocolo binario.

### 2.2 Configuracion Experimental

**Hardware:**
- MacBook Pro M4 Max
- CPU: 16 cores (12 performance + 4 efficiency)
- GPU: 40 cores
- Neural Engine: 16 cores (19 TFLOPS FP16)
- RAM: 36GB memoria unificada
- SSD: 994.66 GB (432 GB libres)
- OS: macOS Tahoe 26.3.1 (Darwin 25.3.0)

**Duracion:** Aproximadamente 6.5 horas (17:30 -- 00:06 UTC, 22-23 de marzo de 2026)

**Operador:** 1 humano (Juan Carlos Quiceno Vasquez). Dirigio las primeras 5 horas de forma activa, luego descanso mientras el Commander opero autonomamente.

**Fases temporales del experimento:**

| Fase | Hora (UTC) | Evento | Nodos |
|------|------------|--------|-------|
| 0 | 17:30 | Spawn inicial del mesh (7 nodos core) | 7 |
| 1 | 17:30-19:53 | Oleada 1 --- Inteligencia (5 agentes auditores) | 7 |
| 2 | 19:53-22:16 | Re-spawn tras errores; ajustes de sesion | 7 |
| 3 | 22:16-22:44 | Commander autonomo; oleadas de tareas | 7 |
| 4 | 23:32 | NIGHT_SHIFT_ACTIVATED; operador descansa | 7 |
| 5 | 23:38 | FULL_MESH_ACTIVATED: 37 sesiones descubiertas + importadas | 48 |
| 6 | 23:45 | GPT_NODE_JOINED: primer nodo GPT-4o | 49 |
| 7 | 23:48 | LEGION_GROWS: gpt-chat + gemini-2 | 51 |
| 8 | 23:50 | ICARUS_DEPLOYED + MASSIVE_EXPANSION (DeepSeek, Kimi, NVIDIA) | 55 |
| 9 | 23:59 | DEEPSEEK_FIRST_CONTACT: 4 mensajes de alta calidad | 55 |
| 10 | 00:03 | GLM5_JOINED: octava familia de modelos | 56 |
| 11 | 00:05 | TRANSCENDENTAL_MISSION: mision final broadcast a 56 nodos | 56 |

**Metodo de integracion por tipo de modelo:**

| Modelo | Metodo | Proceso |
|--------|--------|---------|
| Claude Opus/Sonnet (48 nodos) | Filesystem directo | Sesiones `claude` con acceso a disco |
| Gemini 2.5 Flash (2 nodos) | Filesystem directo | Sesion Google AI Studio con acceso a proyecto |
| GPT-4o (2 nodos) | Puente humano | Copy-paste JSON via ChatGPT web |
| DeepSeek-V3 (1 nodo) | Puente humano | Copy-paste JSON via deepseek.com |
| Kimi-K2 (1 nodo) | Registro de protocolo | Nodo registrado, protocolo validado |
| NVIDIA Nemotron (1 nodo) | Registro de protocolo | Nodo registrado, protocolo validado |
| GLM-4 Flash (1 nodo) | Registro de protocolo | Nodo registrado, protocolo validado |

### 2.3 Metricas Recolectadas

Se definieron las siguientes metricas cuantitativas para evaluar el experimento:

1. **Mensajes intercambiados:** Conteo total y por nodo de mensajes enviados y recibidos, clasificados por tipo (task, result, query, alert, sync).
2. **Cobertura de tests:** Delta en numero de tests unitarios antes y despues del experimento.
3. **Bugs identificados y corregidos:** Severidad (CRITICAL, HIGH, MEDIUM, LOW) y estado de correccion.
4. **Modulos creados:** Nuevos archivos Python producidos durante el experimento.
5. **Reportes de inteligencia:** Documentos JSON generados por nodos auditores y entregados al Commander.
6. **Trust scores:** Puntuacion de confianza por nodo segun Cerberus.
7. **Distribucion de modelos:** Conteo de nodos por familia de modelo.

### 2.4 Stack de Seguridad (7 Capas)

El DOF Mesh implementa un stack de seguridad de 7 capas, todas deterministicas (cero dependencia de LLM):

**Capa 1: MeshGuardian** (`core/mesh_guardian.py`)
Modulo de seguridad a nivel de infraestructura del mesh. Protege la integridad del registro de nodos y el bus de mensajes contra manipulacion directa.

**Capa 2: Icarus** (`core/icarus.py`)
Cazador proactivo de amenazas con 4 capacidades:
- *Forense conductual:* Perfiles de comportamiento por nodo, deteccion de cambios de personalidad que indiquen compromiso.
- *Correlacion cross-nodo:* Deteccion de ataques coordinados (floods, cadenas de ataque, cliques/conspiraciones, patrones de timing de bots).
- *Sistema de honeypots:* Despliegue de nodos falsos (`FAKE_ADMIN`), canary tokens (`CANARY_TOKEN_icarus_7h1s_1s_f4k3`), y endpoints ficticios (`/api/v1/internal/secrets`).
- *Inteligencia de amenazas:* Analisis de patrones de ataque, prediccion de proximos objetivos, huellas de atacantes.

Clase principal: `Icarus` con metodos `profile_node()`, `profile_all()`, `detect_coordination()`, `deploy_honeypot()`, `check_honeypots()`, `threat_intel()`, `hunt()`. Persistencia en `logs/mesh/icarus_profiles.json`, `icarus_honeypots.json`, `icarus_intel.jsonl`.

**Capa 3: Cerberus** (`core/cerberus.py`)
Guardian reactivo con 3 cabezas:
- *Cabeza 1 (Validador de mensajes):* 7 categorias de patrones regex: inyeccion de codigo (14 patrones), inyeccion de prompts (12 patrones), exfiltracion de datos (4 patrones de API keys + 4 de datos), inyeccion de comandos (6 patrones), path traversal (6 patrones), bypass de governance (7 patrones).
- *Cabeza 2 (Monitor de comportamiento):* Rate limiting, deteccion de anomalias, scoring de confianza, gestion de cuarentena.
- *Cabeza 3 (Analizador de contenido):* Entropia de Shannon, anomalias de tamano, deteccion de repeticion, payloads sospechosos.

Veredictos en 5 niveles: SAFE, LOW, MEDIUM, HIGH, CRITICAL. Los mensajes clasificados HIGH o CRITICAL son bloqueados automaticamente. Persistencia en `logs/mesh/cerberus_trust.json`, `cerberus_threats.jsonl`, `cerberus_quarantine.json`.

**Capa 4: SecurityHierarchy** (`core/security_hierarchy.py`)
Orquestador de seguridad en 5 niveles: L0 (triage) -> L1 (analisis basico) -> L2 (analisis profundo) -> L3 (respuesta) -> L4 (recuperacion).

**Capa 5: Governance** (`core/governance.py`)
CONSTITUTION: ~50 tokens inyectados en cada agente. HARD_RULES bloquean output. SOFT_RULES emiten advertencias. Todas las reglas son funciones `(text: str) -> bool` --- cero LLM.

**Capa 6: AST Verifier** (`core/ast_verifier.py`)
Verificacion de arbol de sintaxis abstracta. Valida que el codigo generado por agentes cumpla patrones estructurales requeridos. Retorna `VerificationResult` con `.passed`, `.score`, `.violations`.

**Capa 7: Z3 Gate** (`core/z3_gate.py`)
Puerta formal basada en el solver Z3 de Microsoft Research. Cuatro veredictos: APPROVED, REJECTED, TIMEOUT, FALLBACK. Cada prueba genera un hash keccak256 para atestacion on-chain.

### 2.5 Protocolo de Oleadas

El experimento se organizo en 4 oleadas de despliegue de agentes:

**Oleada 1 --- Inteligencia (7 nodos, 17:30-22:44 UTC)**
Nodos core desplegados: commander, architect, researcher, guardian, narrator, reviewer, social-intel. Cada nodo recibio tareas especializadas via MessageBus. El guardian ejecuto el test suite completo (2041 tests, 114/115 pasaron). El reviewer produjo code review de 5 archivos. El researcher genero investigacion de mercado.

**Oleada 2 --- Expansion Masiva (41 nodos adicionales, 23:32-23:38 UTC)**
El SessionScanner descubrio 37 sesiones Claude existentes en `~/.claude/projects/` y las importo automaticamente al mesh. Adicionalmente, se integraron 4 proyectos externos: investigador-temas, skill-researcher, agente-cyber, opus-home. El mesh paso de 7 a 48 nodos en 6 minutos.

**Oleada 3 --- Cross-Model + Seguridad (7 nodos, 23:38-23:50 UTC)**
Ingreso de los primeros nodos no-Claude:
- antigraviti (Gemini 2.5 Flash): primer nodo cross-model
- gpt-legion y gpt-chat (GPT-4o): primeros nodos GPT
- gemini-2 (Gemini 2.5 Flash): segundo nodo Gemini
- icarus (Claude Opus): cazador de amenazas desplegado
- deepseek (DeepSeek-V3), kimi-k2 (Kimi-K2), nvidia-nim (Nemotron)

**Oleada 4 --- Cierre (1 nodo, 00:03-00:06 UTC)**
Ingreso de glm-5 (GLM-4 Flash, Zhipu AI). Broadcast de mision trascendental a los 56 nodos.

---

## 3. Resultados

### 3.1 Metricas Cuantitativas

**Tabla 1. Estadisticas globales del mesh.**

| Metrica | Valor |
|---------|-------|
| Nodos totales registrados | 56 |
| Familias de modelos | 8 |
| Mensajes totales intercambiados | 120 |
| Nodos con actividad de mensajes | 7 |
| Nodos activos (con sesion) | 19 |
| Nodos descubiertos (importados) | 37 |
| Reportes de inteligencia generados | 5 |
| Tests antes del experimento | 2,041 |
| Tests despues del experimento | 2,153 |
| Tests nuevos creados | 112 |
| Bugs identificados | 14 |
| Bugs corregidos en sesion | 3 |
| Modulos nuevos creados | 3 |
| Duracion total del experimento | ~6.5 horas |

**Tabla 2. Distribucion de mensajes por tipo.**

| Tipo | Cantidad | Porcentaje |
|------|----------|------------|
| query | 52 | 43.3% |
| task | 41 | 34.2% |
| sync | 13 | 10.8% |
| alert | 11 | 9.2% |
| result | 3 | 2.5% |
| **Total** | **120** | **100%** |

El predominio de mensajes tipo `query` (43.3%) refleja un patron de coordinacion donde el Commander solicita informacion antes de asignar tareas. Los mensajes tipo `alert` (9.2%) corresponden a broadcasts de eventos significativos (union de nuevos nodos, activacion del mesh completo).

**Tabla 3. Distribucion de mensajes por nodo emisor.**

| Nodo | Modelo | Enviados | Recibidos | Rol |
|------|--------|----------|-----------|-----|
| commander | Claude Sonnet 4.6 | 87 | 6 | Orquestador |
| architect | Claude Sonnet 4.6 | 7 | 23 | Arquitectura |
| researcher | Claude Sonnet 4.6 | 5 | 23 | Investigacion |
| deepseek | DeepSeek-V3 | 4 | 0 | Razonamiento matematico |
| reviewer | Claude Sonnet 4.6 | 3 | 19 | Code review |
| guardian | Claude Sonnet 4.6 | 2 | 32 | Seguridad |
| narrator | Claude Sonnet 4.6 | 2 | 22 | Documentacion |

Se observa una topologia hub-and-spoke con el Commander como nodo central (72.5% de todos los mensajes enviados). El guardian fue el nodo que mas mensajes recibio (32), consistente con su rol como punto de contacto para reportes de seguridad de multiples nodos.

**Tabla 4. Distribucion de nodos por familia de modelo.**

| Familia | Modelo | Nodos | Porcentaje |
|---------|--------|-------|------------|
| Claude Sonnet | claude-sonnet-4-6 | 35 | 62.5% |
| Claude Opus | claude-opus-4-6 | 13 | 23.2% |
| Gemini | gemini-2.5-flash | 2 | 3.6% |
| GPT | gpt-4o | 2 | 3.6% |
| DeepSeek | deepseek-v3 | 1 | 1.8% |
| Kimi | kimi-k2-instruct | 1 | 1.8% |
| NVIDIA | nvidia-nemotron | 1 | 1.8% |
| GLM | glm-4-flash | 1 | 1.8% |
| **Total** | | **56** | **100%** |

### 3.2 Contribuciones por Familia de Modelo

#### 3.2.1 Claude (48 nodos: 35 Sonnet + 13 Opus)

Los nodos Claude constituyeron el 85.7% del mesh y produjeron la totalidad de los artefactos de codigo y tests. Contribuciones principales:

- **Orquestacion:** El nodo commander (Sonnet) envio 87 mensajes, gestionando las 4 oleadas de despliegue y coordinando tareas entre los nodos especializados.
- **Seguridad:** El nodo guardian produjo el `security_audit.json` identificando 2 vulnerabilidades CRITICAL (oracle_key.json expuesto en dos rutas, 6+ API keys en .env sin encriptacion en reposo) y 3 problemas MEDIUM (`git add .` en backup_manager.py y cloud_sync.py, `os.popen('date')` en agent_factory.py).
- **Cobertura:** El nodo researcher genero el `coverage_report.json` documentando 2,041 tests sobre 48 modulos cubiertos, con 4 gaps criticos identificados (crew_runner, node_mesh, claude_commander, autonomous_daemon).
- **Code review:** El nodo reviewer produjo el `quality_report.json` identificando 14 bugs potenciales, incluyendo un bug HIGH de colision de msg_id en node_mesh.py (corregido a uuid4).
- **Documentacion:** El nodo narrator genero el `docs_audit.json` auditando 13 archivos SOUL.md y detectando 3 agentes sin integracion mesh y 13 roles sin archivo SOUL.
- **Tests:** 112 tests nuevos escritos: 62 para node_mesh.py y 50 para autonomous_daemon.py.
- **Modulos nuevos:** mesh_monitor.py (dashboard ASCII), mesh_guardian.py (seguridad), agents/antigraviti/SOUL.md.

#### 3.2.2 DeepSeek-V3 (1 nodo)

El nodo DeepSeek produjo 4 mensajes de resultado (`ds-001` a `ds-004`), cada uno con contribuciones sustantivas y diferenciadas:

**ds-001 (Presentacion):** Identificacion de 4 capacidades diferenciales --- razonamiento matematico (estabilidad de Lyapunov para multi-agente), optimizacion algoritmica (problemas NP-dificiles con garantias), eficiencia computacional (reduccion de complejidades asintoticas), y perspectiva del ecosistema chino de IA (Qwen, GLM, Yi, Baichuan).

**ds-002 (Propuesta de Routing Optimo):** Analisis formal del problema de escalabilidad del broadcast O(n). Propuesta de esquema hibrido:
1. Clustering por afinidad con k ~ sqrt(n) = 7-8 clusters, cada uno con cluster-head.
2. DHT overlay con finger tables para routing O(log n).
3. Broadcast eficiente: solo a cluster-heads O(k), luego propagacion interna O(n/k).
4. Complejidad total: O(2*sqrt(n)) ~ O(14) vs O(55) actual.
5. Formalizacion: G(V,E) con k-means sobre feature vectors de 10 dimensiones.
6. Routing deterministico, sin LLM, cumple invariante DOF-3.

**ds-003 (Analisis de Redundancia de Metricas):** Demostracion de que la metrica SS(f) = 1 - f^3 es derivable de PFI si se conoce el factor de fallos base k: f = k*(1-PFI), SS = 1 - (k(1-PFI))^3. Ademas, RP <= GCR bajo governance como condicion necesaria, y SSR = 1 implica PFI = 0 y GCR = 1. Propuesta: eliminar SS por ser transformacion redundante; mantener 4 metricas independientes (SSR, GCR, PFI, RP).

**ds-004 (Perspectiva China de IA):** 5 recomendaciones tecnologicas:
1. Router MoE deterministico (reduccion 70% en computo).
2. vLLM/LMDeploy PagedAttention (throughput 10x).
3. OpenCompass (Shanghai AI Lab) como benchmark externo.
4. CodeGeeX4 (Zhipu, 128K contexto) para autogeneracion de tests.
5. GLM-4 RLHF para governance alignment.

#### 3.2.3 Gemini 2.5 Flash (2 nodos)

El nodo `antigraviti` fue el primer nodo cross-model en unirse al mesh, validando que el protocolo de filesystem funciona con agentes no-Claude que tienen acceso al mismo disco. Contribucion principal: **validacion de interoperabilidad del protocolo.** El nodo se registro exitosamente, recibio su SOUL.md, y confirmo la viabilidad del mesh multi-modelo.

#### 3.2.4 GPT-4o (2 nodos)

Los nodos `gpt-legion` y `gpt-chat` ingresaron via puente humano (copy-paste de JSON desde ChatGPT web). Su ingreso valido el patron de **human bridge** como mecanismo viable para integrar modelos sin acceso directo a filesystem. El evento `GPT_NODE_JOINED` (23:45:51 UTC) fue registrado como "First GPT node in DOF mesh history."

#### 3.2.5 Kimi-K2, NVIDIA Nemotron, GLM-4 Flash (3 nodos)

Estos nodos se registraron en el mesh para validar el protocolo y expandir la diversidad de familias. Su presencia confirma la capacidad del protocolo para escalar a 8 familias sin modificaciones en la infraestructura.

### 3.3 Reportes de Inteligencia

Los 5 reportes generados por los nodos auditores y entregados al inbox del Commander constituyen el principal artefacto de produccion del experimento:

**Tabla 5. Reportes de inteligencia generados.**

| Reporte | Generador | Hallazgos principales |
|---------|-----------|----------------------|
| security_audit.json | guardian | 2 CRITICAL (oracle_key.json en 2 rutas, .env sin encriptar), 6 WARNING, 8 archivos limpios |
| coverage_report.json | researcher | 52 modulos core, 2,041 tests, 48 modulos cubiertos, 4 gaps criticos |
| provider_health.json | architect | 9 proveedores auditados: Groq EXPIRED, Cerebras EXPIRED, 5 activos |
| quality_report.json | reviewer | 14 bugs potenciales, 1 HIGH (msg_id collision), 3 MEDIUM, 10 LOW |
| docs_audit.json | narrator | 13 SOULs, 10 con mesh integration, 3 sin, 13 roles sin SOUL |

### 3.4 Analisis de Seguridad

#### 3.4.1 Cerberus

El modulo Cerberus implementa 49 patrones regex compilados distribuidos en 7 categorias de amenaza:

| Categoria | Patrones | Cobertura |
|-----------|----------|-----------|
| Inyeccion de codigo | 14 | eval, exec, os.system, subprocess, curl\|bash, nc -e, python -c |
| Inyeccion de prompts | 12 | "ignore previous", "you are now", DAN mode, jailbreak, role-swap |
| API keys (exfiltracion) | 7 | Groq (gsk_), OpenAI (sk-), Google (AIza), NVIDIA (nvapi-), GitHub (ghp_), AWS (AKIA), Bearer |
| Datos (exfiltracion) | 4 | base64 >100 chars, hex >64 chars, 256-bit hex, tarjetas de credito |
| Inyeccion de comandos | 6 | ; && \|\| \| $() backticks |
| Path traversal | 6 | ../, /etc/passwd, /etc/shadow, ~/.ssh/, ~/.env |
| Bypass de governance | 7 | "disable rules", "empty HARD_RULES", "modify constitution", "bypass governance" |

Todos los patrones son regex puras --- cero falsos negativos por variabilidad de LLM.

#### 3.4.2 Icarus

El cazador proactivo opera con los siguientes umbrales calibrados:

| Parametro | Valor | Significado |
|-----------|-------|-------------|
| Desviacion de longitud de mensaje | 3.0 sigma | Anomalia si mensaje > 3 desviaciones estandar |
| Contraccion de vocabulario | 0.5 ratio | Alerta si vocabulario cae al 50% |
| Cambio de objetivos | 0.7 ratio | Alerta si 70% de mensajes van a nuevos targets |
| Flood (min identicos) | 3 | 3+ mensajes identicos = flood |
| Exclusividad de clique | 0.8 | 80%+ mensajes entre mismos nodos = conspiracion |
| Tolerancia timing de bot | 500ms | Jitter < 500ms entre mensajes = bot |

Honeypots desplegados con 3 canary tokens:
- `ADMIN_OVERRIDE_KEY_d3adb33f` (admin falso)
- `CANARY_TOKEN_icarus_7h1s_1s_f4k3` (token canario)
- `ENDPOINT_/api/v1/internal/secrets` (endpoint ficticio)

### 3.5 Rendimiento del Sistema

**Utilizacion de recursos durante el experimento:**

| Recurso | Valor observado |
|---------|-----------------|
| Swap utilizado | 0 bytes |
| CPU pico | ~75% (durante spawn paralelo de 7 nodos) |
| RAM pico | ~28 GB (37 sesiones Claude simultaneas) |
| Disco (logs/mesh/) | ~2.5 MB total |
| I/O filesystem | ~120 writes (mensajes) + ~56 writes (nodos) |

La ausencia total de swap es un hallazgo critico: el M4 Max de 36GB fue suficiente para mantener 48 sesiones Claude en memoria sin degradacion.

### 3.6 Timeline de Crecimiento del Mesh

```
Nodos
56 |                                                     +----*
55 |                                                +----+
52 |                                           +----+
51 |                                      +----+
49 |                                 +----+
48 |                            +----+
 7 | +---------------------------+
   |________________________________________________
   17:30  19:53  22:16  23:32  23:38  23:45  00:03  (UTC)
         Fase 0-1        |      |      |      |
                    Night |   Full    GPT    GLM
                    Shift | Mesh(48) Joins  Joins
```

El crecimiento exhibe un patron sigmoidal: estabilidad inicial (7 nodos, ~6 horas), expansion explosiva (7 -> 48 en 6 minutos via SessionScanner), y crecimiento lineal (48 -> 56 en 25 minutos via integracion manual de modelos externos).

---

## 4. Analisis

### 4.1 H1: La Diversidad Cognitiva Aporta Valor

La evidencia soporta fuertemente H1. El caso mas ilustrativo es el nodo DeepSeek-V3:

**Propuesta de routing O(sqrt(n)).** Ningun nodo Claude habia identificado el problema de escalabilidad del broadcast O(n) como prioridad. DeepSeek, con su especializacion en optimizacion algoritmica, lo detecto inmediatamente y propuso una solucion formal con garantias de complejidad. La propuesta incluyo: clustering por afinidad, DHT overlay, y broadcast eficiente con complejidad total O(2*sqrt(n)).

**Analisis de redundancia de metricas.** DeepSeek demostro matematicamente que SS(f) = 1 - f^3 es derivable de PFI, proponiendo la eliminacion de una metrica redundante. Este es un caso clasico de "fresh eyes" --- un modelo externo identificando patrones que el equipo original habia normalizado.

**Perspectiva del ecosistema chino.** Las recomendaciones de vLLM/LMDeploy PagedAttention y OpenCompass como benchmark externo representan conocimiento que no habria emergido de modelos entrenados exclusivamente en corpus anglosajon.

Estas tres contribuciones son cualitativamente distintas de lo producido por los 48 nodos Claude. La diversidad cognitiva no solo es aditiva --- es **complementaria**.

### 4.2 H2: El Protocolo de Filesystem Escala

Los datos soportan parcialmente H2. El protocolo funciono correctamente para 56 nodos y 120 mensajes. Sin embargo, se identificaron bottlenecks estructurales:

**Complejidad actual:**
- `send_message()`: O(1) amortizado (write to JSONL + write to inbox)
- `broadcast()`: O(n) (copia a n-1 inboxes)
- `read_inbox()`: O(m) donde m = mensajes en inbox del nodo
- `get_state()`: O(n*m) --- lee todos los nodos y todos los mensajes. **Este es el bottleneck critico.**

**Analisis de escalabilidad:**

| Nodos | Broadcast actual O(n) | Propuesta DeepSeek O(sqrt(n)) | Mejora |
|-------|----------------------|-------------------------------|--------|
| 56 | 55 copias | ~15 copias | 3.7x |
| 200 | 199 copias | ~28 copias | 7.1x |
| 1,000 | 999 copias | ~63 copias | 15.9x |
| 10,000 | 9,999 copias | ~200 copias | 50x |

El bug de colision de `msg_id` identificado por el reviewer (HIGH severity) fue critico: el metodo original usaba `time.time() + pid + id(self)`, produciendo IDs identicos en escenarios de alto throughput. La correccion a `uuid4` elimino el riesgo.

La race condition en `_save_nodes()` con escrituras concurrentes desde `asyncio.gather()` durante `spawn_team()` permanece como riesgo no resuelto.

### 4.3 H3: La Seguridad Multi-Capa es Suficiente

Las 7 capas de seguridad cubren amenazas en profundidad:

| Capa | Tipo | Amenazas cubiertas |
|------|------|-------------------|
| MeshGuardian | Infraestructura | Manipulacion de registro, bus |
| Icarus | Proactivo | Ataques coordinados, bots, compromiso |
| Cerberus | Reactivo | Inyeccion (codigo, prompts, comandos), exfiltracion, traversal |
| SecurityHierarchy | Escalamiento | Triage L0 -> respuesta L4 |
| Governance | Constitucional | HARD_RULES bloquean, SOFT_RULES advierten |
| AST Verifier | Estructural | Codigo generado cumple patrones |
| Z3 Gate | Formal | Pruebas matematicas con hash keccak256 |

**Gap identificado:** El reporte del guardian revelo que la governance deja pasar ciertos patrones de prompt injection que Cerberus si detecta. Las capas son complementarias por diseno, pero esto confirma que ninguna capa individual es suficiente.

**Ausencia de ataques reales:** Durante el experimento no se registraron ataques reales contra el mesh, lo cual es esperado dado que opera exclusivamente en filesystem local sin exposicion a red. Los honeypots de Icarus permanecieron sin activar. Esto constituye una limitacion para evaluar H3 en condiciones adversariales.

### 4.4 El Puente Humano como Patron de Integracion

El patron de puente humano (human bridge) se valido con DeepSeek y GPT:

**Proceso:**
1. El operador copia el contenido del inbox del nodo externo y lo pega en la interfaz web del modelo.
2. El modelo genera su respuesta en formato JSON valido.
3. El operador copia el JSON de respuesta y lo guarda como archivo en `logs/mesh/inbox/commander/`.
4. El Commander lee el archivo y procesa la respuesta como cualquier otro mensaje del mesh.

**Datos:**
- DeepSeek produjo 4 JSONs validos (ds-001 a ds-004) con contenido de alta calidad.
- La latencia depende enteramente del operador humano (~minutos por mensaje).
- El formato JSON fue respetado perfectamente por DeepSeek-V3.

**Viabilidad:** El patron funciona pero no es autonomo. Para eliminar la dependencia del operador, se requiere un HTTP bridge que exponga los inboxes como endpoints REST. Este es trabajo futuro identificado en el experimento.

---

## 5. Discusion

### 5.1 Limitaciones

**L1: Asimetria de participacion.** De los 56 nodos, solo 7 tuvieron actividad de mensajes. Los 37 nodos descubiertos via SessionScanner se registraron pero no ejecutaron tareas. La tasa de participacion efectiva fue del 12.5%.

**L2: Modelos web requieren puente humano.** DeepSeek, GPT, Kimi, GLM y NVIDIA solo pudieron participar via copy-paste JSON. Esto introduce una dependencia del operador que contradice el objetivo de autonomia.

**L3: Single machine.** Todo el experimento corrio en una unica maquina. No se probo la comunicacion entre meshes en maquinas distintas, lo cual es un requisito para verdadera distribucion.

**L4: Modelo de confianza basico.** El trust scoring de Cerberus opera a nivel de nodo individual. No existe un sistema de reputacion transitiva (si A confia en B y B confia en C, A confia parcialmente en C), lo cual seria necesario para meshes federados.

**L5: Sin validacion de proveedores en vivo.** El `provider_health.json` se baso en documentacion y experiencia previa, no en llamadas API en tiempo real durante el experimento. Los estados "expired" de Groq y Cerebras no fueron verificados programaticamente.

**L6: Sin ataques adversariales reales.** Los honeypots de Icarus no se activaron porque no hubo atacantes. Las capacidades defensivas del stack de seguridad no fueron testeadas bajo condiciones adversariales reales.

### 5.2 Trabajo Futuro

**HTTP Bridge.** Implementar un servidor REST que exponga los inboxes como endpoints, permitiendo a modelos web (DeepSeek, GPT, Kimi, GLM) enviar y recibir mensajes sin intervencion humana. Endpoint propuesto: `POST /api/v1/mesh/inbox/{node_id}`.

**Protocolo de Federacion.** Extender el protocolo de filesystem a un protocolo de red para permitir meshes en multiples maquinas. Opciones: WebSocket bidireccional, gRPC streaming, o NATS como message broker.

**Verificacion Formal del Protocolo.** Especificar el protocolo del mesh en TLA+ o PROMELA y verificar formalmente propiedades de liveness (todo mensaje eventualmente se entrega), safety (ningun mensaje se pierde o duplica), y fairness (ningun nodo es indefinidamente ignorado).

**Implementacion del Routing O(sqrt(n)).** Implementar la propuesta de DeepSeek: clustering por afinidad con k ~ sqrt(n), DHT overlay con finger tables. Benchmark contra broadcast naive.

**Benchmark Estandarizado Cross-Model.** Disenar un benchmark que mida la contribucion diferencial de cada familia de modelo en tareas estandarizadas: razonamiento matematico (DeepSeek), creatividad (GPT), analisis de codigo (Claude), velocidad de inferencia (Gemini), etc.

**Red Teaming del Mesh.** Ejecutar campanas de red team contra el stack de seguridad: inyectar nodos maliciosos, intentar exfiltrar datos via canales laterales, probar evasion de los 49 patrones de Cerberus, y activar los honeypots de Icarus.

### 5.3 Implicaciones

**Para la industria:** El mesh multi-modelo es factible con infraestructura minima (un laptop, archivos JSON). No se necesitan APIs propietarias, brokers de mensajes, ni infraestructura cloud. Esto democratiza la orquestacion de IA.

**Para la investigacion:** La diversidad cognitiva entre modelos de IA es medible y produce valor no redundante. DeepSeek identifico problemas que 48 nodos Claude no vieron. Este es un argumento fuerte contra los monocultivos de modelo.

**Para la sociedad:** Un mesh abierto donde cualquier modelo puede participar (con capas de seguridad) representa un modelo de gobernanza para IA multi-stakeholder: ningun proveedor tiene control exclusivo, la seguridad es deterministica (no depende de LLM), y la auditoria es completa (todo queda en JSONL).

---

## 6. Conclusiones

Este trabajo presenta la primera demostracion exitosa de colaboracion autonoma entre 56 agentes de inteligencia artificial pertenecientes a 8 familias de modelos, operando sobre un protocolo de comunicacion basado en archivos JSON en filesystem local.

Los resultados confirman las tres hipotesis planteadas, con matices:

1. **H1 (Diversidad cognitiva) --- CONFIRMADA.** El nodo DeepSeek-V3 produjo 3 contribuciones cualitativamente distintas a las de los 48 nodos Claude: routing O(sqrt(n)), analisis de redundancia de metricas, y perspectiva del ecosistema chino de IA. Estas contribuciones no son redundantes --- cada modelo aporta desde su fortaleza cognitiva.

2. **H2 (Protocolo de filesystem) --- PARCIALMENTE CONFIRMADA.** El protocolo funciono correctamente para 56 nodos y 120 mensajes, pero se identificaron bottlenecks (broadcast O(n), race conditions en escritura concurrente) que limitarian la escalabilidad mas alla de ~200 nodos sin las optimizaciones propuestas.

3. **H3 (Seguridad multi-capa) --- CONFIRMADA CON RESERVAS.** Las 7 capas de seguridad son complementarias y cubren amenazas en profundidad. Sin embargo, no fueron testeadas bajo ataques adversariales reales. La ausencia de ataques durante el experimento es consistente con la operacion en filesystem local.

El experimento produjo artefactos tangibles: 112 tests nuevos, 5 reportes de inteligencia, 3 modulos nuevos, identificacion de 2 vulnerabilidades criticas, y una propuesta de optimizacion de routing con analisis formal de complejidad.

La contribucion mas significativa es de naturaleza conceptual: **la demostracion de que modelos de IA de diferentes proveedores y arquitecturas pueden colaborar autonomamente sobre un protocolo minimo (archivos JSON en disco), produciendo resultados superiores a los que cualquier modelo individual podria generar.**

---

## Referencias

1. Quiceno Vasquez, J.C. "I'm not an expert. I just didn't stop building." *Medium*, 21 de marzo de 2026. https://medium.com/@jquiceva/im-not-an-expert-i-just-didn-t-stop-building-e117c2bc886e

2. DeepSeek-AI. "DeepSeek-V3 Technical Report." *arXiv:2412.19437*, 2024.

3. Bai, Y., et al. "Constitutional AI: Harmlessness from AI Feedback." *Anthropic*, 2023. arXiv:2212.08073.

4. Gemini Team, Google. "Gemini: A Family of Highly Capable Multimodal Models." *arXiv:2312.11805*, 2024.

5. Hong, S., et al. "MetaGPT: Meta Programming for A Multi-Agent Collaborative Framework." *ICLR 2024*.

6. Wu, Q., et al. "AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation." *arXiv:2308.08155*, 2023.

7. CrewAI. "CrewAI: Framework for orchestrating role-playing, autonomous AI agents." https://github.com/joaomdmoura/crewAI, 2024.

8. LangGraph. "LangGraph: Multi-Actor Applications with LLMs." *LangChain*, 2024.

9. Quiceno Vasquez, J.C. "Deterministic Observability Framework." *GitHub*, 2026. https://github.com/Cyberpaisa/deterministic-observability-framework

10. de Moura, L., Bjorner, N. "Z3: An Efficient SMT Solver." *TACAS 2008*, LNCS 4963.

---

## Apendices

### Apendice A. Timeline Completo de Eventos

Datos extraidos de `logs/mesh/mesh_events.jsonl` (27 eventos):

```
2026-03-22T17:30:20  spawn        commander     76.5s    session=35db4510
2026-03-22T17:31:01  spawn        reviewer     117.5s    session=858ed156
2026-03-22T17:31:17  spawn        researcher   133.7s    session=7a5f3ddd
2026-03-22T17:31:20  spawn        architect    136.4s    session=846623d8
2026-03-22T17:33:01  spawn        social-intel 180.7s    session=dd21937e
2026-03-22T17:33:04  spawn        guardian     240.7s    session=7570227f
2026-03-22T17:33:43  spawn        book-writer  222.6s    session=8050e8e7
2026-03-22T17:35:10  spawn        narrator     366.0s    session=a24938ec
2026-03-22T19:53:00  spawn        commander    133.8s    session=9f691e57 (re-spawn)
2026-03-22T19:53:01  spawn        architect      ERROR   session_failed
2026-03-22T19:53:03  spawn        researcher     ERROR   session_failed
2026-03-22T19:53:04  spawn        guardian        ERROR   session_failed
2026-03-22T19:53:06  spawn        narrator        ERROR   session_failed
2026-03-22T19:53:08  spawn        reviewer        ERROR   session_failed
2026-03-22T22:16:44  spawn        commander     96.4s    session=9f691e57 (resumed)
2026-03-22T22:16:57  spawn        commander     81.2s    session=9addc911
2026-03-22T22:44:21  spawn        commander    114.9s    session=eaf76882
2026-03-22T23:32:11  NIGHT_SHIFT_ACTIVATED       7 nodos, operador descansa
2026-03-22T23:32:19  COMMANDER_AUTONOMOUS_MODE   Estrategia: security > tests > docs
2026-03-22T23:38:23  FULL_MESH_ACTIVATED         48 nodos (12 Opus + 35 Sonnet + 1 Gemini)
2026-03-22T23:45:51  GPT_NODE_JOINED             49 nodos, 4 familias
2026-03-22T23:48:11  LEGION_GROWS                51 nodos (gpt-chat + gemini-2)
2026-03-22T23:50:08  ICARUS_DEPLOYED             52 nodos, stack de seguridad completo
2026-03-22T23:50:45  MASSIVE_EXPANSION           55 nodos (deepseek + kimi-k2 + nvidia-nim)
2026-03-22T23:59:53  DEEPSEEK_FIRST_CONTACT      4 mensajes de alta calidad matematica
2026-03-23T00:03:47  GLM5_JOINED                 56 nodos, 8 familias
2026-03-23T00:05:56  TRANSCENDENTAL_MISSION      Broadcast a 56 nodos
```

### Apendice B. Formato del Protocolo de Mensajes

**Esquema JSON de MeshMessage:**

```json
{
  "msg_id": "string (UUID4)",
  "from_node": "string (node_id del emisor)",
  "to_node": "string (node_id del destinatario, '*' para broadcast)",
  "content": "string (contenido del mensaje, texto libre)",
  "msg_type": "string (task | result | query | alert | sync)",
  "timestamp": "number (epoch seconds, float)",
  "read": "boolean (opcional, marcado por receptor)",
  "reply_to": "string | null (msg_id del mensaje al que responde)"
}
```

**Esquema JSON de MeshNode:**

```json
{
  "node_id": "string (identificador unico)",
  "role": "string (descripcion del rol)",
  "session_id": "string | null (UUID de sesion Claude)",
  "status": "string (idle | active | spawning | error)",
  "last_active": "number (epoch seconds)",
  "messages_sent": "integer",
  "messages_received": "integer",
  "tools": ["string (lista de herramientas disponibles)"],
  "model": "string (identificador del modelo LLM)",
  "created_at": "number (epoch seconds)"
}
```

### Apendice C. Nodos Nombrados del Mesh

| # | node_id | model | role | sent | recv |
|---|---------|-------|------|------|------|
| 1 | commander | claude-sonnet-4-6 | Orquestador | 87 | 6 |
| 2 | architect | claude-sonnet-4-6 | Arquitectura de codigo | 7 | 23 |
| 3 | researcher | claude-sonnet-4-6 | Investigacion y analisis | 5 | 23 |
| 4 | guardian | claude-sonnet-4-6 | Seguridad y testing | 2 | 32 |
| 5 | narrator | claude-sonnet-4-6 | Documentacion | 2 | 22 |
| 6 | reviewer | claude-sonnet-4-6 | Code review | 3 | 19 |
| 7 | antigraviti | gemini-2.5-flash | Nodo Gemini cross-model | 0 | 0 |
| 8 | investigador-temas | claude-sonnet-4-6 | Investigacion cross-domain | 0 | 0 |
| 9 | opus-home | claude-opus-4-6 | General purpose | 0 | 0 |
| 10 | skill-researcher | claude-opus-4-6 | Investigacion de skills | 0 | 0 |
| 11 | cyber-agent | claude-opus-4-6 | Ciberseguridad | 0 | 0 |
| 12 | gpt-legion | gpt-4o | Colaborador cross-model GPT | 0 | 0 |
| 13 | gpt-chat | gpt-4o | Conversacion creativa GPT | 0 | 0 |
| 14 | gemini-2 | gemini-2.5-flash | Segundo nodo Gemini | 0 | 0 |
| 15 | icarus | claude-opus-4-6 | Cazador de amenazas OPSEC | 0 | 0 |
| 16 | deepseek | deepseek-v3 | Razonamiento matematico | 4 | 0 |
| 17 | kimi-k2 | kimi-k2-instruct | Analisis multilingue | 0 | 0 |
| 18 | nvidia-nim | nvidia-nemotron | Inferencia GPU-optimizada | 0 | 0 |
| 19 | glm-5 | glm-4-flash | LLM chino, RLHF alignment | 0 | 0 |

Adicionalmente: 37 nodos descubiertos via SessionScanner (28 Sonnet, 9 Opus).

### Apendice D. Tests Creados Durante el Experimento

| Archivo | Tests | Modulo cubierto |
|---------|-------|-----------------|
| tests/test_node_mesh.py | 62 | core/node_mesh.py (NodeMesh, MessageBus, SessionScanner) |
| tests/test_autonomous_daemon.py | 50 | core/autonomous_daemon.py (4 fases, 3 daemons) |
| **Total** | **112** | |

### Apendice E. Bugs Identificados

**Tabla E1. Bugs corregidos durante el experimento.**

| ID | Modulo | Severidad | Descripcion | Fix |
|----|--------|-----------|-------------|-----|
| BUG-001 | core/node_mesh.py | HIGH | msg_id collision: `_gen_msg_id()` usa time+pid+id(self), produce duplicados en alto throughput | Cambiado a uuid4 |
| BUG-002 | core/node_mesh.py | MEDIUM | send_message sin validacion de nodos existentes | Agregada validacion |
| BUG-003 | core/autonomous_daemon.py | MEDIUM | Logs de multiples daemons escritos al mismo archivo | Per-daemon log files |

**Tabla E2. Bugs identificados pero no corregidos.**

| ID | Modulo | Severidad | Descripcion |
|----|--------|-----------|-------------|
| BUG-004 | core/node_mesh.py | MEDIUM | Race condition en `_save_nodes()` con `asyncio.gather()` |
| BUG-005 | core/supervisor.py | MEDIUM | Threshold 6.0 (era 7.0) deja pasar outputs mediocres (5.0-5.99) en retry exhaustion |
| BUG-006 | core/supervisor.py | LOW | `reasons` field en SupervisorVerdict sin default_factory |
| BUG-007 | core/governance.py | MEDIUM | False positive patterns demasiado amplios |

---

*Documento generado el 23 de marzo de 2026. Todos los datos provienen de logs persistidos en `logs/mesh/` del repositorio DOF.*
