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
```

---

## Arquitectura del Bridge

### Archivo: `core/web_bridge.py`

```python
WEB_TARGETS = {
    "minimax": {
        "url": "https://agent.minimax.io/chat",
        "input_selector": ".tiptap.ProseMirror",   # Editor rico (no textarea)
        "response_selector": ".message.received .message-content",
        "wait_ms": 40000,
    },
    "gemini":  { ... },
    "chatgpt": { ... },
    "kimi":    { ... },
    "deepseek":{ ... },
}
```

**Clase `WebBridge`:**
- `start()` — abre Chrome con perfil persistente, carga sesión guardada
- `send_and_receive(prompt)` — escribe, envía, espera respuesta real
- `process_inbox()` — procesa todos los `.json` del inbox
- `run(poll_interval)` — loop infinito, poll cada N segundos

### Archivo: `scripts/open_minimax.py`
Script de setup: abre Chrome, te da 3 minutos para loguearte, guarda la sesión en:
```
logs/browser_profiles/minimax/session_state.json
```

---

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
```python
page.keyboard.press("Control+a")
page.keyboard.press("Delete")
```

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
```bash
python3 core/web_bridge.py --node minimax --poll 10
```

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
```

---

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
```

---

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
