# CLI-Anything — Integración con DOF Mesh

## Fuente
- **Repo**: https://github.com/HKUDS/CLI-Anything
- **Licencia**: MIT
- **Descubierto**: 23 de Marzo 2026, durante sesión nocturna del mesh

## Qué es
Framework que **genera CLIs automáticamente** para cualquier software. Un agente IA puede controlar GIMP, Blender, OBS, Audacity, LibreOffice, FFmpeg, etc. sin GUI automation frágil.

## Por qué vale oro para DOF
1. **Control universal**: Los 57 nodos del mesh podrían controlar CUALQUIER software instalado
2. **Sin GUI**: CLI puro → determinístico → auditable en JSONL → compatible con governance DOF
3. **Auto-generado**: No hay que escribir integraciones manualmente — el pipeline las genera
4. **1839 tests**: Calidad probada, compatible con nuestro estándar (2481 tests DOF)
5. **Multi-plataforma**: Claude Code, OpenClaw, Codex — todas las plataformas que usamos

## Arquitectura — 7 Fases
1. **Analyze** — Escanea código fuente, mapea GUI actions → APIs
2. **Design** — Arquitectura de comandos, modelos de estado, formatos de output
3. **Implement** — CLI basado en Click con REPL, JSON output, undo/redo
4. **Plan Tests** — Crea TEST.md con estrategias de testing
5. **Write Tests** — Implementa test suites automáticamente
6. **Document** — Actualiza documentación con resultados
7. **Publish** — Genera setup.py e instala en PATH

## Apps Soportadas (16+)
- **Creative**: GIMP, Blender, OBS Studio, Audacity, Krita, Kdenlive, Shotcut, Inkscape
- **Data/AI**: ComfyUI, Ollama, NotebookLM, Novita
- **Diagramming**: Draw.io, Mermaid
- **Infra**: AdGuardHome, Zoom

## Integración con DOF

### Fase 1 — Instalación como plugin
```bash
# En Claude Code
/plugin marketplace add HKUDS/CLI-Anything
/plugin install cli-anything

# Generar CLI para una app
/cli-anything:cli-anything ./target-software
```

### Fase 2 — Mesh como orquestador
```
Commander recibe tarea: "Edita esta imagen en GIMP"
    ↓
CognitiveMap → routing → architect (mejor para código)
    ↓
architect genera CLI commands:
    cli-anything-gimp --json layer add --name "Background"
    cli-anything-gimp --json filter apply --type "gaussian-blur" --radius 5
    ↓
Cerberus valida los comandos (no rm -rf, no injection)
    ↓
Ejecuta en la máquina local
    ↓
Resultado JSON → governance check → respuesta al mesh
```

### Fase 3 — Cada nodo controla su software local
```
Mesh-Medellín: controla GIMP, Blender, FFmpeg
Mesh-Houston:  controla OBS, Audacity, ComfyUI
Mesh-Europa:   controla LibreOffice, Draw.io

Federación → cualquier nodo pide a cualquier mesh
```

## Stack Técnico
- Python ≥3.10
- Click ≥8.0
- pytest (compatible con unittest via wrapper)
- JSON output (compatible con JSONL de DOF)
- SKILL.md (compatible con DOF skill_engine.py)

## Requisitos de Integración
1. Instalar CLI-Anything como plugin de Claude Code
2. Agregar wrapper en `core/cli_bridge.py` que conecte CLI commands con mesh protocol
3. Agregar skill en `core/skill_engine.py` para routing de tareas de software
4. Cerberus debe validar CLI commands antes de ejecución (COMMAND_INJECTION check)
5. Logging de todos los CLI calls a JSONL para auditoría

## Valor Estratégico
- **Diferenciador**: Ningún otro framework multi-modelo tiene control de software real
- **Escalabilidad**: Cada nueva app = un `cli-anything:cli-anything ./app` y listo
- **Hackathon**: Esto podría ser la demo killer — "el mesh edita fotos en GIMP mientras analiza datos en LibreOffice"
- **Libro**: Capítulo nuevo sobre "Agent Control Plane" usando CLI-Anything

## Estado de Instalación (23 Marzo 2026)

### Instalado y funcionando en M4 Max:
- `cli-anything-ollama` v1.0.1 — **SERVER OK**, controla LLMs locales
- `cli-anything-audacity` v1.0.0 — Audio editing via sox/ffmpeg

### Software disponible en el Mac:
- Ollama: `/opt/homebrew/bin/ollama` — INSTALLED, server running
- FFmpeg: `/opt/homebrew/bin/ffmpeg` — INSTALLED
- Node.js: v22.16.0 — INSTALLED

### Pendiente de instalar (brew install):
- Blender — 3D rendering (HIGH priority)
- Mermaid CLI (mmdc) — Diagrams from code (HIGH)
- GIMP — Image editing (MEDIUM)
- Inkscape — SVG (MEDIUM)
- Draw.io — Diagrams (MEDIUM)

### Fallos detectados y mejoras necesarias:
1. `cli-anything-ollama model list` retorna vacío cuando no hay modelos — OK pero debería sugerir `ollama pull`
2. No hay validación de seguridad en los CLI commands — DOF Cerberus debe interceptar
3. subprocess.run() sin timeout en algunos backends — riesgo de hang
4. Session files sin file locking en macOS (fcntl funciona pero no todos los CLIs lo usan)
5. No hay integración con JSONL auditing de DOF — necesita wrapper
6. Los SKILL.md no son compatibles directamente con DOF skill_engine.py — necesita adaptador

### Mejoras para DOF (core/cli_bridge.py futuro):
1. Wrapper que intercepta CLI commands y los valida con Cerberus antes de ejecutar
2. Logging de todos los CLI calls a logs/cli_commands.jsonl
3. Timeout configurable por comando
4. Adaptador SKILL.md → DOF skill format
5. Mesh routing: CognitiveMap decide qué nodo ejecuta qué software

## Asignaciones al Mesh
- DeepSeek: Analizar complejidad algorítmica del pipeline de 7 fases
- GPT-Remote: Proponer apps prioritarias para federación
- Antigraviti: Evaluar si Gemini 1M context puede mejorar fase de análisis
- Commander: Diseñar core/cli_bridge.py cuando se apruebe integración
