# DOF-MESH: Índice de Blindaje Local (Sovereign Hardening Index)
*Phase 4 — Soberanía Absoluta | 2026-04-01*

## Invariantes de Seguridad

| Categoría | Vulnerabilidad Web2 | Defensa DOF-Sovereign | Estado |
| :--- | :--- | :--- | :--- |
| **Identidad** | BOLA en `/api/inbox/{id}` | Nodos firman con `QAION_PRIVATE_KEY` (`X-DOF-Signature`) | [PENDIENTE] |
| **Resiliencia** | Fail-Open en Adaline/Groq | Fail-Closed-to-oMLX: caída externa activa inferencia local | [ACTIVO] |
| **Integridad** | Deps sin SHA pin | SHA-pinning obligatorio. Cero `@latest` en deps críticas | [ACTIVO] |
| **Autonomía** | Single point of failure externo | oMLX + DOF-MESH: stack local completo sin nube | [ACTIVO] |
| **Interoperabilidad** | CLIs no parseables | Agent-First CLI: `--json`, `NO_COLOR`, exit codes 0/1/2/3 | [ACTIVO] |
| **Auditoría** | Fallos silenciosos | Todo fallo de auth → `logs/mesh_security.jsonl` (off-git) | [PENDIENTE] |

---

## Stack Soberano Phase 4

```
[Agente / Claude Code / Humano]
          ↓  --json ó NO_COLOR=1 ó TTY-detection
[DOF-MESH scripts/ — Agent-First CLI]
          ↓  requests.post()  BASE_URL desde .env
[oMLX  localhost:8080/v1]   ← Apple Silicon nativo
          ↓
[Llama 3.3 70B / DeepSeek R1 en MLX]
```

Regla Inmutable: Si Adaline/Groq/Anthropic cae → exit 3 + log → oMLX local.
Si oMLX tampoco responde → proceso termina. Nunca Fail-Open.

---

## oMLX — Motor Local (github.com/jundot/omlx · Apache 2.0)

| Capacidad | Detalle |
|---|---|
| KV Tiering | Contexto en RAM/SSD. AGENTS.md se procesa una vez y se cachea. |
| Multi-modelo | Llama + DeepSeek simultáneos con LRU. |
| API Drop-in | localhost:8080/v1 (OpenAI Chat Completions). Código Python del MESH no cambia. |
| 0 red | Ningún byte sale de la máquina durante inferencia. |

Configuración `.env`:
```
OMLX_BASE_URL=http://localhost:8080/v1
OMLX_MODEL=llama3.3-70b
```

---

## Estándar Agent-First CLI

Todo script nuevo en `scripts/` debe cumplir:

| Regla | Implementación |
|---|---|
| Dual-audience | `--json` → NDJSON para agentes; sin flag → TUI para humanos |
| Auto-detección | `sys.stdout.isatty()` + `NO_COLOR` env var |
| Exit codes | 0=ok, 1=error, 2=bad flags, 3=auth failure |
| Hints | `Hint: <acción>` en cada excepción |
| Context protection | API keys y payloads ocultos por defecto; `--verbose` = opt-in |
| Fail-Fast | Validar auth ANTES de hacer trabajo de red |

Plantilla: `scripts/execute_global_evaluator.py`

---

## Caso de Estudio: Polymarket Hack 2026

| Vector | Lección | Defensa MESH |
|---|---|---|
| BOLA en endpoint | Puerto sin firma = backdoor | Sovereign Auth + X-DOF-Signature |
| Fail-Open en API tercero | Geo-API cae → sistema "se abre" → soberanía perdida | Fail-Closed-to-oMLX |
| Supply chain sin pin | npm infectado compromete host | SHA-pinning obligatorio |

---

## Invariantes de No-Ruptura

1. Prohibido borrar `~/.claude/projects/` sin consentimiento explícito.
2. `docs/06_security/` y `logs/security/` están en `.gitignore`. No subirlos nunca.
3. Ningún paquete nuevo sin SHA pin en dependencias críticas.
4. **VETADO**: OpenClaude y cualquier herramienta basada en source leaks vía npm no-pinned. Vector Glassworm confirmado.
