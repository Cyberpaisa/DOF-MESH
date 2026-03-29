# CLI-Anything — Integration with DOF Mesh

## Source
- **Repo**: https://github.com/HKUDS/CLI-Anything
- **License**: MIT
- **Discovered**: March 23, 2026, during the mesh night session

## What It Is
Framework that **automatically generates CLIs** for any software. An AI agent can control GIMP, Blender, OBS, Audacity, LibreOffice, FFmpeg, etc. without fragile GUI automation.

## Why It's Worth Gold for DOF
1. **Universal control**: The mesh's 57 nodes could control ANY installed software
2. **No GUI**: Pure CLI → deterministic → auditable in JSONL → compatible with DOF governance
3. **Auto-generated**: No need to write integrations manually — the pipeline generates them
4. **1839 tests**: Proven quality, compatible with our standard (2481 DOF tests)
5. **Multi-platform**: Claude Code, OpenClaw, Codex — all platforms we use

## Architecture — 7 Phases
1. **Analyze** — Scans source code, maps GUI actions → APIs
2. **Design** — Command architecture, state models, output formats
3. **Implement** — Click-based CLI with REPL, JSON output, undo/redo
4. **Plan Tests** — Creates TEST.md with testing strategies
5. **Write Tests** — Implements test suites automatically
6. **Document** — Updates documentation with results
7. **Publish** — Generates setup.py and installs to PATH

## Supported Apps (16+)
- **Creative**: GIMP, Blender, OBS Studio, Audacity, Krita, Kdenlive, Shotcut, Inkscape
- **Data/AI**: ComfyUI, Ollama, NotebookLM, Novita
- **Diagramming**: Draw.io, Mermaid
- **Infra**: AdGuardHome, Zoom

## Integration with DOF

### Phase 1 — Installation as plugin
```bash
# In Claude Code
/plugin marketplace add HKUDS/CLI-Anything
/plugin install cli-anything

# Generate CLI for an app
/cli-anything:cli-anything ./target-software
```

### Phase 2 — Mesh as orchestrator
```
Commander receives task: "Edit this image in GIMP"
    ↓
CognitiveMap → routing → architect (best for code)
    ↓
architect generates CLI commands:
    cli-anything-gimp --json layer add --name "Background"
    cli-anything-gimp --json filter apply --type "gaussian-blur" --radius 5
    ↓
Cerberus validates the commands (no rm -rf, no injection)
    ↓
Executes on local machine
    ↓
JSON result → governance check → response to mesh
```

### Phase 3 — Each node controls its local software
```
Mesh-Medellin: controls GIMP, Blender, FFmpeg
Mesh-Houston:  controls OBS, Audacity, ComfyUI
Mesh-Europe:   controls LibreOffice, Draw.io

Federation → any node requests from any mesh
```

## Tech Stack
- Python ≥3.10
- Click ≥8.0
- pytest (compatible with unittest via wrapper)
- JSON output (compatible with DOF JSONL)
- SKILL.md (compatible with DOF skill_engine.py)

## Integration Requirements
1. Install CLI-Anything as Claude Code plugin
2. Add wrapper in `core/cli_bridge.py` that connects CLI commands with mesh protocol
3. Add skill in `core/skill_engine.py` for software task routing
4. Cerberus must validate CLI commands before execution (COMMAND_INJECTION check)
5. Logging of all CLI calls to JSONL for auditing

## Strategic Value
- **Differentiator**: No other multi-model framework has real software control
- **Scalability**: Each new app = a `cli-anything:cli-anything ./app` and done
- **Hackathon**: This could be the killer demo — "the mesh edits photos in GIMP while analyzing data in LibreOffice"
- **Book**: New chapter on "Agent Control Plane" using CLI-Anything

## Installation Status (March 23, 2026)

### Installed and running on M4 Max:
- `cli-anything-ollama` v1.0.1 — **SERVER OK**, controls local LLMs
- `cli-anything-audacity` v1.0.0 — Audio editing via sox/ffmpeg

### Software available on the Mac:
- Ollama: `/opt/homebrew/bin/ollama` — INSTALLED, server running
- FFmpeg: `/opt/homebrew/bin/ffmpeg` — INSTALLED
- Node.js: v22.16.0 — INSTALLED

### Pending installation (brew install):
- Blender — 3D rendering (HIGH priority)
- Mermaid CLI (mmdc) — Diagrams from code (HIGH)
- GIMP — Image editing (MEDIUM)
- Inkscape — SVG (MEDIUM)
- Draw.io — Diagrams (MEDIUM)

### Detected failures and needed improvements:
1. `cli-anything-ollama model list` returns empty when no models are available — OK but should suggest `ollama pull`
2. No security validation on CLI commands — DOF Cerberus must intercept
3. subprocess.run() without timeout in some backends — hang risk
4. Session files without file locking on macOS (fcntl works but not all CLIs use it)
5. No integration with DOF JSONL auditing — needs wrapper
6. SKILL.md files not directly compatible with DOF skill_engine.py — needs adapter

### Improvements for DOF (future core/cli_bridge.py):
1. Wrapper that intercepts CLI commands and validates them with Cerberus before executing
2. Logging of all CLI calls to logs/cli_commands.jsonl
3. Configurable timeout per command
4. SKILL.md → DOF skill format adapter
5. Mesh routing: CognitiveMap decides which node runs which software

## Mesh Assignments
- DeepSeek: Analyze algorithmic complexity of the 7-phase pipeline
- GPT-Remote: Propose priority apps for federation
- Antigraviti: Evaluate if Gemini 1M context can improve analysis phase
- Commander: Design core/cli_bridge.py when integration is approved
