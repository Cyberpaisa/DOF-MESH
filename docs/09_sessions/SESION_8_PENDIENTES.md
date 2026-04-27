# DOF-MESH — Sesión 8 · Pendientes y contexto para próximas sesiones

**Fecha:** 12 abril 2026  
**Branch:** main | **Versión código:** v0.6.0 (bump a v0.7.0 pendiente)  
**Tests:** 4,302 pasando | **Módulos:** 143

---

## Qué se hizo en esta sesión

### Website dofmesh.com (Mintlify)
- Sweep completo de todos los `.mdx`: 9 chains, 4,302 tests, 143 módulos
- Tempo Chain removido de todas las páginas
- Página `changelog/changelog.mdx` creada — historial v0.5.0 → v0.6.0 → sesión 8
- `docs.json` actualizado con tab "Updates"

### Fase 2 — Resiliencia (commits a main)
- **`core/mesh_scheduler.py`** — `DiskTaskQueue` con filelock
  - Persiste tareas en JSONL, sobrevive reinicios
  - API: `push()`, `pop()`, `drain()`, `clear()`, `size()`
  - 15 tests en `tests/test_disk_task_queue.py`
- **`core/governance.py`** — `BoundaryResult` + `check_system_prompt_boundary()`
  - Detecta leakage de system prompt en respuestas (n-gram sliding window)
  - Detecta injection en mensajes de usuario (reusar _OVERRIDE_PATTERNS)
  - 15 tests en `tests/test_system_prompt_boundary.py`
- **`core/claude_commander.py`** — BOUNDARY check integrado en `command()`

### Fase 3 — Streaming + Aislamiento (commits a main)
- **`core/streaming_executor.py`** — `StreamingToolExecutor` (módulo nuevo)
  - Ejecuta lista de ToolCall con eventos JSONL: ExecutionStarted, ToolStarted, ToolCompleted, ExecutionComplete, ExecutionAborted
  - Soporte abort via `asyncio.Event`
  - Handlers sync y async
  - 15 tests en `tests/test_streaming_executor.py`
- **`core/claude_commander.py`** — AbortSignal Cascade
  - `_abort_event: asyncio.Event` en `__init__`
  - `abort()` y `reset_abort()` para cancelar comandos en vuelo
  - Parámetro `abort_event` en `command()` (caller-supplied o instance-level)
- **`scripts/spawn_worker.sh`** — Git Worktree Isolation
  - Usa `git worktree add` en `/tmp/dof-worktree-*` (no `git checkout -b`)
  - Trap EXIT/INT/TERM → cleanup automático del worktree y branch
  - Workers nunca tocan main

---

## Pendiente para próximas sesiones

### Bump v0.7.0 (acordado — hacer cuando estén listos los cambios acumulados)
Archivos a cambiar:
- `dof/__init__.py` → `__version__ = "0.7.0"`
- `pyproject.toml` → `version = "0.7.0"`
- Todos los `.mdx` → referencias a v0.6.0 → v0.7.0
- `git tag v0.7.0` + publicar `dof-sdk v0.7.0` a PyPI via `scripts/release.sh`

Comando cuando esté listo:
```bash
./scripts/release.sh --bump minor   # 0.6.0 → 0.7.0
# o manual:
# 1. Editar dof/__init__.py y pyproject.toml
# 2. python3 -m unittest discover -s tests
# 3. git tag v0.7.0
# 4. TWINE_USERNAME=__token__ TWINE_PASSWORD=$PYPI_API_TOKEN twine upload dist/*
```

### DOF Leaderboard (descartado por ahora)
- No tiene sentido con solo 2 agentes registrados (#1687, #1686)
- Retomar cuando haya agentes externos usando DOF
- Prerequisito: 10+ agentes registrados en DOFProofRegistry

### Conflux
- Solo testnet hasta resultados del hackathon Global Hackfest 2026
- Contrato desplegado: `0x554cCa8ceBE30dF95CeeFfFBB9ede5bA7C7A9B83` (Chain ID 71)
- 146+ transactions verificadas

### Mejoras posibles para acumular antes del bump v0.7.0
Ideas documentadas (no comprometidas):
- `StreamingToolExecutor` — agregar retry por tool con backoff
- `DiskTaskQueue` — TTL por tarea (expirar tareas viejas automáticamente)
- `SystemPromptBoundary` — semantic similarity check (más allá de n-gram exacto)
- `spawn_worker.sh` — pasar tareas via DiskTaskQueue en vez de inbox/ manual
- DOF Leaderboard — primer diseño

---

## Estado del sistema al cierre de sesión 8

| Componente | Estado |
|---|---|
| Tests | 4,302 / 0 fallos |
| Módulos core | 143 |
| Chains activas | 8 (4 mainnet + 5 testnet) |
| Attestations on-chain | 30+ |
| Z3 proofs | 4/4 PROVEN |
| dofmesh.com | Actualizado y desplegado |
| PyPI dof-sdk | v0.5.1 (bump a v0.7.0 pendiente) |
| Git tag | v0.6.0 (próximo: v0.7.0) |

## Commits de esta sesión (5 commits a main)
- `09a26cb` docs: actualizar dofmesh.com — tests 4272, chains 8, Tempo Chain removido, changelog nuevo
- `6325893` docs: sweep completo — 9 chains en todos los mdx, tests 4272 en refs
- `a3edb32` feat(fase2): DiskTaskQueue filelock + SystemPromptBoundary — 30 tests OK
- `5621ba9` feat(fase3): AbortSignal cascade + StreamingToolExecutor + Git Worktree Isolation — 15 tests OK
- `b8060e1` docs: actualizar métricas sesión 8 — 4302 tests, 143 módulos, changelog completo
