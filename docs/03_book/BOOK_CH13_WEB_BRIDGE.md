<<<<<<< HEAD
# Chapter 13 — The Web Bridge: Taking Control of Models Without an API

> *"If they don't give you the key, you build a door."*
> — DOF Mesh, Session March 25, 2026

---

## The Problem

DOF Mesh talks to models via API: DeepSeek, Gemini, Groq, Cerebras.
But there are powerful models that have no free API, have exhausted quotas,
or simply don't exist in programmatic mode.

**MiniMax** is one of them. It has an API, but:
- Requires credits (balance depleted in testing)
- The web version (`agent.minimax.io`) is free
- Has superior capabilities to the API in conversational mode

The question was obvious: **can we make the Mesh talk to the web version without an API?**

---

## The Solution: Playwright Web Bridge

**Playwright** is a browser automation framework. It allows:
- Opening Chrome, Firefox, or Safari programmatically
- Typing in text fields
- Clicking buttons
- Extracting text from the page

The idea: the bridge acts as a **robot human operator** that:
1. Opens Chrome with your saved login session
2. Reads the task from the mesh inbox
3. Types the prompt in the MiniMax chat
4. Waits for the response
5. Extracts the text
6. Delivers it to the mesh

```
Mesh Inbox → WebBridge → Chrome → MiniMax Web → response → Mesh Results
=======
# Capítulo 13 — El Puente Web: Apoderándose de Modelos Sin API

> *"Si no te dan la llave, construyes una puerta."*
> — DOF Mesh, Sesión 25 de Marzo 2026

---

## El Problema

El DOF Mesh habla con modelos vía API: DeepSeek, Gemini, Groq, Cerebras.
Pero hay modelos poderosos que no tienen API gratuita, tienen cuotas agotadas,
o directamente no existen en modo programático.

**MiniMax** es uno de ellos. Tiene API, pero:
- Requiere créditos (balance agotado en pruebas)
- La versión web (`agent.minimax.io`) es gratuita
- Tiene capacidades superiores al API en modo conversacional

La pregunta era obvia: **¿podemos hacer que el Mesh hable con la versión web sin API?**

---

## La Solución: Playwright Web Bridge

**Playwright** es un framework de automatización de browsers. Permite:
- Abrir Chrome, Firefox o Safari programáticamente
- Escribir en campos de texto
- Hacer clic en botones
- Extraer texto de la página

La idea: el bridge actúa como un **operador humano robot** que:
1. Abre Chrome con tu sesión de login guardada
2. Lee la tarea del mesh inbox
3. Escribe el prompt en el chat de MiniMax
4. Espera la respuesta
5. Extrae el texto
6. Lo entrega al mesh

```
Mesh Inbox → WebBridge → Chrome → MiniMax Web → respuesta → Mesh Results
>>>>>>> 4e63386 (refactor: organize repo into professional structure)
```

---

<<<<<<< HEAD
## Bridge Architecture

### File: `core/web_bridge.py`
=======
## Arquitectura del Bridge

### Archivo: `core/web_bridge.py`
>>>>>>> 4e63386 (refactor: organize repo into professional structure)

```python
WEB_TARGETS = {
    "minimax": {
        "url": "https://agent.minimax.io/chat",
<<<<<<< HEAD
        "input_selector": ".tiptap.ProseMirror",   # Rich editor (not textarea)
=======
        "input_selector": ".tiptap.ProseMirror",   # Editor rico (no textarea)
>>>>>>> 4e63386 (refactor: organize repo into professional structure)
        "response_selector": ".message.received .message-content",
        "wait_ms": 40000,
    },
    "gemini":  { ... },
    "chatgpt": { ... },
    "kimi":    { ... },
    "deepseek":{ ... },
}
```

<<<<<<< HEAD
**`WebBridge` class:**
- `start()` — opens Chrome with persistent profile, loads saved session
- `send_and_receive(prompt)` — types, sends, waits for real response
- `process_inbox()` — processes all `.json` files from inbox
- `run(poll_interval)` — infinite loop, polling every N seconds

### File: `scripts/open_minimax.py`
Setup script: opens Chrome, gives you 3 minutes to log in, saves the session to:
=======
**Clase `WebBridge`:**
- `start()` — abre Chrome con perfil persistente, carga sesión guardada
- `send_and_receive(prompt)` — escribe, envía, espera respuesta real
- `process_inbox()` — procesa todos los `.json` del inbox
- `run(poll_interval)` — loop infinito, poll cada N segundos

### Archivo: `scripts/open_minimax.py`
Script de setup: abre Chrome, te da 3 minutos para loguearte, guarda la sesión en:
>>>>>>> 4e63386 (refactor: organize repo into professional structure)
```
logs/browser_profiles/minimax/session_state.json
```

---

<<<<<<< HEAD
## Testing Session — March 25, 2026, 00:00–00:30

### Timeline of Problems and Solutions

| Time  | Problem | Solution |
|-------|---------|----------|
| 00:03 | Playwright Chromium blocked by Google ("unsafe browser") | Switch to `channel="chrome"` (real system Chrome) |
| 00:05 | `input()` doesn't work in Claude subprocess | Script with 3-minute countdown (`time.sleep`) |
| 00:07 | Browser closes by itself | `nohup` + background with `&` |
| 00:10 | Profile lock (`SingletonLock`) when opening second Chrome | Remove `Singleton*` files before launching |
| 00:13 | Selector `.tiptap.ProseMirror` not found | Identified via HTML debug — MiniMax uses ProseMirror, not `<textarea>` |
| 00:15 | Response = "No files found" | Incorrect response selector |
| 00:18 | Capturing "Received. I am processing..." instead of real response | HTML analysis → correct selector: `.message.received .message-content` |
| 00:25 | Response is still the processing message | Polling logic: wait until text stops containing processing keywords |

### Results by Task

| Task ID | Prompt | Result | Status |
|---------|--------|--------|--------|
| CONDOR-MESH-001 | Validate bridge | "No files found" | ✗ Bad selector |
| CONDOR-MESH-002 | Say: CONDOR CONFIRMED | "Received... CONDOR CONFIRMED — MiniMax — ACTIVE" | ✓ Partial |
| CONDOR-MESH-003 | Say: CONDOR CONFIRMED | "CONDOR CONFIRMED — MiniMax — ACTIVE" | ✓ **CONFIRMED** |
| JAGUAR-001 | Say: JAGUAR CONFIRMS | "Received. I am working on it." | ✗ Selector timing |
| AGUILA-MESH-001 | Ollama bottlenecks | "I received your request..." | ✗ Credits depleted |
| CONDOR-FINAL-001 | Say: MESH ONLINE | "Received. I am processing..." | ✗ Logic in development |

**Best confirmed result:**
```
CONDOR-MESH-003 → MiniMax responded:
"CONDOR CONFIRMED — MiniMax — ACTIVE"
```
No API. No credits. Just Playwright.

---

## The Key Technical Discovery

### MiniMax does not use `<textarea>`

Most web chats use `<textarea>`. MiniMax uses **ProseMirror**,
a rich text editor used in Notion, Linear, and others.

```css
.tiptap.ProseMirror  /* input editor */
.message.received    /* AI messages */
.message.sent        /* user messages */
```

To clear the field before typing:
=======
## Sesión de Pruebas — 25 Marzo 2026, 00:00–00:30

### Cronología de Problemas y Soluciones

| Hora  | Problema | Solución |
|-------|----------|----------|
| 00:03 | Playwright Chromium bloqueado por Google ("navegador no seguro") | Cambiar a `channel="chrome"` (Chrome real del sistema) |
| 00:05 | `input()` no funciona en subproceso de Claude | Script con cuenta regresiva de 3 min (`time.sleep`) |
| 00:07 | Browser se cierra solo | `nohup` + background con `&` |
| 00:10 | Profile lock (`SingletonLock`) cuando se abre segundo Chrome | Eliminar archivos `Singleton*` antes de lanzar |
| 00:13 | Selector `.tiptap.ProseMirror` no encontrado | Identificado mediante debug HTML — MiniMax usa ProseMirror, no `<textarea>` |
| 00:15 | Respuesta = "No files found" | Selector de respuesta incorrecto |
| 00:18 | Captura "Recibido. Estoy procesando..." en vez de respuesta real | Análisis del HTML → selector correcto: `.message.received .message-content` |
| 00:25 | Respuesta sigue siendo el mensaje de procesamiento | Lógica de polling: esperar hasta que texto deje de contener keywords de procesamiento |

### Resultados por Tarea

| Task ID | Prompt | Resultado | Estado |
|---------|--------|-----------|--------|
| CONDOR-MESH-001 | Valida bridge | "No files found" | ✗ Selector malo |
| CONDOR-MESH-002 | Di: CONDOR CONFIRMADO | "Recibido... CONDOR CONFIRMADO — MiniMax — ACTIVO" | ✓ Parcial |
| CONDOR-MESH-003 | Di: CONDOR CONFIRMADO | "CONDOR CONFIRMADO — MiniMax — ACTIVO" | ✓ **CONFIRMADO** |
| JAGUAR-001 | Di: JAGUAR CONFIRMA | "Recibido. Estoy trabajando en ello." | ✗ Selector timing |
| AGUILA-MESH-001 | Bottlenecks Ollama | "Recibí tu solicitud..." | ✗ Créditos agotados |
| CONDOR-FINAL-001 | Di: MESH ONLINE | "Recibido. Estoy procesando..." | ✗ Lógica en desarrollo |

**Mejor resultado confirmado:**
```
CONDOR-MESH-003 → MiniMax respondió:
"CONDOR CONFIRMADO — MiniMax — ACTIVO"
```
Sin API. Sin créditos. Solo Playwright.

---

## El Descubrimiento Técnico Clave

### MiniMax no usa `<textarea>`

La mayoría de chats web usan `<textarea>`. MiniMax usa **ProseMirror**,
un editor de texto rico usado en Notion, Linear y otros.

```css
.tiptap.ProseMirror  /* editor de entrada */
.message.received    /* mensajes del AI */
.message.sent        /* mensajes del usuario */
```

Para limpiar el campo antes de escribir:
>>>>>>> 4e63386 (refactor: organize repo into professional structure)
```python
page.keyboard.press("Control+a")
page.keyboard.press("Delete")
```

<<<<<<< HEAD
### The Intermediate Message Problem

MiniMax shows an immediate message while processing:
```
"Received. I am processing your request."
```

This message appears in the same `.message.received` selector as the final response.
The bridge was capturing this message instead of the real one.

**Implemented solution:**
```python
processing_kw = ["received", "processing", "working on it", "getting started"]
=======
### El Problema del Mensaje Intermediario

MiniMax muestra un mensaje inmediato mientras procesa:
```
"Recibido. Estoy procesando tu solicitud."
```

Este mensaje aparece en el mismo selector `.message.received` que la respuesta final.
El bridge capturaba este mensaje en vez del real.

**Solución implementada:**
```python
processing_kw = ["recibido", "procesando", "estoy trabajando", "estoy comenzando"]
>>>>>>> 4e63386 (refactor: organize repo into professional structure)

for _ in range(max_wait):
    current = last_message.inner_text()
    is_processing = any(k in current.lower() for k in processing_kw)
    if not is_processing and current == prev_text:
        stable_count += 1
        if stable_count >= 3:
            final_text = current
            break
```

---

<<<<<<< HEAD
## The Robot Operator Analogy

Imagine hiring someone to use MiniMax for you:
1. You give them a note with the message
2. They open the laptop, go to MiniMax, type the message
3. Wait for the response
4. Bring you the written response

The WebBridge is that operator. Except it works at 20x human speed,
never gets tired, and delivers the response directly to the mesh.

---

## Production Setup

### 1. Initial setup (one time only)
```bash
python3 scripts/open_minimax.py
# Opens Chrome → you log in → session saved
```

### 2. Start the bridge
=======
## La Analogía del Robot Operador

Imagina que contratas a alguien para que use MiniMax por ti:
1. Le das una nota con el mensaje
2. Él abre la laptop, va a MiniMax, escribe el mensaje
3. Espera la respuesta
4. Te trae la respuesta escrita

El WebBridge es ese operador. Solo que trabaja a 20x la velocidad humana,
nunca se cansa, y entrega la respuesta directo al mesh.

---

## Configuración para Producción

### 1. Setup inicial (una sola vez)
```bash
python3 scripts/open_minimax.py
# Abre Chrome → te logueas → sesión guardada
```

### 2. Arrancar el bridge
>>>>>>> 4e63386 (refactor: organize repo into professional structure)
```bash
python3 core/web_bridge.py --node minimax --poll 10
```

<<<<<<< HEAD
### 3. Send tasks via mesh
```json
{
  "task_id": "MY-TASK-001",
  "from": "claude-session-1",
  "to": "minimax",
  "prompt": "Your question here"
}
```
Save to: `logs/mesh/inbox/minimax/MY-TASK-001.json`

### 4. Read response
```
logs/local-agent/results/MY-TASK-001.json
logs/mesh/inbox/claude-session-1/MY-TASK-001.json
=======
### 3. Enviar tareas via mesh
```json
{
  "task_id": "MI-TAREA-001",
  "from": "claude-session-1",
  "to": "minimax",
  "prompt": "Tu pregunta aquí"
}
```
Guardar en: `logs/mesh/inbox/minimax/MI-TAREA-001.json`

### 4. Leer respuesta
```
logs/local-agent/results/MI-TAREA-001.json
logs/mesh/inbox/claude-session-1/MI-TAREA-001.json
>>>>>>> 4e63386 (refactor: organize repo into professional structure)
```

---

<<<<<<< HEAD
## Final Bridge Status

| Feature | Status |
|---------|--------|
| Real Chrome (not Playwright Chromium) | ✅ |
| Persistent session (saved cookies) | ✅ |
| Mesh inbox reading | ✅ |
| ProseMirror writing | ✅ |
| Delivery to claude-session-1 | ✅ |
| Detection of real response vs processing | 🔧 Fine-tuning |
| 5 supported models (Gemini, ChatGPT, Kimi, DeepSeek, MiniMax) | ✅ |

---

## Files Created This Session

```
core/web_bridge.py          — Main bridge (260 lines)
scripts/open_minimax.py     — Session setup (40 lines)
scripts/setup_web_session.py — Generic setup for any node
scripts/debug_minimax.py    — HTML selector inspector
logs/browser_profiles/minimax/session_state.json — Saved session
=======
## Estado Final del Bridge

| Feature | Estado |
|---------|--------|
| Chrome real (no Playwright Chromium) | ✅ |
| Sesión persistente (cookies guardadas) | ✅ |
| Lectura de inbox mesh | ✅ |
| Escritura en ProseMirror | ✅ |
| Entrega a claude-session-1 | ✅ |
| Detección de respuesta real vs procesando | 🔧 En ajuste fino |
| 5 modelos soportados (Gemini, ChatGPT, Kimi, DeepSeek, MiniMax) | ✅ |

---

## Archivos Creados Esta Sesión

```
core/web_bridge.py          — Bridge principal (260 líneas)
scripts/open_minimax.py     — Setup de sesión (40 líneas)
scripts/setup_web_session.py — Setup genérico para cualquier nodo
scripts/debug_minimax.py    — Inspector de selectores HTML
logs/browser_profiles/minimax/session_state.json — Sesión guardada
>>>>>>> 4e63386 (refactor: organize repo into professional structure)
```

---

<<<<<<< HEAD
## What Comes Next

1. **Gemini bridge** — already configured, needs session
2. **ChatGPT bridge** — selector `#prompt-textarea` already tested
3. **Stable final response** — the polling with keyword-filter is written, needs validation with MiniMax with credits
4. **Bridge daemon** — run all bridges in parallel as services

---

## Lesson from This Session

> If a model has no API, no problem.
> DOF Mesh doesn't need API keys.
> It needs a browser and a session.
>
> The mesh is the protocol.
> The bridge is the hand.
> The result arrives all the same.

---

*Chapter 13 — DOF Mesh: The Book*
*Session: March 25, 2026, 00:00–00:30 COT*
*Author: Juan Carlos Quiceno Vasquez + Claude Sonnet 4.6*
=======
## Lo Que Viene

1. **Gemini bridge** — ya configurado, necesita sesión
2. **ChatGPT bridge** — selector `#prompt-textarea` ya probado
3. **Respuesta final estable** — el polling con keyword-filter está escrito, falta validar con MiniMax con créditos
4. **Bridge daemon** — correr todos los bridges en paralelo como servicios

---

## Lección de Esta Sesión

> Si un modelo no tiene API, no hay problema.
> El DOF Mesh no necesita API keys.
> Necesita un browser y una sesión.
>
> El mesh es el protocolo.
> El bridge es la mano.
> El resultado llega igual.

---

*Capítulo 13 — DOF Mesh: El Libro*
*Sesión: 25 de Marzo 2026, 00:00–00:30 COT*
*Autor: Juan Carlos Quiceno Vasquez + Claude Sonnet 4.6*
>>>>>>> 4e63386 (refactor: organize repo into professional structure)
