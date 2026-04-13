# DOF-MESH — Estado Caliente

> Último update: 2026-04-13

## Tests
**4,465** passing · 0 failures · 0 errors

## Versión activa
`v0.8.0` · PyPI: `dof-sdk==0.8.0`

## Features nuevas (sesión 9)

### DOF-MCP Gateway — `0c5032f`
- `core/gateway/` — FastAPI HTTP bridge para `mcp_server.py`
- Auth por `x-api-key` header, rate limiting 100 req/min, CORS abierto
- 15 tools expuestas vía `POST /mcp/tools/{tool_name}`
- Dev mode: acepta cualquier key `sk-dof-*` si `DOF_GATEWAY_KEYS` no está seteada
- 10 tests · `GET /health` sin auth
- Arrancar: `DOF_GATEWAY_KEYS=sk-dof-xxx uvicorn core.gateway.server:app --port 8080`

### DOF-Router — `ba9bf14`
- `core/router/` — routing inteligente con failover automático
- `DOFRouter.select_agent()`: excluye agentes con 3+ fallos consecutivos, elige por menor latencia, desempata por `last_used`
- `FailoverHandler`: hasta 3 intentos, reroute automático, log JSONL
- `MetricsStore`: persistencia en `logs/router/agent_metrics.jsonl`
- 13 tests · backward compatible con daemon actual

## Pendiente

- [ ] **Activar DOF-Router en daemon con feature flag**
  - En `core/feature_flags.py`: agregar `dof_router: false`
  - En `core/autonomous_daemon.py`, función `execute()`:
    ```python
    # reemplazar:
    agent_id = self._select_provider()
    # con:
    agent_id = self.router.select_agent(task_type=action.mode) if self.router else self._select_provider()
    ```
  - Activar con `dof_router: true` cuando haya métricas reales

## Commits recientes

```
ba9bf14  feat(router): DOF-Router — intelligent agent routing with failover (13 tests)
0c5032f  feat(gateway): DOF-MCP Gateway — HTTP bridge para mcp_server (FastAPI + auth + rate limiting)
```
