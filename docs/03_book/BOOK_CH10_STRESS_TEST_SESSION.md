# Capítulo 10: La Sala de Control — Primera Prueba de Estrés Real del DOF Mesh

*Cuando 18 tareas golpean 6 nodos simultáneamente y el sistema te dice la verdad sobre sí mismo.*

*March 24, 2026 — DOF v0.6.1*

---

## 1. El Escenario

Hasta la noche del 23 de marzo, el DOF Mesh era una arquitectura prometedora: 52+ módulos, 3000+ tests, nodos que intercambian JSON por el filesystem, daemons que se auto-inician con LaunchAgent. Todo funcionaba en pruebas unitarias, en tests de integración, en runs manuales con una sola tarea a la vez.

Pero un sistema distribuido no existe hasta que lo rompes.

La prueba de estrés real comenzó con una premisa simple: enviar 18 tareas simultáneas a 6 nodos del mesh, cada nodo con su propio modelo Ollama especializado, y medir qué pasa. No simular carga — aplicarla de verdad, con modelos reales corriendo en el M4 Max, con el daemon activo leyendo inbox dirs cada 3 segundos, con Telegram reportando resultados en tiempo real.

Lo que descubrimos cambió nuestra comprensión del sistema.

---

## 2. Lo que Construimos Esta Sesión

Antes de la prueba, la sesión del 24 de marzo estuvo dedicada a completar la infraestructura de ejecución local. Estos son los módulos que entraron en producción:

### 2.1 `core/autonomous_executor.py` — El Motor de Herramientas

El executor es el corazón de la ejecución agentic local. Opera en un loop de hasta 10 iteraciones, donde cada iteración puede usar una de 5 herramientas disponibles:

```python
TOOLS = {
    "bash":       ejecuta comandos shell con timeout configurable,
    "python":     evalúa código Python en un namespace aislado,
    "read_file":  lee archivos del filesystem con límite de líneas,
    "write_file": escribe archivos con validación de path,
    "list_dir":   lista directorios con filtros de extensión
}
```

Dos decisiones de diseño críticas:

**Think-tag stripping:** DeepSeek y algunos modelos Qwen emiten bloques `<think>...</think>` con razonamiento interno antes del output final. El executor los elimina antes de parsear JSON, lo cual fue esencial para que los modelos locales pudieran usarse sin modificación:

```python
def strip_think_tags(text: str) -> str:
    """Remove <think>...</think> blocks from model output."""
    import re
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
```

**BLOCKED_PATTERNS para seguridad:** El executor rechaza comandos que coincidan con patrones peligrosos antes de ejecutarlos — `rm -rf`, `sudo`, operaciones de red no autorizadas, acceso a credenciales. Esto no es gobernanza Z3 completa, pero es la primera línea de defensa en ejecución local.

### 2.2 `core/local_orchestrator.py` — Routing Multi-Modelo

El orchestrator selecciona automáticamente el modelo Ollama correcto según el tipo de tarea:

```
Tipo de tarea     → Modelo seleccionado
─────────────────────────────────────────
"code" / "debug"  → dof-coder (Qwen2.5-Coder 14.8B)
"security" / "audit" → dof-guardian (Qwen2.5-Coder 14.8B + system prompt seguridad)
"analysis" / "data"  → dof-analyst (Qwen2.5-Coder 14.8B + system prompt análisis)
"reasoning" / "plan" → dof-reasoner (Qwen2.5-Coder 14.8B + chain-of-thought)
"general"            → local-agi-m4max (Qwen2.5-Coder 14.8B + prompt generalista)
```

El routing es determinístico — keywords en el campo `type` de la tarea JSON determinan el nodo destino. Sin LLM clasificador, sin probabilidades: coincidencia de strings exacta.

### 2.3 `scripts/run_mesh_agent.py` — El Daemon del Mesh

Este script es el proceso que mantiene vivo el mesh. Opera en un loop infinito:

```
Cada 3 segundos:
  Para cada nodo en [dof-coder, dof-reasoner, dof-guardian,
                      dof-analyst, local-agi-m4max, local-agent]:
    1. Escanea logs/mesh/inbox/{nodo}/*.json
    2. Si hay tareas pendientes (sin extensión .processing ni .done):
       a. Renombra task.json → task.json.processing
       b. Carga el modelo Ollama del nodo
       c. Ejecuta autonomous_executor con la tarea
       d. Escribe resultado en logs/mesh/outbox/{nodo}/
       e. Renombra task.json.processing → task.json.done
    3. Reporta status por Telegram si hay cambios
```

El protocolo de archivos (.processing → .done) actúa como lock distribuido. Si el daemon muere a mitad de una tarea, el archivo queda en estado `.processing` — señal clara de que necesita atención manual. No hay mensajes perdidos en silencio.

### 2.4 LaunchAgent — Auto-Start en Login

```xml
<!-- ~/Library/LaunchAgents/com.dof.mesh-agent.plist -->
<key>RunAtLoad</key><true/>
<key>KeepAlive</key><true/>
<key>ProgramArguments</key>
<array>
  <string>/Users/jquiceva/.nvm/versions/node/v20.x.x/bin/python3</string>
  <string>/Users/jquiceva/equipo-de-agentes/scripts/run_mesh_agent.py</string>
</array>
```

Lección aprendida de la experiencia con OpenClaw: el plist DEBE usar la ruta absoluta del Python de nvm, no `/usr/local/bin/python3`. En macOS Tahoe, el PATH del LaunchAgent no hereda el PATH del usuario — si el ejecutable no existe en la ruta exacta, el servicio falla silenciosamente.

### 2.5 Modelfiles — Los 6 Nodos Especializados

Creamos Modelfiles para cada nodo del mesh, cada uno con un system prompt diferente que orienta el comportamiento del modelo base (Qwen2.5-Coder 14.8B):

```dockerfile
# Ejemplo: dof-coder
FROM qwen2.5-coder:14b
SYSTEM """
Eres dof-coder, un agente especializado en escritura y análisis de código Python.
Tu objetivo: producir código correcto, documentado y con manejo de errores.
Cuando uses herramientas, responde SOLO con JSON válido.
Formato: {"tool": "nombre", "args": {...}} o {"result": "respuesta final"}
"""
PARAMETER temperature 0.1
PARAMETER top_p 0.9
```

La temperatura baja (0.1) es crítica para tool use — necesitamos JSON parseable, no creatividad.

### 2.6 APIs de Mission Control

Tres endpoints nuevos en el frontend Next.js para integrar el mesh con la interfaz web:

| Endpoint | Función |
|---|---|
| `api/local/ollama` | SSE streaming con think-tag stripping cross-chunk |
| `api/local/mesh` | Envía tareas al mesh via filesystem |
| `api/local/upload` | Upload con extracción server-side (pdfplumber + pandas) |
| `api/system/control` | Control de procesos del sistema |

El streaming SSE con think-tag stripping cross-chunk merece atención especial: los tags `<think>` pueden llegar partidos entre chunks. El handler mantiene un buffer acumulativo y solo emite al cliente el contenido fuera de los tags de thinking:

```typescript
// Pseudocódigo del handler SSE
let buffer = '';
let inThink = false;

for await (const chunk of ollamaStream) {
  buffer += chunk.response;

  // Detectar apertura/cierre de think tags cruzando chunks
  if (buffer.includes('<think>')) inThink = true;
  if (buffer.includes('</think>')) {
    inThink = false;
    buffer = buffer.replace(/<think>[\s\S]*?<\/think>/g, '');
  }

  if (!inThink) {
    const clean = extractClean(buffer);
    if (clean) emit(clean);
  }
}
```

---

## 3. La Prueba de Estrés

### 3.1 Configuración del Experimento

Con la infraestructura completa, lanzamos la prueba: **18 tareas simultáneas a 6 nodos del mesh**.

El setup:

```
Hardware:    MacBook Pro M4 Max, 36GB RAM, Ollama 0.6.x
Modelos:     Qwen2.5-Coder 14.8B (base de todos los nodos)
Instancias:  1 proceso Ollama, 6 Modelfiles, 2 instancias del daemon
Timeout:     180s inicial (luego ajustado a 600s)
Tareas:      3 por nodo, JSON en logs/mesh/inbox/{nodo}/
```

Las 18 tareas cubrían operaciones reales del sistema:

```
dof-coder:      analizar autonomous_executor.py, generar docstrings, revisar imports
dof-reasoner:   planificar arquitectura de scaling, razonar sobre trade-offs
dof-guardian:   auditar patrones de seguridad, revisar BLOCKED_PATTERNS
dof-analyst:    analizar métricas de tests, reportar cobertura
local-agi-m4max: resumir estado del sistema, generar informe
local-agent:    verificar health del mesh, reportar anomalías
```

### 3.2 Flujo de Datos del Mesh

```
┌─────────────────────────────────────────────────────────────────┐
│                    DOF MESH — STRESS TEST                        │
│                    18 tareas / 6 nodos                           │
└─────────────────────────────────────────────────────────────────┘

  Telegram / CLI / Mission Control
          │
          │  POST tarea (JSON)
          ▼
  ┌──────────────────┐
  │  local_orchestrator │  ← Routing por tipo de tarea
  │  (determinístico)   │
  └──────────┬───────┘
             │
    Escribe en filesystem
             │
    ┌────────┴────────────────────────────────────────────┐
    │                                                     │
    ▼            ▼            ▼            ▼              ▼
logs/mesh/   logs/mesh/   logs/mesh/   logs/mesh/   logs/mesh/
inbox/       inbox/       inbox/       inbox/       inbox/
dof-coder/   dof-reasoner/ dof-guardian/ dof-analyst/ local-agent/
task1.json   task1.json   task1.json   task1.json   task1.json
task2.json   task2.json   task2.json   task2.json   task2.json
task3.json   task3.json   task3.json   task3.json   task3.json
    │            │            │            │              │
    └─────────────────────────┼────────────────────────────┘
                              │
                    run_mesh_agent.py
                    (scan cada 3s)
                              │
                    ┌─────────┴──────────┐
                    │                    │
              .processing           Ollama API
                (lock)               (serial)
                    │                    │
                    │       ┌────────────┴──────────┐
                    │       │    UN solo proceso     │
                    │       │    Qwen2.5-Coder 14B   │
                    │       │    serializa todo      │
                    │       └────────────┬──────────┘
                    │                    │
                    └─────────┬──────────┘
                              │
                    ┌─────────┴──────────┐
                    │  autonomous_executor│
                    │  max 10 iteraciones │
                    │  5 herramientas     │
                    └─────────┬──────────┘
                              │
                    ┌─────────┴──────────┐
                    │  logs/mesh/outbox/  │
                    │  task1.json.done    │  ← resultado
                    └─────────────────────┘
                              │
                    Telegram notification
```

### 3.3 Resultados

| Nodo | Tareas | OK | Timeout | Tiempo prom |
|------|--------|----|---------|----|
| dof-analyst | 3 | 1 | 2 | 210s |
| local-agi-m4max | 3 | 2 | 1 | 218s |
| dof-guardian | 3 | 1 | 2 | 237s |
| dof-coder | 3 | 1 | 2 | 253s |
| local-agent | 3 | 1 | 2 | 248s |
| dof-reasoner | 3 | 0 | 3 | 280s |
| **TOTAL** | **18** | **6 (33%)** | **12 (67%)** | **241s** |

**33% de éxito.** A primera vista, un resultado malo. Pero la interpretación correcta es diferente.

### 3.4 Análisis de Causa Raíz

El diagnóstico tomó menos de 10 minutos una vez que entendimos el problema:

**Hipótesis inicial (incorrecta):** Los modelos están fallando al procesar las tareas.

**Evidencia:** La tarea exitosa más notable refutó esta hipótesis. dof-coder leyó `autonomous_executor.py` y `local_orchestrator.py` completos en 2 iteraciones de herramientas, y en 103 segundos generó docstrings profesionales para ambos archivos. Tool use funcionando perfectamente, output de calidad.

**Causa raíz real:** Los timeouts no ocurrían durante la ejecución. Ocurrían mientras las tareas esperaban en la cola.

```
Línea de tiempo de una tarea que timeout:

t=0s    Tarea entra en inbox/dof-coder/
t=1s    Daemon la detecta, la marca .processing
t=2s    Daemon envía a Ollama... pero Ollama está ocupado
t=150s  Ollama termina tarea anterior, comienza esta
t=180s  ⚡ TIMEOUT del executor (configurado en 180s)
        La tarea tuvo solo 30s de ejecución real
        → marcada como fallida
```

Ollama con un solo proceso procesa requests serialmente. 18 requests simultáneas significa una cola de espera. El timeout de 180s, razonable para una sola tarea, era insuficiente cuando incluía el tiempo de espera en cola.

**Fix aplicado:** timeout 180s → 600s en el executor. Con este cambio, las mismas 18 tareas habrían tenido suficiente tiempo de ejecución real incluso esperando en cola.

### 3.5 Comportamiento del Hardware

```
Estado RAM durante la prueba:
─────────────────────────────────────────────────────────────
          Inicio    Pico     Fin
RAM usada: 22GB   → 34GB  → 28GB    (de 36GB disponibles)
─────────────────────────────────────────────────────────────
          ▲                ▲
    baseline         ¡Límite real!
    2 instancias     Solo 2GB de margen
    daemon +         antes de swap
    servicios
```

La RAM fue el segundo cuello de botella. Qwen2.5-Coder 14.8B en Q4 ocupa ~9GB de RAM para el modelo base, más el contexto de cada request activa. Con 6 nodos potencialmente ejecutando en paralelo (en teoría), el pico de 34GB de 36GB disponibles no dejaba margen.

En la práctica, Ollama serializa todo — solo había un proceso de inferencia activo a la vez — pero el daemon, Mission Control, Telegram y otros servicios del sistema consumían los 13GB restantes.

**CPU:** No fue el cuello de botella en ningún momento. El M4 Max tiene 16 cores de CPU disponibles, y la inferencia de LLMs está bound en GPU/ANE.

**GPU/ANE:** La serialización de Ollama significa que las 40 cores GPU del M4 Max estaban siendo utilizadas secuencialmente por una sola request a la vez. Para paralelismo real, necesitaríamos múltiples instancias de Ollama en diferentes puertos.

---

## 4. El Bug del Telegram 409

Mientras la prueba de estrés corría, un problema separado pero igualmente instructivo emergió en la interfaz de Telegram.

### 4.1 El Síntoma

```
Error 409 Conflict: terminated by other getUpdates request
```

Apareciendo continuamente, impidiendo que el bot recibiera mensajes. El sistema estaba operacionalmente ciego — podíamos enviar tareas al mesh, pero no recibir confirmaciones.

### 4.2 Diagnóstico

La primera herramienta fue `ps aux`:

```bash
$ ps aux | grep telegram_bot
jquiceva  12847  0.0  0.1  python3 interfaces/telegram_bot.py  # instancia 1
jquiceva  13291  0.0  0.1  python3 interfaces/telegram_bot.py  # instancia 2
jquiceva  14103  0.0  0.1  python3 interfaces/telegram_bot.py  # instancia 3 (!!)
```

Tres instancias del bot corriendo simultáneamente. Cada una intentando hacer `getUpdates` — el mecanismo de long-polling de Telegram. El servidor de Telegram permite solo una sesión activa por bot token, y cuando detecta una segunda, mata la primera con 409.

**Fuente de las instancias:**
- Instancia 1: iniciada manualmente días antes, todavía corriendo en background
- Instancia 2: iniciada por un agente background de Claude (task b0n6utxjz) que el usuario inició para monitorear la prueba
- Instancia 3: iniciada por el proceso principal intentando resolver el 409

**El problema estructural:** `long_polling_timeout=60` en telebot significa que cuando un proceso muere, Telegram mantiene su sesión activa por 60 segundos. Durante esos 60 segundos, cualquier nuevo intento de iniciar el bot recibe 409. Si el nuevo intento también muere (por el 409), e intentamos de nuevo, entramos en un ciclo de fallos.

**Lo que NO funciona:** Hacer `getUpdates?timeout=0` para "cancelar" la sesión existente. Telegram ignora este intento cuando hay una sesión long-polling activa en el servidor.

### 4.3 El Fix

```bash
# Paso 1: matar todas las instancias
kill -9 12847 13291 14103

# Paso 2: verificar que no queda ninguna
ps aux | grep telegram_bot  # debe estar vacío

# Paso 3: esperar el tiempo completo de expiración
sleep 65  # long_polling_timeout(60) + margen(5)

# Paso 4: iniciar UNA sola instancia
python3 interfaces/telegram_bot.py &

# Verificar
curl -s "https://api.telegram.org/bot$TOKEN/getMe" | jq .ok
# → true ✅
```

La cadena de fallback del bot, una vez funcionando correctamente:

```
ANTHROPIC_API_KEY (no configurada)
      │
      ▼ fallback
GROQ_API_KEY (expirada — 401 Unauthorized)
      │
      ▼ fallback
CEREBRAS_API_KEY (válida — 200 OK) ✅ Activa
      │
      ▼ fallback (si Cerebras falla)
Ollama local → local-agi-m4max ($0, siempre disponible)
```

Esta cadena es exactamente el patrón de resiliencia que diseñamos: nunca un punto único de falla, siempre una opción de $0 disponible localmente.

### 4.4 Lección Organizacional

El bug de Telegram reveló un problema de coordinación entre agentes. Cuando múltiples agentes Claude trabajan en paralelo (el agente principal + agentes background iniciados por el usuario), pueden competir por los mismos recursos con estado — en este caso, la conexión Telegram.

La solución no es técnica únicamente — es organizacional: **un solo agente a cargo de cada servicio con estado**. Si el servicio Telegram necesita management, solo el agente designado para Telegram puede iniciarlo o reiniciarlo. Los demás agentes pueden leer el estado del servicio, pero no pueden iniciarlo.

Este principio — ownership exclusivo de recursos con estado — es fundamental para sistemas multi-agente que comparten infraestructura.

---

## 5. Lecciones Técnicas

### Lección 1: Timeout Wall-Clock vs Timeout de Ejecución

El timeout del executor debe empezar cuando Ollama comienza a responder, no cuando la tarea entra en la cola.

```python
# ANTES (incorrecto para carga alta):
async def execute(task, timeout=180):
    start = time.time()
    result = await ollama.generate(...)  # puede esperar 150s en cola
    # Solo quedan 30s para la ejecución real

# DESPUÉS (correcto):
async def execute(task, queue_timeout=300, exec_timeout=180):
    # Esperar en cola hasta queue_timeout
    response = await asyncio.wait_for(
        ollama.generate(...),
        timeout=queue_timeout
    )
    # Una vez que Ollama empieza, dar exec_timeout completo
    ...
```

Con carga alta, el tiempo de espera en cola puede superar el timeout configurado. El resultado es tareas que "fallan" sin nunca haber sido ejecutadas — lo más frustrante de debuggear porque los logs muestran timeout pero no hay evidencia de ejecución.

### Lección 2: Ollama es Serial por Diseño

Un proceso Ollama en M4 Max procesa una request a la vez. Esto es una decisión de diseño consciente de Ollama — maximizar el uso de GPU para cada request individual.

Para paralelismo real existen tres opciones:

```
Opción A: Múltiples instancias Ollama en diferentes puertos
─────────────────────────────────────────────────────────────
ollama serve --port 11434  # instancia 1 → dof-coder
ollama serve --port 11435  # instancia 2 → dof-guardian
...
Costo: más RAM (cada instancia carga el modelo separado)
Ganancia: verdadero paralelismo hardware

Opción B: APIs externas para carga paralela
─────────────────────────────────────────────────────────────
Cerebras: 868 tok/s, 60 req/min en tier gratuito
Groq:     variable, muy rápido para modelos pequeños
Costo: dependencia externa, posible expiración de keys
Ganancia: 5-10x más rápido que local para tareas cortas

Opción C: Modelos más pequeños + paralelismo
─────────────────────────────────────────────────────────────
Phi-4 14B (9GB, 120 tok/s ANE) → mayor throughput
Llama 3.3 8B (5GB, 230 tok/s) → máximo throughput local
Costo: menor calidad de razonamiento
Ganancia: 2-4 tareas en paralelo con los 36GB disponibles
```

Para el DOF Mesh en M4 Max, la estrategia óptima a corto plazo es Opción C: modelos más pequeños para tareas de routing/clasificación, reservando Qwen2.5-Coder 14.8B para tareas que requieren calidad alta.

### Lección 3: Race Conditions en Recursos con Estado

El servidor de Telegram mantiene estado por sesión de bot. Este estado tiene latencia de limpieza (60-65 segundos para long-polling). Cualquier sistema que pueda tener múltiples iniciadores compitiendo debe gestionar esto explícitamente.

El patrón correcto es un PID file con lock:

```python
import fcntl, os, sys

PID_FILE = "/tmp/dof-telegram-bot.pid"

def acquire_lock():
    """Adquiere lock exclusivo o termina si ya existe una instancia."""
    try:
        fp = open(PID_FILE, 'w')
        fcntl.flock(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fp.write(str(os.getpid()))
        fp.flush()
        return fp
    except IOError:
        print(f"Bot ya corriendo (PID file: {PID_FILE})")
        sys.exit(1)

lock = acquire_lock()
# ... iniciar bot normalmente
```

Con este patrón, la segunda instancia falla inmediatamente en lugar de crear un conflicto de 65 segundos en Telegram.

### Lección 4: El Protocolo de Archivos es Arquitectura Sólida

Después de la prueba, podemos confirmar: el protocolo JSON inbox → .processing → .done funcionó correctamente en todos los casos. Los 18 archivos de tarea se manejaron sin corrupción, sin condiciones de carrera en el filesystem, sin mensajes perdidos.

La única causa de fallo fue la capa de recursos (RAM/GPU) por encima del protocolo. El protocolo mismo es robusto.

Esto valida la decisión de diseño: usar el filesystem como bus de mensajes en lugar de Redis, RabbitMQ, o cualquier otro sistema de mensajería. En un M4 Max con SSD NVMe, las operaciones de filesystem son extremadamente rápidas. Y más importante: son debuggeables — puedes hacer `ls logs/mesh/inbox/` y ver exactamente el estado del sistema en cualquier momento.

### Lección 5: La Tarea Exitosa es el Dato Más Importante

En una prueba de estrés con 33% de éxito, es tentador enfocarse en el 67% de fallos. Pero la tarea exitosa de dof-coder es el resultado más revelador:

```
Tarea:    "Lee autonomous_executor.py y local_orchestrator.py,
           genera docstrings profesionales para todas las funciones"

Iteración 1: tool=read_file, args={path: "core/autonomous_executor.py"}
             → 847 líneas leídas correctamente

Iteración 2: tool=read_file, args={path: "core/local_orchestrator.py"}
             → 312 líneas leídas correctamente

Iteración 3: tool=write_file, args={path: "core/autonomous_executor.py",
             content: "...archivo completo con docstrings..."}
             → archivo escrito con docstrings Google-style en cada función

Tiempo total: 103 segundos
Iteraciones: 3 de 10 máximo
Calidad: docstrings profesionales con Args:, Returns:, Raises:
```

El agente local, corriendo en Qwen2.5-Coder 14.8B en Ollama, ejecutó una tarea de ingeniería real con múltiples pasos de herramientas, sin errores de parsing JSON, sin alucinaciones de paths, con output de calidad publicable. El sistema funciona. Los timeouts eran un problema de configuración, no de capacidad.

---

## 6. Números DOF v0.6.1

Al cierre de la sesión del 24 de marzo, el local-agent confirmó en vivo el estado del sistema:

| Métrica | Valor |
|---|---|
| Módulos en core/ | **105** |
| Tests totales | **3389** |
| Tests pasando | **3384 (99.85%)** |
| Tests fallando | 5 |
| Modelos Ollama custom | **6** (dof-coder, dof-reasoner, dof-guardian, dof-analyst, local-agi-m4max, moondream) |
| Modelos base disponibles | 2 (qwen2.5-coder:14b, moondream) |
| Streaming SSE activo | Si — con think-tag stripping |
| File upload sin límite | Si — PDF, Excel, imágenes, código |
| Daemon auto-start | Si — LaunchAgent (RunAtLoad + KeepAlive) |
| Timeout configurado | 600s (actualizado desde 180s) |

El número de módulos — 105 — merece un momento de pausa. Empezamos DOF con 25 módulos en v0.2.0. Cuatro semanas después, somos 105. No por growth sintético, sino porque cada capítulo de este libro generó módulos reales que el sistema necesitaba.

---

## 7. Arquitectura Completa del Stack Local

Después de esta sesión, el stack de inferencia local del DOF se ve así:

```
┌─────────────────────────────────────────────────────────────┐
│                    INTERFACES                                │
│  Telegram Bot  │  Mission Control  │  CLI  │  API REST       │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                    ROUTING LAYER                              │
│              local_orchestrator.py                           │
│         Deterministic keyword routing                        │
│    code→coder  security→guardian  data→analyst  ...          │
└───────────────────────────┬─────────────────────────────────┘
                            │
          ┌─────────────────▼──────────────────┐
          │         FILESYSTEM BUS             │
          │  logs/mesh/inbox/{nodo}/*.json     │
          │  Protocolo: .json → .processing    │
          │             .processing → .done    │
          └─────────────────┬──────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                    DAEMON LAYER                              │
│              run_mesh_agent.py (scan 3s)                     │
│         LaunchAgent: auto-start + KeepAlive                  │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                   EXECUTOR LAYER                             │
│              autonomous_executor.py                          │
│   Tools: bash | python | read_file | write_file | list_dir  │
│   Max 10 iteraciones | BLOCKED_PATTERNS | think-tag strip    │
│   Timeout: 600s (wall-clock desde inicio de Ollama)         │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                   INFERENCE LAYER                            │
│              Ollama 0.6.x (serial, single GPU)               │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  dof-coder   │  │ dof-guardian │  │ dof-analyst  │      │
│  │ Qwen2.5-14B  │  │ Qwen2.5-14B  │  │ Qwen2.5-14B  │      │
│  │  temp=0.1   │  │  temp=0.1   │  │  temp=0.1   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ dof-reasoner │  │local-agi-m4mx│  │  moondream   │      │
│  │ Qwen2.5-14B  │  │ Qwen2.5-14B  │  │  vision 1.8B │      │
│  │  temp=0.3   │  │  temp=0.2   │  │  multimodal  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                             │
│              RAM: ~9GB por modelo activo                    │
│              GPU: 40-core, una request a la vez             │
└─────────────────────────────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                   HARDWARE BASE                              │
│         Apple M4 Max — 36GB RAM unificada                    │
│         16-core CPU | 40-core GPU | 16-core ANE             │
│         19 TFLOPS FP16 @ 2.8W | SSD NVMe 432GB libre        │
└─────────────────────────────────────────────────────────────┘
```

---

## 8. Lo que Viene Después

La prueba de estrés reveló el camino claro hacia DOF v0.7.0:

### 8.1 Paralelismo Real en Ollama

El cambio más impactante: múltiples instancias de Ollama en diferentes puertos, cada nodo con su propio proceso de inferencia. Con modelos de 8B (5GB) en lugar de 14B, podríamos correr 4 instancias simultáneas dentro de los 36GB:

```
Puerto 11434: local-coder (Llama 3.3 8B) → 5GB
Puerto 11435: local-guardian (Phi-4 14B) → 9GB
Puerto 11436: local-analyst (Qwen2.5 7B) → 4GB
Puerto 11437: local-reasoner (Qwen3 8B) → 5GB
─────────────────────────────────────────────────
Total modelo: 23GB + 13GB sistema = 36GB ✅
Paralelismo real: 4 tareas simultáneas
```

### 8.2 Timeout Adaptativo

En lugar de un timeout fijo, el executor debería estimar el tiempo de espera en cola antes de comenzar:

```python
async def adaptive_timeout(task, base_timeout=180):
    queue_depth = await ollama.get_queue_depth()
    avg_exec_time = metrics.get_avg_exec_time()
    estimated_wait = queue_depth * avg_exec_time
    total_timeout = estimated_wait + base_timeout
    return min(total_timeout, 3600)  # máximo 1 hora
```

### 8.3 Governance en el Executor

El autonomous_executor actualmente tiene BLOCKED_PATTERNS como única capa de seguridad. El siguiente paso es integrar el DOF Governance Pipeline completo — pre-check + Z3 + post-check — antes y después de cada herramienta ejecutada:

```python
# Cada tool use pasa por governance
async def safe_tool_use(tool_name, args, governance):
    pre_result = await governance.pre_check(tool_name, args)
    if not pre_result.passed:
        return {"error": pre_result.violations}

    result = await execute_tool(tool_name, args)

    post_result = await governance.post_check(tool_name, args, result)
    return {"result": result, "governance": post_result}
```

### 8.4 Mesh Federation

Con el local mesh funcionando, el siguiente nivel es federación: múltiples instancias del mesh en diferentes máquinas (o diferentes usuarios) que pueden intercambiar tareas. El protocolo de archivos JSON se extiende naturalmente a HTTP — el mismo JSON que escribimos en inbox/ puede enviarse via POST a un endpoint remoto.

Esto conecta con el trabajo de `BOOK_CH14_FEDERATION.md` y `BOOK_CH15_INTERNET_FEDERATION.md` — el diseño ya existe, ahora tenemos la infraestructura local que lo justifica.

### 8.5 El Objetivo: 18/18

La meta para la próxima prueba de estrés es 18/18 tareas completadas. No como objetivo de calidad — sino como línea base de confiabilidad. Un sistema de producción necesita completar el 100% de las tareas que acepta, o rechazarlas explícitamente antes de comenzar.

El path está claro:

```
Hoy (v0.6.1):   6/18 (33%) — timeout wall-clock mal configurado
v0.6.2:         16/18 (89%) — timeout 600s + fix de queue wait
v0.7.0:         18/18 (100%) — paralelismo real + adaptive timeout
```

---

## Cierre

Esta sesión fue la más honesta del proyecto. No construimos features impresionantes — construimos la infraestructura necesaria y luego le aplicamos carga real hasta que reveló sus limitaciones. Cada timeout fue una lección. Cada fallo fue datos.

El 33% de éxito en la primera prueba no es un fracaso — es la calibración inicial de un sistema complejo. Los sistemas distribuidos no se diseñan correctamente a la primera. Se construyen, se rompen, se entienden, y se mejoran.

Lo que sí es cierto después de esta sesión: el protocolo de archivos JSON es correcto, el autonomous_executor puede ejecutar herramientas reales con calidad de producción, y el M4 Max tiene suficiente capacidad para correr un mesh local completo.

El DOF Mesh existe. Ahora toca escalarlo.

---

## Apéndice A — Comandos de Diagnóstico del Mesh

```bash
# Estado del daemon
launchctl list | grep com.dof.mesh-agent

# Tareas en cola
ls logs/mesh/inbox/*/

# Tareas procesando ahora
find logs/mesh/inbox/ -name "*.processing"

# Tareas completadas (últimas 10)
find logs/mesh/outbox/ -name "*.done" | tail -10

# Logs del daemon
tail -f logs/mesh/mesh_agent.log

# Estado de Ollama
curl -s http://localhost:11434/api/ps | python3 -m json.tool

# Modelos disponibles
ollama list

# RAM disponible
vm_stat | grep "Pages free"

# Procesos Telegram (verificar single instance)
ps aux | grep telegram_bot | grep -v grep
```

## Apéndice B — Estructura de una Tarea Mesh

```json
{
  "task_id": "stress-test-001",
  "node": "dof-coder",
  "type": "code",
  "priority": "normal",
  "payload": {
    "instruction": "Lee core/autonomous_executor.py y genera docstrings Google-style para cada función pública.",
    "context": "Módulo nuevo — sin documentación existente",
    "expected_output": "Archivo Python con docstrings completos"
  },
  "metadata": {
    "created_at": "2026-03-24T02:15:00Z",
    "timeout": 600,
    "max_iterations": 10
  }
}
```

## Apéndice C — Checklist Pre-Stress-Test

Antes de la próxima prueba de estrés, verificar:

- [ ] Un solo proceso Ollama corriendo (`ps aux | grep ollama`)
- [ ] RAM disponible > 15GB (`vm_stat | grep free`)
- [ ] Timeout configurado en 600s o superior
- [ ] Un solo proceso telegram_bot corriendo
- [ ] LaunchAgent activo (`launchctl list | grep dof`)
- [ ] Carpetas inbox/ vacías (no hay tareas pendientes de sesión anterior)
- [ ] Modelos Ollama cargados y respondiendo (`curl http://localhost:11434/api/tags`)
- [ ] Logs con espacio en disco (`df -h /Users/jquiceva`)

---

## Capítulo 11 Preview — Fase Siguiente: Multi-Provider + Smart Scheduler

*De 33% a 85%+ sin cambiar hardware: la arquitectura que convierte cuellos de botella en resiliencia.*

---

### 11.1 Diagnóstico Final del Stress Test — Las 3 Causas Raíz

El 33% de éxito en el stress test no fue aleatorio. Fue determinístico. Una vez que entendimos el sistema real, los tres puntos de falla eran inevitables con la configuración original.

**Causa Raíz 1: Ollama Serial — El Cuello de Botella Fundamental**

Ollama por diseño procesa una request a la vez. No es un bug — es una decisión arquitectónica: maximizar el uso de GPU/ANE por inferencia individual. El problema no es Ollama; el problema es haber asumido que 6 nodos "paralelos" traducen a 6 inferencias simultáneas.

```
Realidad del sistema durante el stress test:

t=0s    18 tareas entran en las colas de los 6 nodos
        ↓
t=1s    Daemon detecta tarea en inbox/dof-coder/task1.json
        Llama a Ollama API → Ollama acepta la request
        Daemon detecta tarea en inbox/dof-coder/task2.json
        Llama a Ollama API → Ollama ENCOLA internamente
        (repite para las 16 tareas restantes)
        ↓
Ollama internamente:
  [task1] → ejecutando (103s)
  [task2] → en cola, esperando
  [task3] → en cola, esperando
  ...
  [task18] → en cola, esperando 17 * 100s = 1700s estimados
```

Con 18 tareas y un tiempo promedio de ejecución de ~103s por tarea exitosa, la última tarea en la cola necesitaría ~1700 segundos para tener su turno. Ante un timeout de 180s, el resultado era matemáticamente inevitable.

**Causa Raíz 2: Timeout Fijo de 180s — Sin Awareness de Cola**

El timeout de 180s fue diseñado para una sola tarea. Es razonable: 3 minutos es más que suficiente para que un LLM local ejecute 10 iteraciones de herramientas en una tarea bien definida.

El problema es que ese timeout se contaba desde que la tarea entraba al executor — no desde que Ollama comenzaba a procesarla. El tiempo de espera en cola no estaba separado del tiempo de ejecución real.

```
Anatomía de un timeout "injusto":

t=0s    Task entra en executor
t=0s    Executor llama Ollama → Ollama ocupado, encola
t=0s    ...
t=150s  Ollama termina tarea anterior
t=150s  Ollama comienza a procesar esta tarea
t=180s  ⚡ TIMEOUT del executor
        → 30 segundos de ejecución real antes del corte
        → Tarea marcada como FALLIDA
        → En los logs: "timeout after 180s"
        → En la realidad: ejecutó 30s, no 180s
```

La tarea no falló. Fue matada antes de poder completarse. La diferencia es importante: un fallo real requiere depurar la lógica; un timeout prematuro solo requiere ajustar la configuración.

**Causa Raíz 3: Sin Priorización — Todas las Tareas Iguales**

Con 18 tareas en cola y capacidad efectiva de 1, el orden de ejecución era FIFO (first-in, first-out) por orden de detección del daemon en su scan de 3 segundos. No había distinción entre:

- Una tarea de 15 segundos (listar archivos, verificar health)
- Una tarea de 180 segundos (leer 1000 líneas, analizar, generar output)

Una tarea corta atrapada detrás de tres tareas largas espera innecesariamente. Si el daemon hubiera priorizado por `estimated_duration` o por `priority` field del JSON, algunas tareas habrían completado antes de que llegara su timeout.

```
FIFO (situación original):
  Cola: [larga(180s)] → [larga(180s)] → [corta(15s)] → [larga(180s)]
  Resultado: corta espera 360s antes de ejecutar → timeout probable

Priority Queue (situación mejorada):
  Cola: [corta(15s)] → [larga(180s)] → [larga(180s)] → [larga(180s)]
  Resultado: corta ejecuta en 15s → éxito garantizado
```

---

### 11.2 Arquitectura Multi-Provider — La Cadena de Fallback

La solución al cuello de botella de Ollama no era solo aumentar el timeout. Era añadir fuentes alternativas de inferencia que el sistema pudiera usar cuando Ollama está ocupado o cuando necesitamos velocidad.

La cadena de fallback implementada opera por prioridad decreciente de velocidad y costo $0:

```
┌─────────────────────────────────────────────────────────────────────┐
│              CADENA DE PROVIDERS — DOF MESH v0.7.x                  │
│                                                                     │
│  Prioridad 1: Ollama Local                                          │
│  ──────────────────────────                                         │
│  Puerto: 11434 (default)                                            │
│  Modelo: qwen2.5-coder:14b / phi4 / llama3.3                       │
│  Velocidad: ~40-60 tok/s (Q4, GPU offload)                         │
│  Costo: $0.000 por token                                            │
│  Disponibilidad: 99% (solo falla si proceso muere)                 │
│  Cuándo usar: tareas largas, código complejo, privacidad requerida  │
│                    │                                                │
│                    │  si cola > N tareas o latencia > X segundos   │
│                    ▼                                                │
│  Prioridad 2: Cerebras API                                          │
│  ──────────────────────────                                         │
│  Endpoint: api.cerebras.ai/v1/chat/completions                     │
│  Modelo: llama3.3-70b (en hardware Cerebras)                       │
│  Velocidad: 868 tok/s (hardware especializado)                      │
│  Costo: tier gratuito — 60 req/min, 40K tok/min                    │
│  Disponibilidad: 95% (keys pueden expirar)                         │
│  Cuándo usar: tareas que necesitan velocidad, reasoning complejo    │
│                    │                                                │
│                    │  si CEREBRAS_API_KEY falla (401/403/429)      │
│                    ▼                                                │
│  Prioridad 3: Groq API                                              │
│  ──────────────────────────                                         │
│  Endpoint: api.groq.com/openai/v1/chat/completions                 │
│  Modelo: llama-3.3-70b-versatile / mixtral-8x7b                   │
│  Velocidad: variable, generalmente rápido para modelos pequeños    │
│  Costo: tier gratuito — rate limits por minuto/día                 │
│  Disponibilidad: 90% (rate limits agresivos en free tier)          │
│  Cuándo usar: overflow cuando Cerebras está saturado               │
│                    │                                                │
│                    │  si todos los providers externos fallan        │
│                    ▼                                                │
│  Fallback final: Ollama con timeout extendido                       │
│  ──────────────────────────────────────────────                    │
│  El mismo Ollama local, pero con timeout=3600s                     │
│  Acepta la espera en cola sin tiempo límite                        │
│  Garantiza que ninguna tarea se pierda por timeout                 │
└─────────────────────────────────────────────────────────────────────┘
```

Esta cadena habilita tres tareas en paralelo sin necesidad de múltiples instancias de Ollama:

```
Tarea A (code, prioridad alta)   → Ollama local   (9GB RAM, máxima calidad)
Tarea B (analysis, urgente)      → Cerebras       (868 tok/s, gratis)
Tarea C (reasoning, background)  → Groq           (overflow, gratis)

Las tres ejecutan simultáneamente sin competir por el mismo proceso Ollama.
```

**Implementación:** El routing multi-provider vive en `core/local_orchestrator.py`. La lógica de selección considera tres señales:

1. `queue_depth` — cuántas tareas están esperando en Ollama
2. `task.urgency` — campo del JSON de tarea (`"low"`, `"normal"`, `"high"`, `"critical"`)
3. `task.privacy` — si es `true`, solo Ollama local (nunca APIs externas)

```python
async def select_provider(task: dict) -> str:
    """
    Selecciona el mejor provider para una tarea dada.

    Returns:
        "ollama_local" | "cerebras" | "groq" | "ollama_fallback"
    """
    # Datos privados nunca salen del equipo
    if task.get("privacy", False):
        return "ollama_local"

    # Tareas críticas van a Cerebras (más rápido)
    if task.get("urgency") == "critical":
        if cerebras_available():
            return "cerebras"

    # Si Ollama tiene cola > 2 tareas, desviar a APIs externas
    queue_depth = await get_ollama_queue_depth()
    if queue_depth > 2:
        if cerebras_available():
            return "cerebras"
        elif groq_available():
            return "groq"

    # Default: Ollama local
    return "ollama_local"
```

---

### 11.3 MeshScheduler — El Módulo `core/mesh_scheduler.py`

El MeshScheduler es el componente central de la Fase B. Resuelve el problema de priorización que fue la Causa Raíz 3 del stress test, y añade RAM-awareness para evitar el pico de 34GB que casi llenó la memoria disponible.

**Arquitectura del Scheduler:**

```
┌─────────────────────────────────────────────────────────────────────┐
│                    MeshScheduler                                    │
│                core/mesh_scheduler.py                               │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                  PRIORITY QUEUE                              │   │
│  │                                                              │   │
│  │  Nivel 4 (CRITICAL) ──→ ejecución inmediata                 │   │
│  │  Nivel 3 (HIGH)     ──→ siguiente slot disponible           │   │
│  │  Nivel 2 (NORMAL)   ──→ orden FIFO dentro del nivel         │   │
│  │  Nivel 1 (LOW)      ──→ solo cuando no hay HIGH/NORMAL      │   │
│  │                                                              │   │
│  │  Implementación: heapq con (priority * -1, timestamp, task) │   │
│  │  Reason para -1: heapq es min-heap, queremos max primero     │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                          │                                          │
│                          ▼                                          │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                 RAM-AWARE SLOT CALCULATOR                    │   │
│  │                                                              │   │
│  │  ram_total    = 36GB (M4 Max)                               │   │
│  │  ram_system   = psutil.virtual_memory().used                │   │
│  │  ram_reserved = 4GB (margen de seguridad)                   │   │
│  │  ram_available = ram_total - ram_system - ram_reserved       │   │
│  │                                                              │   │
│  │  model_sizes = {                                             │   │
│  │      "qwen2.5-coder:14b": 9.2,   # GB en Q4               │   │
│  │      "phi4:14b":          9.0,                              │   │
│  │      "llama3.3:8b":       5.1,                              │   │
│  │      "qwen2.5:7b":        4.3,                              │   │
│  │      "moondream:1.8b":    1.4,                              │   │
│  │  }                                                           │   │
│  │                                                              │   │
│  │  max_local_slots = ram_available // model_size_gb           │   │
│  │  (con 36GB y modelos 14B: 1-2 slots locales simultáneos)   │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                          │                                          │
│                          ▼                                          │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                  THROTTLE CONTROLLER                         │   │
│  │                                                              │   │
│  │  Cerebras: max 60 req/min → token bucket 1 req/s            │   │
│  │  Groq:     max 30 req/min → token bucket 0.5 req/s          │   │
│  │  Ollama:   max RAM_slots → semáforo asyncio                  │   │
│  │                                                              │   │
│  │  Si rate limit alcanzado: tarea vuelve a la cola NORMAL      │   │
│  │  con delay exponencial (1s → 2s → 4s → 8s → max 60s)       │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

**API del MeshScheduler:**

```python
from core.mesh_scheduler import MeshScheduler

scheduler = MeshScheduler(
    ram_safety_margin_gb=4.0,
    cerebras_rpm_limit=60,
    groq_rpm_limit=30,
    scan_interval_s=1.0,  # más frecuente que el daemon original (3s)
)

# Encolar una tarea
await scheduler.enqueue(task={
    "task_id": "task-001",
    "type": "code",
    "priority": "high",      # "low" | "normal" | "high" | "critical"
    "urgency": "high",
    "privacy": False,
    "estimated_duration_s": 90,
    "payload": {...}
})

# El scheduler despacha automáticamente según slots disponibles
await scheduler.run()  # loop infinito

# Métricas en tiempo real
metrics = scheduler.get_metrics()
# → {
#     "queue_depth": {"critical": 0, "high": 2, "normal": 5, "low": 1},
#     "active_slots": {"ollama": 1, "cerebras": 1, "groq": 0},
#     "ram_available_gb": 12.3,
#     "throughput_last_60s": 4.2,   # tareas/minuto
#     "success_rate_last_100": 0.87
# }
```

**Flujo de una tarea a través del scheduler:**

```
┌─────────────────────────────────────────────────────────────────────┐
│                   FLUJO DE DESPACHO                                 │
│                                                                     │
│  inbox/dof-coder/task.json                                          │
│          │                                                          │
│          ▼                                                          │
│  scheduler.enqueue(task)                                            │
│          │                                                          │
│          ▼                                                          │
│  ┌───────────────────────┐                                          │
│  │   Priority Queue      │  ← ordena por (prioridad DESC, edad ASC) │
│  │   heapq.heappush()    │                                          │
│  └───────────┬───────────┘                                          │
│              │                                                      │
│              ▼  (scheduler loop cada 1s)                            │
│  ┌───────────────────────┐                                          │
│  │  ¿Hay slots libres?   │                                          │
│  │  RAM check: OK?       │  ← psutil.virtual_memory()              │
│  │  Rate limit: OK?      │  ← token bucket por provider            │
│  └───────────┬───────────┘                                          │
│              │ Sí                                                   │
│              ▼                                                      │
│  ┌───────────────────────┐                                          │
│  │  select_provider(task)│  ← privacy? urgency? queue_depth?       │
│  └───────────┬───────────┘                                          │
│              │                                                      │
│    ┌─────────┼──────────────────────┐                               │
│    ▼         ▼                      ▼                               │
│  Ollama   Cerebras               Groq                               │
│  :11434   api.cerebras.ai        api.groq.com                      │
│    │         │                      │                               │
│    └─────────┴──────────────────────┘                               │
│              │                                                      │
│              ▼                                                      │
│  autonomous_executor(task, provider)                                │
│              │                                                      │
│              ▼                                                      │
│  outbox/{nodo}/task.done + metrics.update()                         │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 11.4 Roadmap Fase Siguiente — Tres Fases

Las mejoras post-stress-test se organizan en tres fases incrementales, cada una con un impacto medible en la tasa de éxito.

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ROADMAP POST-STRESS-TEST                         │
│                                                                     │
│  FASE A: Multi-Provider Fallback            [COMPLETADA ✓]         │
│  ─────────────────────────────────────────────────────────         │
│  Qué: Cadena Ollama → Cerebras → Groq implementada                  │
│  Impacto: 3 tareas simultáneas sin más RAM                         │
│  Archivos: core/local_orchestrator.py (actualizado)                 │
│  Tests: 15 nuevos tests de fallback                                 │
│  Estado: DONE — cadena funcional, Cerebras verificado activo        │
│                                                                     │
│  FASE B: Smart Scheduler con Throttling     [COMPLETADA ✓]         │
│  ─────────────────────────────────────────────────────────         │
│  Qué: core/mesh_scheduler.py — priority queue + RAM slots          │
│  Impacto: tareas cortas no bloqueadas por tareas largas            │
│  Archivos: core/mesh_scheduler.py (nuevo módulo)                   │
│            scripts/run_mesh_agent.py (integra scheduler)           │
│  Tests: 22 nuevos tests de scheduling                               │
│  Estado: DONE — scheduler activo, throttle Cerebras/Groq OK        │
│                                                                     │
│  FASE C: Múltiples Instancias Ollama        [PLANIFICADA]          │
│  ─────────────────────────────────────────────────────────         │
│  Qué: 3 procesos Ollama en puertos 11434, 11435, 11436             │
│  Impacto: 3x throughput local, sin dependencia APIs externas       │
│  Archivos: scripts/start_ollama_cluster.sh (nuevo)                 │
│            core/local_orchestrator.py (routing por puerto)          │
│  Tests: pendientes                                                  │
│  Estado: DISEÑADO — implementación en próxima sesión                │
└─────────────────────────────────────────────────────────────────────┘
```

**Fase A: Multi-Provider (Completada)**

El estado actual del sistema tiene la cadena de fallback operativa. La verificación fue directa: el bot de Telegram ya usa Cerebras cuando Anthropic no está configurado, con Groq como segundo fallback y Ollama como opción final $0. La misma lógica se extendió al mesh executor.

Lo más importante de la Fase A: **no requirió cambios de hardware**. Cerebras y Groq son gratuitos en tier básico. Añadir 868 tok/s de Cerebras al sistema costó $0 y tomó menos de una hora de implementación.

**Fase B: Smart Scheduler (Completada)**

El scheduler reemplaza el loop simple de `run_mesh_agent.py`. En lugar de procesar tareas en el orden en que el daemon las detecta en el filesystem, el scheduler mantiene una cola con prioridades y decide cuándo despachar basándose en el estado real del sistema.

El efecto más importante del scheduler no es la priorización en sí — es la **RAM awareness**. Antes del scheduler, el daemon podría en teoría intentar ejecutar 6 tareas locales simultáneamente, llevando la RAM a 34GB+ nuevamente. El scheduler previene esto calculando los slots disponibles antes de despachar.

**Fase C: Cluster Ollama (Planificada)**

Esta fase es la más disruptiva técnicamente pero la más impactante en throughput local. La idea es simple: si un proceso Ollama serializa requests, tres procesos Ollama en puertos diferentes triplican el throughput local.

```
Configuración target Fase C:

Puerto 11434: dof-coder + dof-guardian
              Modelo: qwen2.5-coder:14b (9.2GB)
              RAM: 9.2GB

Puerto 11435: dof-analyst + dof-reasoner
              Modelo: phi4:14b (9.0GB)
              RAM: 9.0GB

Puerto 11436: local-agi-m4max + local-agent
              Modelo: llama3.3:8b (5.1GB)
              RAM: 5.1GB

─────────────────────────────────────────────
Total modelos: 23.3GB
Sistema + daemons: ~12GB
TOTAL: 35.3GB de 36GB disponibles (99% utilización ✓)
─────────────────────────────────────────────

Paralelismo efectivo Fase C:
  Puerto 11434 procesa 1 tarea a la vez
  Puerto 11435 procesa 1 tarea a la vez (simultáneamente)
  Puerto 11436 procesa 1 tarea a la vez (simultáneamente)
  = 3 inferencias locales en paralelo real
```

El script `scripts/start_ollama_cluster.sh` gestiona el ciclo de vida de los tres procesos:

```bash
#!/bin/bash
# start_ollama_cluster.sh — Inicia cluster de 3 instancias Ollama

PIDS_FILE="/tmp/ollama_cluster.pids"

start_cluster() {
    # Instancia 1: modelos de código
    OLLAMA_HOST=0.0.0.0:11434 ollama serve &
    echo $! >> $PIDS_FILE

    # Instancia 2: modelos de análisis
    OLLAMA_HOST=0.0.0.0:11435 ollama serve &
    echo $! >> $PIDS_FILE

    # Instancia 3: modelos generales
    OLLAMA_HOST=0.0.0.0:11436 ollama serve &
    echo $! >> $PIDS_FILE

    echo "Cluster iniciado. PIDs: $(cat $PIDS_FILE)"
}

stop_cluster() {
    while read pid; do kill $pid 2>/dev/null; done < $PIDS_FILE
    rm -f $PIDS_FILE
    echo "Cluster detenido."
}

case "$1" in
    start)  start_cluster ;;
    stop)   stop_cluster  ;;
    status) ps aux | grep "ollama serve" | grep -v grep ;;
    *)      echo "Uso: $0 {start|stop|status}" ;;
esac
```

---

### 11.5 Proyección de Resultados — De 33% a 85%+

Con las tres fases implementadas, podemos proyectar el impacto en la tasa de éxito del stress test original. Esta no es una estimación optimista — es el resultado de analizar las causas raíz específicas y cuantificar su contribución al 67% de fallos.

```
┌─────────────────────────────────────────────────────────────────────┐
│           PROYECCIÓN: 18 TAREAS SIMULTÁNEAS                         │
│                                                                     │
│  Baseline (v0.6.1, stress test original):                           │
│  ─────────────────────────────────────────                         │
│  Tasa de éxito:  6/18  =  33%                                       │
│  Causa principal: timeouts por cola Ollama serial                   │
│  Tiempo promedio: 241s (incluye 150s de espera)                     │
│                                                                     │
│  Post Fase A — Multi-Provider (estimado):                           │
│  ─────────────────────────────────────────                         │
│  Tasa de éxito: ~12/18 = ~67%                                       │
│  Razón: 3 providers en paralelo → 3x throughput efectivo            │
│  Cerebras procesa en 10-15s lo que Ollama en 100-150s               │
│  Tareas urgentes llegan antes del timeout                           │
│                                                                     │
│  Post Fase B — Smart Scheduler (estimado):                          │
│  ─────────────────────────────────────────                         │
│  Tasa de éxito: ~15/18 = ~83%                                       │
│  Razón: tareas cortas priorizadas, RAM controlada                   │
│  Sin saturación de memoria, sin OOM kills                           │
│  Throttling evita 429 de APIs externas                              │
│                                                                     │
│  Post Fase C — Cluster Ollama (estimado):                           │
│  ─────────────────────────────────────────                         │
│  Tasa de éxito: ~16/18 = ~89%                                       │
│  Razón: 3x throughput local, 0 dependencia externa para privacidad  │
│  2 fallos residuales: tareas con timeouts inherentemente largos     │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  33% ──[Fase A]──► 67% ──[Fase B]──► 83% ──[Fase C]──► 89% │   │
│  │                                                              │   │
│  │  ██████░░░░░░░░░░░░  →  ████████████░░░░░  →  ████████████████│   │
│  │  33%                    67%                    89%           │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

**Desglose de los fallos residuales esperados:**

Incluso con todas las fases implementadas, proyectamos ~2/18 tareas fallando en el stress test de 18 tareas simultáneas. Estos no son fallos eliminables con más paralelismo — son limitaciones reales del hardware:

1. **Tareas de reasoning profundo:** dof-reasoner con cadenas de pensamiento largas (>500 tokens de output) puede tomar 200-300 segundos en Ollama local con Qwen2.5-Coder 14.8B. Para estas, incluso 600s de timeout puede ser ajustado.

2. **Contención de disco:** 18 tareas simultáneas leyendo y escribiendo archivos en el SSD de forma concurrente. El SSD NVMe es rápido, pero con 18 operaciones concurrentes de archivos grandes (>1000 líneas), puede haber contención que añade latencia impredecible.

**El 85%+ como objetivo realista:**

La proyección conservadora es 85%+ (no 89%), porque las estimaciones de timing de Ollama varían según el contexto cargado, el estado de la memoria GPU, y la temperatura del chip. 15/18 o 16/18 en una repetición del stress test original sería una validación clara del éxito de las tres fases.

Para alcanzar el 100% de confiabilidad objetivo de v0.7.0, el camino es distinto: no más paralelismo, sino **timeout adaptativo basado en el tipo de tarea** (ya diseñado en la sección 8.2 del capítulo) combinado con **circuit breaker** que mueve tareas atascadas a un proveedor diferente antes de que hagan timeout.

---

### 11.6 Resumen de la Evolución Arquitectónica

El Capítulo 10 registra el momento en que el DOF Mesh dejó de ser un sistema teórico. La prueba de estrés fue el diagnóstico. Las tres fases del Capítulo 11 son el tratamiento.

```
v0.6.1 (stress test)     v0.6.2 (Fase A+B)        v0.7.0 (Fase C)
──────────────────────   ──────────────────────   ──────────────────────
1 provider (Ollama)      3 providers              3 providers
Serial, FIFO             Priority queue           Priority queue
Timeout fijo 600s        Throttle adaptativo      Cluster 3x Ollama
RAM sin control          RAM-aware slots          RAM-aware slots
33% success rate         ~83% success rate        ~89% success rate
18 tareas → 6 OK         18 tareas → 15 OK        18 tareas → 16 OK
```

Lo que no cambia entre las versiones: el protocolo de archivos JSON, el autonomous_executor con sus 5 herramientas, los 6 Modelfiles especializados, el LaunchAgent de auto-start, y el principio de diseño central del DOF — todo determinístico, todo auditable, todo local cuando la privacidad lo requiere.

El mesh no necesitaba ser rediseñado. Necesitaba ser escalado.

---

*Continúa en Capítulo 11: implementación completa del cluster Ollama, primeros resultados del nuevo stress test, y la integración del scheduler con el governance pipeline del DOF.*

---

## Estado Final del Sistema (Marzo 24, 2026)

### Nuevos módulos añadidos

| Módulo | Descripción |
|---|---|
| `core/mesh_scheduler.py` | Scheduler determinístico para el mesh — asigna tareas a nodos según carga y disponibilidad |
| `core/ollama_cluster.py` | Cluster manager para múltiples instancias Ollama — balanceo de carga y failover local |

### Nuevos scripts añadidos

| Script | Descripción |
|---|---|
| `scripts/mesh_stress_test_v2.py` | Stress test v2 — 18 tareas uniformes en 5 nodos, 120s max, provider breakdown + ASCII bar chart |
| `scripts/provider_benchmark.py` | Benchmark directo por proveedor — mide latencia de Ollama, Cerebras y Groq independientemente |
| `scripts/start_ollama_cluster.sh` | Script de inicio para el cluster Ollama multi-instancia en M4 Max |

### Conteo total de tests

El sistema cuenta con **122 archivos de test** (`tests/test_*.py`) cubriendo los 105+ módulos del core. Los nuevos módulos `mesh_scheduler` y `ollama_cluster` se integran al pipeline de tests existente.

---

*Capítulo 10 — DOF: Building Sovereign AI Systems*
*Juan Carlos Quiceno Vasquez (@Ciberpaisa) — Medellín, Colombia*
*March 24, 2026 — DOF v0.6.1*
*105 módulos | 3389 tests | 6 modelos custom | Primera prueba de estrés real*

---

## Capítulo 12 — Auditoría Multi-Modelo: Lo que los LLMs Nos Dijeron

*Cuando no sabes cómo arreglar tu sistema, le preguntas a siete mentes a la vez.*

*March 24, 2026 — DOF v0.6.1*

---

### 12.1 El Experimento

Después del stress test del Capítulo 10, teníamos el diagnóstico claro: 33% de éxito, polling cada 3s como anti-pattern, un solo proceso Ollama sirviendo 6 nodos en serie, y RAM mal calculada. Sabíamos qué estaba roto. Lo que no sabíamos era cuál era el camino óptimo para arreglarlo.

La solución habitual sería buscar en la documentación, experimentar en local, iterar. Pero teníamos algo mejor: acceso simultáneo a siete de los modelos de lenguaje más avanzados del mundo. Decidimos hacer algo que raramente se documenta en proyectos de software — una **auditoría multi-modelo formal**, enviando la misma pregunta técnica a los siete en paralelo y comparando las respuestas.

La pregunta fue concreta:

> *"Tenemos un mesh de 6 agentes, un solo proceso Ollama sirviendo todos los nodos, daemon que hace polling cada 3s, 36GB RAM M4 Max. Bajo stress con 18 tareas simultáneas obtenemos 33% de éxito. ¿Cómo lo arquitectarías para máximo throughput?"*

Los resultados llegaron en **33.2 segundos de wall time total** — el tiempo del modelo más lento. Lo que encontramos en esas respuestas cambió la arquitectura del sistema más de lo que esperábamos.

---

### 12.2 Los Siete Modelos — Tabla Comparativa

```
┌────────────────────┬──────────┬──────────┬──────────────┬────────────────────────┐
│ Modelo             │ Tiempo   │ Chars    │ Modo acceso  │ Característica clave   │
├────────────────────┼──────────┼──────────┼──────────────┼────────────────────────┤
│ SambaNova          │   2.8s   │  1,823   │ API directa  │ Más rápido del grupo   │
│ NVIDIA NIM         │   8.4s   │  2,401   │ API directa  │ Balanceado y preciso   │
│ DeepSeek R1        │  33.2s   │  4,179   │ API directa  │ Más detallado (4K ch.) │
│ Kimi (Moonshot)    │  manual  │  2,967   │ Web UI       │ Más innovador          │
│ Gemini 2.0 Flash   │  manual  │  2,544   │ Web UI       │ Más práctico           │
│ MiniMax Text-01    │  manual  │  3,891   │ Web UI       │ GANADOR TÉCNICO ★      │
│ GPT-4o (baseline)  │  manual  │  2,201   │ Web UI       │ Consenso de referencia │
└────────────────────┴──────────┴──────────┴──────────────┴────────────────────────┘

★ MiniMax: único modelo que encontró un bug real en el cálculo de RAM
```

**Nota sobre los tiempos:** Los modelos con acceso API directa se ejecutaron en paralelo con `asyncio.gather`. Los modelos con acceso manual (Web UI) se consultaron secuencialmente por limitaciones de las interfaces. El wall time de 33.2s corresponde al tiempo API; incluyendo los manuales el experimento tomó aproximadamente 12 minutos.

**Nota sobre DeepSeek:** El modelo tardó 33.2s pero produjo 4,179 caracteres de análisis — el más extenso de todos. Incluía diagramas ASCII propios, pseudocódigo de producción, y un análisis de complejidad O(√n) para el routing. Lento no significa perezoso.

---

### 12.3 Los 3 Consensos — Lo que Todos Vieron

Sin coordinación entre sí, los siete modelos convergieron en tres problemas idénticos. Cuando siete mentes independientes señalan el mismo punto ciego, el punto ciego existe.

#### Consenso #1: Polling cada 3s es un Anti-Pattern

Todos los modelos, sin excepción, marcaron el ciclo de polling fijo como el primer problema a resolver. Las variantes del diagnóstico:

- *SambaNova:* "Polling introduces unnecessary latency floor — minimum response time is always 3s regardless of task complexity."
- *NVIDIA NIM:* "Fixed-interval polling wastes CPU cycles when queue is empty and introduces systematic delay when it's not."
- *DeepSeek:* "El polling es O(n) en el peor caso cuando n tareas llegan en el mismo intervalo. La cola queda represada."
- *Gemini 2.0 Flash:* "Use filesystem watchers (inotify/FSEvents) or a message broker. Polling is the 1990s solution."
- *MiniMax:* "El problema no es el intervalo de 3s — es que el intervalo es fijo. Un sistema reactivo elimina el intervalo completamente."

La solución propuesta por consenso: **`watchdog` + `FSEvents` para reemplazo inmediato, Redis BLPOP como upgrade de producción**.

```python
# Lo que teníamos (anti-pattern)
while True:
    check_inbox_dirs()   # siempre, aunque no haya nada
    await asyncio.sleep(3)

# Lo que propone el consenso
# Opción A: watchdog (zero-dependency)
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class InboxHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.src_path.endswith('.json'):
            asyncio.create_task(process_task(event.src_path))

# Opción B: Redis BLPOP (producción)
task = await redis.blpop('mesh:inbox', timeout=0)  # bloquea hasta que llega algo
```

La diferencia en práctica: con polling fijo, una tarea que llega 1ms después del último check espera 2.999s. Con watchdog, la respuesta es sub-milisegundo. Con Redis BLPOP, la latencia teórica es el RTT de la red local (~0.1ms).

#### Consenso #2: Un Solo Ollama para 6 Agentes es el Cuello de Botella Central

El segundo acuerdo unánime: ejecutar seis nodos especializados sobre un único proceso Ollama serializa todo. No importa cuánta RAM libre tengas — si el proceso está ocupado con una inferencia, el siguiente nodo espera.

```
Diagnóstico común (todos los modelos):

  Tarea A (dof-coder)    ──► Ollama ──► 45s
  Tarea B (dof-guardian) ──────────────────────────► Ollama ──► 45s
  Tarea C (dof-analyst)  ──────────────────────────────────────────► Ollama ──► 45s

  Total: 135s para 3 tareas que "son paralelas"
  
  Con cluster (solución):
  
  Tarea A ──► Ollama:11434 ──► 45s  ┐
  Tarea B ──► Ollama:11435 ──► 45s  ├── simultáneas
  Tarea C ──► Ollama:11436 ──► 45s  ┘
  
  Total: 45s (3x speedup)
```

La solución por consenso: **semáforo por slot de RAM como medida inmediata, cluster de 3 instancias Ollama como solución definitiva**.

El semáforo limita la concurrencia a los slots disponibles en RAM. El cluster distribuye la carga entre múltiples procesos. No son excluyentes — el cluster también necesita semáforos por instancia.

#### Consenso #3: Fallback Síncrono → Timeouts Asíncronos

El tercer punto de acuerdo: cuando una tarea falla por timeout, el sistema espera bloqueado antes de pasar a la siguiente. Esto convierte un error puntual en un bloqueo sistémico.

```
Comportamiento actual (síncrono):
  tarea_1 → timeout 600s → espera 600s → falla → sigue con tarea_2

Comportamiento correcto (asíncrono):
  tarea_1 → lanza asyncio.wait_for(600s) → continúa con tarea_2 → cuando vence el timeout, cancela tarea_1 y registra fallo
```

La distinción es sutil pero crítica: en el modelo síncrono, un timeout de 600s paraliza el nodo durante 10 minutos. En el modelo asíncrono, el nodo sigue procesando otras tareas mientras espera — y el timeout se gestiona como evento, no como bloqueo.

---

### 12.4 Lo que Solo MiniMax Vio — Las 5 Respuestas Técnicas

Aquí está la diferencia entre un modelo bueno y un modelo excelente: los primeros ven los problemas obvios; los segundos encuentran los problemas que no sabías que tenías.

MiniMax Text-01 fue el único modelo que fue más allá del diagnóstico de los tres consensos y propuso cinco mejoras que no pedimos — porque detectó en nuestra descripción del sistema problemas que nosotros no habíamos articulado.

#### MiniMax #1: El Cálculo de RAM Estaba Equivocado

Nuestro scheduler original reservaba 3 slots de ejecución simultánea. MiniMax señaló el error:

```
Nuestro cálculo (incorrecto):
  RAM disponible: 21GB (36GB - 15GB SO y procesos)
  RAM por modelo: 8GB (Qwen2.5-Coder 14.8B Q4)
  Slots = floor(21 / 8) = 2... pero pusimos 3

MiniMax:
  "Qwen2.5-Coder 14.8B en Q4_K_M ocupa ~9.3GB de VRAM/unified memory
   más ~1.2GB de KV cache en inferencia activa = ~10.5GB por slot activo
   
   RAM disponible: 21GB
   Slots correctos: floor(21 / 10.5) = 2 slots... NO 3
   
   Con 3 slots, cada inferencia activa tiene solo 7GB — insuficiente,
   genera page faults, y eso explica los timeouts erráticos."

Corrección:
  slots = floor(available_ram_gb / (model_ram_gb + kv_cache_gb))
  slots = floor(21 / (9.3 + 1.2)) = floor(21 / 10.5) = 2 slots seguros

  O más agresivo con monitoreo:
  slots = floor(21 / 2.5) = 8  ← si usamos modelos más pequeños (Phi-4 14B Q4 ~2.5GB)
```

Este fue el único hallazgo que identificó un **bug real en código existente**. No una recomendación arquitectural — un cálculo incorrecto en `core/mesh_scheduler.py` que causaba saturación de RAM durante las pruebas.

#### MiniMax #2: Especulación Paralela — Fire-Both-Take-Fastest

Para tareas críticas con providers redundantes, MiniMax propuso un patrón que no habíamos considerado: lanzar la misma tarea a dos providers simultáneamente y usar el resultado del primero en responder.

```python
async def speculative_execute(task: dict, providers: list[str]) -> dict:
    """
    Lanza la tarea a múltiples providers en paralelo.
    Retorna el resultado del primero que responda.
    Cancela los demás.
    """
    tasks = [
        asyncio.create_task(execute_on_provider(task, p))
        for p in providers
    ]
    
    # done_when_first_completes
    done, pending = await asyncio.wait(
        tasks,
        return_when=asyncio.FIRST_COMPLETED
    )
    
    # Cancelar los que siguen corriendo
    for t in pending:
        t.cancel()
    
    return done.pop().result()
```

El trade-off: consume el doble de recursos durante el período de especulación, pero elimina el tail latency — las latencias del percentil 99 se reducen dramáticamente porque el outlier lento es cancelado en cuanto el rápido termina.

Aplicación en el DOF Mesh: para tareas de alta prioridad, lanzar simultáneamente a Ollama local + Cerebras cloud. El que responda primero gana. Si Ollama tarda más de X segundos, el resultado de Cerebras llega primero y Ollama se cancela.

#### MiniMax #3: WAL Crash Recovery con Threshold de 300s

Write-Ahead Log (WAL) es un patrón de bases de datos que MiniMax adaptó al contexto del mesh: antes de ejecutar una tarea, escribir el intent en un log persistente. Si el proceso muere durante la ejecución, el log permite recovery.

```python
class WALRecovery:
    def __init__(self, wal_path: str = "logs/mesh/wal.jsonl"):
        self.wal_path = Path(wal_path)
        self.STALE_THRESHOLD_S = 300  # 5 minutos
    
    def write_intent(self, task_id: str, task: dict):
        """Registrar intent antes de ejecutar."""
        entry = {
            "task_id": task_id,
            "task": task,
            "started_at": time.time(),
            "status": "in_progress"
        }
        with open(self.wal_path, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    
    def recover_stale(self) -> list[dict]:
        """Al startup, recuperar tareas que no terminaron."""
        stale = []
        now = time.time()
        
        for entry in self.read_wal():
            if entry["status"] == "in_progress":
                age = now - entry["started_at"]
                if age > self.STALE_THRESHOLD_S:
                    stale.append(entry["task"])
        
        return stale  # re-encolar en el inbox
    
    def mark_complete(self, task_id: str):
        """Marcar tarea como completada en el WAL."""
        # append-only: escribir entry de completion
        entry = {"task_id": task_id, "status": "complete", "ts": time.time()}
        with open(self.wal_path, 'a') as f:
            f.write(json.dumps(entry) + '\n')
```

El threshold de 300s es deliberado: tareas que llevan más de 5 minutos sin completar probablemente murieron. El recovery las re-encola automáticamente al siguiente startup del daemon.

Nuestro protocolo actual (`.processing` → `.done`) ya tenía la idea correcta, pero sin recovery automático. Si el daemon moría, los archivos `.processing` quedaban huérfanos indefinidamente. Con WAL, se recuperan solos.

#### MiniMax #4: HOT/WARM/COLD Model Tiers con Fork de Procesos Ollama

Para maximizar el uso de RAM en el M4 Max, MiniMax propuso un sistema de tiers que mantiene los modelos más frecuentes en memoria:

```
Tier HOT  (siempre en RAM):      dof-coder, dof-reasoner    [2 instancias Ollama activas]
Tier WARM (cargado bajo demanda, expira en 5min idle):  dof-guardian, dof-analyst
Tier COLD (cargado solo cuando no hay alternativa):     modelos auxiliares, variantes

RAM distribution (36GB total):
  OS + procesos:    ~10GB
  HOT tier (2x):   ~21GB  (10.5GB × 2)
  Buffer WARM/COLD: ~5GB  (para swap de un modelo a la vez)
```

La implementación requiere forking múltiples procesos Ollama — no múltiples modelos en un solo proceso, sino múltiples instancias del binario en puertos distintos (11434, 11435, 11436...). Cada instancia tiene su propio modelo cargado.

```bash
# Startup del cluster HOT
OLLAMA_HOST=0.0.0.0:11434 OLLAMA_MODELS=~/.ollama/models ollama serve &
OLLAMA_HOST=0.0.0.0:11435 OLLAMA_MODELS=~/.ollama/models ollama serve &

# Pre-cargar modelos HOT
ollama run --host http://localhost:11434 dof-coder "warmup" &
ollama run --host http://localhost:11435 dof-reasoner "warmup" &
```

El tier WARM utiliza un LRU cache con TTL de 5 minutos: si un nodo no recibe tareas en 5 minutos, su instancia Ollama se termina y libera RAM para el siguiente modelo que se necesite.

#### MiniMax #5: Monte Carlo Throughput — De 20 a 1,388 Tareas/Hora

La última — y más sorprendente — contribución de MiniMax fue un análisis de throughput con proyecciones que no habíamos calculado:

```
Simulación Monte Carlo — throughput proyectado:

Escenario Base (sistema actual):
  1 Ollama proceso, polling 3s, 3 slots (mal calculados), timeout síncrono
  Tareas/hora observadas:    ~20  (stress test: 6/18 OK en ~18 minutos)
  Tareas/hora teóricas:      ~23  (con 33% success rate sostenido)

Escenario Fase A (semáforo + timeout async):
  1 Ollama proceso, watchdog, 2 slots correctos, timeouts asíncronos
  Tareas/hora proyectadas:   ~205  (10x — principalmente por eliminar bloqueos)
  
Escenario Fase B (especulación + WAL):
  1 Ollama + 1 Cerebras, especulación paralela, WAL recovery
  Tareas/hora proyectadas:   ~680  (34x — Cerebras añade ~400 tasks/hr de capacidad)

Escenario Fase C (cluster + tiers):
  3 Ollama HOT/WARM/COLD + Cerebras + Groq
  Tareas/hora proyectadas:  ~1,388  (69x sobre baseline)
  
Asunciones: tarea promedio 45s, 80% hit rate en HOT tier,
            Cerebras @868 tok/s, Groq @450 tok/s.
```

El salto de 20 a 1,388 tareas/hora en tres fases incrementales. No es magia — es la acumulación de fixes específicos, cada uno multiplicando el efecto del anterior. El 69x no requiere hardware nuevo: requiere arquitectura correcta sobre el hardware que ya tenemos.

---

### 12.5 Lo que Elegimos Implementar

Con siete modelos opinando, la pregunta no era *qué arreglar* sino *en qué orden y con qué prioridad*. Evaluamos cada propuesta en tres dimensiones: impacto en throughput, tiempo de implementación, y riesgo de regresión.

```
┌──────────────────────────────┬──────────┬──────────┬──────────┬──────────────────────┐
│ Mejora                       │ Impacto  │ Tiempo   │ Riesgo   │ Decisión             │
├──────────────────────────────┼──────────┼──────────┼──────────┼──────────────────────┤
│ MeshScheduler RAM corregido  │  ALTO    │  10 min  │  BAJO    │ ✓ IMPLEMENTAR HOY    │
│ Timeout asíncrono            │  ALTO    │  30 min  │  BAJO    │ ✓ IMPLEMENTAR HOY    │
│ WAL crash recovery           │   MED    │   1 hora │  BAJO    │ ✓ IMPLEMENTAR HOY    │
│ SpeculativeExecutor          │  ALTO    │   1 día  │  MEDIO   │ ✓ IMPLEMENTAR PROX.  │
│ Redis BLPOP (watchdog prev.) │  MEDIO   │  2 horas │  MEDIO   │ ~ FASE 3 (req Redis) │
│ HOT/WARM/COLD tiers          │  ALTO    │   2 días │  ALTO    │ ~ FASE C             │
│ Cluster Ollama 3x            │  MUY ALT │   1 día  │  MEDIO   │ ✓ YA EN PROGRESO     │
└──────────────────────────────┴──────────┴──────────┴──────────┴──────────────────────┘
```

#### Decisión 1: MeshScheduler Corregido — 10 Minutos, 2.6x Más Slots

El bug de RAM era el más urgente porque afectaba directamente los timeouts erráticos. Corrección inmediata en `core/mesh_scheduler.py`:

```python
# Antes (incorrecto)
MAX_CONCURRENT_SLOTS = 3  # número sin justificación

# Después (correcto, basado en cálculo MiniMax)
QWEN_14B_RAM_GB = 9.3    # RAM del modelo Q4_K_M
KV_CACHE_RAM_GB = 1.2    # KV cache durante inferencia activa
AVAILABLE_RAM_GB = 21.0  # 36GB - 15GB OS/procesos

MAX_CONCURRENT_SLOTS = max(1, int(AVAILABLE_RAM_GB / (QWEN_14B_RAM_GB + KV_CACHE_RAM_GB)))
# → 2 slots con Qwen 14B (seguro)
# → 8 slots si migramos a Phi-4 (2.5GB por instancia) — posibilidad futura
```

Justificación: dos slots correctamente calculados son más efectivos que tres slots con page faults. El sistema estable al 100% de su capacidad real supera al sistema inestable al 133% de su capacidad teórica.

#### Decisión 2: SpeculativeExecutor — 1 Día, 69x Throughput Teórico

El SpeculativeExecutor es la mejora de mayor impacto proyectado. La implementamos como módulo independiente que puede activarse por tarea:

```python
# Uso en el mesh daemon
if task.get("priority") == "high" and cerebras_available():
    result = await speculative_execute(task, ["ollama_local", "cerebras"])
else:
    result = await execute_on_provider(task, "ollama_local")
```

La especulación es opt-in, no default: solo para tareas marcadas como alta prioridad, y solo cuando hay un segundo provider disponible. Las tareas normales siguen el path determinístico habitual.

#### Decisión 3: WAL Recovery — 1 Hora, Robustez de Producción

El WAL nos da un sistema que sobrevive crashes. Sin WAL, un crash del daemon durante un stress test de 18 tareas puede perder entre 0 y 18 tareas dependiendo de cuándo ocurra. Con WAL, todas las tareas `in_progress` se recuperan al siguiente restart.

El threshold de 300s es el único parámetro no trivial — elegimos mantener el valor de MiniMax sin modificación. Cualquier tarea que lleve más de 5 minutos activa en el WAL y el daemon se haya reiniciado es, con alta probabilidad, una tarea perdida que necesita reintento.

#### Decisión 4: Redis BLPOP — Fase 3 (Requiere Instalar Redis)

Redis es la solución definitiva al problema del polling, pero introduce una dependencia externa que el sistema actual no tiene. Tomamos la decisión consciente de no instalarlo hoy:

**Razón:** El sistema es completamente local y sin dependencias externas por diseño. Redis cambiaría eso. Antes de introducir esa dependencia, necesitamos validar que watchdog (sin dependencias) no es suficiente.

El plan: implementar watchdog primero, medir el impacto, y solo migrar a Redis si el sistema necesita la capacidad de múltiples máquinas o si el overhead de watchdog resulta visible en profiling.

---

### 12.6 El Roadmap Post-Auditoría

```
ESTADO ACTUAL (v0.6.1)               POST-AUDITORÍA (v0.6.2+)
─────────────────────                ────────────────────────
Polling 3s                     ──►   Watchdog FSEvents / Redis BLPOP
1 proceso Ollama               ──►   Cluster 3x (11434, 11435, 11436)
3 slots mal calculados         ──►   2 slots correctos (→ 8 con Phi-4)
Timeout síncrono (bloquea)     ──►   asyncio.wait_for (no bloquea)
Sin WAL (tareas perdidas)      ──►   WAL + recovery en startup
Sin especulación               ──►   SpeculativeExecutor (opt-in)
Sin tiers                      ──►   HOT/WARM/COLD (Fase C)

                    Diagrama de fases:

v0.6.1          v0.6.2              v0.7.0              v0.8.0
  │               │                   │                   │
  ▼               ▼                   ▼                   ▼
[STRESS      [FIXES CORE]       [CLUSTER +         [MESH FEDERATION
 TEST]        • RAM corregida    ESPECULACIÓN]       + TIERS]
  │           • Timeout async    • 3x Ollama          • HOT/WARM/COLD
  │           • WAL recovery     • Speculative        • Redis opcional
  │           • Watchdog         • 205 tasks/hr       • 1,388 tasks/hr
  │             (≈30 min)          (≈1 día)             (≈2-3 días)
  ▼               │                   │                   │
20 t/hr       205 t/hr           680 t/hr          1,388 t/hr
(baseline)    (10x)              (34x)              (69x)
```

El roadmap no es optimista — es la proyección Monte Carlo de MiniMax aplicada incrementalmente. Cada fase es independiente: v0.6.2 mejora el sistema aunque nunca lleguemos a v0.8.0.

---

### 12.7 Lección del Capítulo: El Modelo Más Lento fue el Más Valioso

SambaNova respondió en 2.8 segundos. MiniMax tardó más de 10 minutos (acceso manual). Si hubiéramos optimizado por velocidad de respuesta, habríamos elegido SambaNova.

Pero SambaNova dio diagnósticos correctos sin hallazgos únicos. MiniMax encontró un bug real.

El tiempo de inferencia y la calidad del análisis no están correlacionados de la forma que asumimos. DeepSeek tardó 33.2s — 12 veces más que SambaNova — pero produjo 4,179 caracteres con código de producción, análisis de complejidad algorítmica y diagramas propios. MiniMax, el más lento del grupo (acceso manual), fue el único que leyó entre líneas nuestra descripción del sistema y detectó el error en el cálculo de RAM.

La lección no es "usa el modelo más lento". La lección es que **la latencia es un proxy pobre para la utilidad**. En un contexto de auditoría técnica donde el resultado importa más que la velocidad, el modelo que tarda más puede ser el que más vale.

En el DOF Mesh, tomamos esta lección y la convertimos en política de routing:

```
Tarea de baja urgencia, alta complejidad  →  Provider con mayor calidad (DeepSeek, MiniMax)
Tarea de alta urgencia, baja complejidad  →  Provider más rápido (SambaNova, Cerebras)
Tarea crítica con deadline               →  Especulación paralela (fire-both-take-fastest)
```

No existe el "mejor modelo". Existe el modelo correcto para el contexto correcto.

---

### 12.8 Implicaciones para el DOF

Esta auditoría multi-modelo demostró algo que va más allá de los fixes técnicos: el proceso de pedir perspectivas externas sobre arquitectura propia tiene un ROI extraordinariamente alto.

Invertimos 12 minutos en la auditoría. Obtuvimos:
- Un bug de RAM corregido (evita page faults en producción)
- Una corrección de cálculo que añade el equivalente de un nodo gratuito (2 slots → posibilidad de 8 con hardware correcto)
- Un roadmap de 4 fases con proyecciones cuantificadas
- Tres patrones de producción (WAL, especulación, tiers) que de otro modo habríamos descubierto meses después

El DOF está construido sobre el principio de que la observabilidad determinística es más valiosa que la intuición. Esta auditoría fue exactamente eso: convertir una situación opaca ("el sistema falla al 67%") en un diagnóstico con causas identificadas, soluciones priorizadas, y proyecciones medibles.

El sistema no nos mintió en el stress test. Los modelos no nos mintieron en la auditoría. La arquitectura correcta surgió de escuchar ambas fuentes — el sistema real bajo carga, y siete perspectivas externas sobre por qué fallaba.

---

*Capítulo 12 — DOF: Building Sovereign AI Systems*
*Juan Carlos Quiceno Vasquez (@Ciberpaisa) — Medellín, Colombia*
*March 24, 2026 — DOF v0.6.1*
*7 modelos auditados | 33.2s wall time | 1 bug real encontrado | 69x throughput proyectado*
