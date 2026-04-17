# Plan de Acción DOF-MESH — Abril 2026
> Maximizar beneficio con mínimo código nuevo. 680 LOC totales en 4 semanas.

---

## TABLA DE PRIORIZACIÓN (Score Beneficio/Esfuerzo)

| # | Mejora | Archivo | LOC | Beneficio técnico | Beneficio mercado | Horas | Score |
|---|--------|---------|-----|-------------------|-------------------|-------|-------|
| 4 | Tool Result Budgeting | `core/tool_hooks.py` | 45 | 35% | 20% | 2h | **9.4** |
| 2 | Concurrency Classification tools | `core/tool_hooks.py` | 60 | 30% | 25% | 3h | **9.1** |
| 8 | Self-Correction Loop governance | `core/governance.py` | 55 | 25% | 30% | 3h | **8.7** |
| 6 | 4 estrategias compactación | `core/memory_manager.py` | 80 | 40% | 15% | 4h | **8.5** |
| 7 | Disk-backed task list filelock | `core/mesh_scheduler.py` | 70 | 20% | 20% | 3h | **8.2** |
| 1 | Async Generator Loop | `core/autonomous_daemon.py` | 40 | 30% | 10% | 2h | **7.8** |
| 5 | System Prompt DYNAMIC_BOUNDARY | `governance.py`+`commander.py` | 90 | 20% | 35% | 5h | **7.2** |
| 10 | AbortSignal Cascade | `core/claude_commander.py` | 65 | 15% | 25% | 4h | **6.8** |
| 9 | Git Worktree Isolation | `scripts/spawn_worker.sh` | 35 | 20% | 20% | 2h | **6.5** |
| 3 | StreamingToolExecutor | `core/streaming_executor.py` | 150 | 25% | 30% | 8h | **5.1** |

---

## FASE 1 — Días 1–7 (230 LOC, 12h, 0 nuevos módulos)

### Item 4 — Tool Result Budgeting (`core/tool_hooks.py`, 45 LOC)
Agregar `TOOL_OUTPUT_LIMITS` dict + método `_budget_output()` + llamada en `post_tool_use()`.
```python
TOOL_OUTPUT_LIMITS = {"Bash": 8000, "Read": 10000, "fetch_url": 5000, "_default": 4000}
```
**Métrica:** reducción ≥ 35% en tamaño JSONL de audit. Verificar: `wc -c logs/tool_hooks.jsonl`

### Item 2 — Concurrency Classification (`core/tool_hooks.py`, 60 LOC)
Agregar `CONCURRENT_SAFE_TOOLS` + `WRITE_TOOLS` sets + método `classify_tool()`. Bypass de Z3Gate para tools read-only.
```python
CONCURRENT_SAFE_TOOLS = {"Read", "Glob", "Grep", "search", "web_search", ...}
```
**Métrica:** latencia `pre_tool_use` para Read/Glob < 0.5ms (vs ~8ms actual).

### Item 8 — Self-Correction Loop (`core/governance.py`, 55 LOC)
Agregar `check_and_correct()`: si solo viola SOFT_RULES, intenta corrección determinística (regex strip) antes de bloquear.
**Métrica:** tasa de pass en `tests/test_governance.py` debe subir ≥ 10%.

### Item 6 — 4 Estrategias Compactación (`core/memory_manager.py`, 80 LOC)
Agregar `compact(strategy)` con: `ttl_evict`, `score_evict`, `dedup_merge`, `summary_compress`.
**Métrica:** `wc -l memory/long_term.jsonl` reducción ≥ 40% en archivos > 1000 entradas.

---

## FASE 2 — Días 8–14 (200 LOC, 10h)

### Item 7 — Disk-backed task list (`core/mesh_scheduler.py`, 70 LOC)
Usar `filelock==3.25.2` (ya disponible). Persistir `_queue` en `~/.dof/tasks/*.jsonl`.
**Métrica:** queue sobrevive `kill -9` + restart del proceso.

### Item 1 — Async scan_state (`core/autonomous_daemon.py`, 40 LOC)
Convertir 5 sub-tareas de `scan_state()` en coroutines + `asyncio.gather()`.
**Métrica:** `elapsed_ms` en `logs/daemon/cycles.jsonl` reducción ≥ 20%.

### Item 5 — System Prompt Boundary (`governance.py` + `claude_commander.py`, 90 LOC)
Agregar `wrap_with_boundary()` + `_BOUNDARY_INJECTION_PATTERNS` para detectar intentos de inyección en separador sistema/usuario.
**Métrica:** test `test_boundary_injection_blocked` pasa.

---

## FASE 3 — Días 15–28 (250 LOC, 14h)

### Item 10 — AbortSignal Cascade (`core/claude_commander.py`, 65 LOC)
`asyncio.wait_for()` con timeout en `command()`. Retorna `CommandResult(status="timeout")`.
**Métrica:** runaway cycles eliminados. `grep "timeout" logs/commander/commands.jsonl | wc -l` > 0.

### Item 9 — Git Worktree Isolation (`scripts/spawn_worker.sh`, 35 LOC)
`git worktree add /tmp/dof-worker-$NAME -b $BRANCH main` + `trap` cleanup.
**Métrica:** N workers = N worktrees en `git worktree list`. 0 conflictos de merge.

### Item 3 — StreamingToolExecutor (`core/streaming_executor.py`, 150 LOC) — NUEVO MÓDULO
`asyncio.Queue` para emitir chunks de output mientras la tool ejecuta. Requiere Items 2 y 4 como prerequisito.
**Métrica:** primer chunk llega en < 50ms aunque output total sea 4KB.

---

## RESUMEN TOTAL

| Fase | Días | LOC | Horas | Archivos modificados | Archivos nuevos |
|------|------|-----|-------|---------------------|-----------------|
| 1 | 1–7 | 230 | 12h | 3 | 0 |
| 2 | 8–14 | 200 | 10h | 3 | 0 |
| 3 | 15–28 | 250 | 14h | 2 | 1 |
| **Total** | **4 semanas** | **680** | **36h** | **7** | **1** |

---

## DIFERIDOS (evaluar en Semana 5+)

- **DOF-MCP Gateway** — 800 LOC, 40h (extensión de `core/mcp_server.py` existente)
- **DOF-Router** — 1200 LOC, 60h

---

*Plan generado: 2026-04-10 | DOF Mesh Legion*
