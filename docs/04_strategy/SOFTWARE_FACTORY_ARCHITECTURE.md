# Software Factory API — Architecture Design

**Author**: architect node (DOF Agent Mesh)
**Date**: 2026-03-22
**Status**: DESIGN — ready for guardian review

---

## 1. Overview

The Software Factory is a FastAPI service that exposes the DOF Node Mesh and Claude Commander as HTTP endpoints. It turns the agent mesh into a programmable platform: any client (Telegram bot, dashboard, CI/CD pipeline, external agent) can spawn nodes, queue tasks, monitor execution, and read results via REST.

```
┌─────────────────────────────────────────────────────────┐
│                    SOFTWARE FACTORY API                   │
│                   (FastAPI + Uvicorn)                     │
│                                                          │
│  /api/v1/nodes/*     ← Node lifecycle (CRUD + spawn)    │
│  /api/v1/tasks/*     ← Task queue (submit, status, cancel)│
│  /api/v1/messages/*  ← Message bus (send, inbox, convo)  │
│  /api/v1/pipelines/* ← Sequential/parallel workflows     │
│  /api/v1/monitor/*   ← Health, metrics, audit logs       │
│  /api/v1/sessions/*  ← Session persistence & discovery   │
│  /ws/events          ← WebSocket live stream             │
│                                                          │
├──────────────┬───────────────────┬───────────────────────┤
│  NodeMesh    │  ClaudeCommander  │  TaskQueue (new)      │
│  (core/)     │  (core/)          │  (core/)              │
└──────────────┴───────────────────┴───────────────────────┘
```

## 2. Core Principles

1. **Thin API layer** — FastAPI is a facade; all logic lives in `core/node_mesh.py` and `core/claude_commander.py`
2. **Async-native** — Both underlying modules are async; FastAPI runs on uvicorn with asyncio event loop
3. **Task queue for long-running ops** — Spawning a node takes 7-120s; API returns a `task_id` immediately and clients poll or subscribe via WebSocket
4. **Governance-first** — All commands pass through `governed_command()` by default
5. **Budget-aware** — Global budget ceiling ($100) enforced; every task logs cost
6. **No secrets in responses** — Outputs are sanitized before returning

## 3. Data Models (Pydantic)

```python
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

# ═══ Enums ═══

class NodeStatus(str, Enum):
    idle = "idle"
    active = "active"
    spawning = "spawning"
    error = "error"

class TaskStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"

class MessageType(str, Enum):
    task = "task"
    result = "result"
    query = "query"
    alert = "alert"
    sync = "sync"

# ═══ Request Models ═══

class SpawnNodeRequest(BaseModel):
    node_id: str = Field(..., pattern=r'^[a-z0-9\-]+$', max_length=64)
    task: str = Field(..., max_length=10000)
    role: Optional[str] = None
    tools: Optional[list[str]] = None
    model: Optional[str] = None
    governed: bool = True  # pass through governance by default

class SendMessageRequest(BaseModel):
    from_node: str
    to_node: str  # "*" for broadcast
    content: str = Field(..., max_length=5000)
    msg_type: MessageType = MessageType.task
    reply_to: Optional[str] = None

class SubmitTaskRequest(BaseModel):
    """Submit a task to the queue without tying it to a specific node."""
    prompt: str = Field(..., max_length=10000)
    node_id: Optional[str] = None  # auto-assign if None
    priority: int = Field(default=5, ge=1, le=10)  # 1=highest
    tools: Optional[list[str]] = None
    governed: bool = True
    callback_url: Optional[str] = None  # webhook on completion

class PipelineStep(BaseModel):
    node_id: str
    task: str

class PipelineRequest(BaseModel):
    steps: list[PipelineStep]

class TeamSpawnRequest(BaseModel):
    nodes: dict[str, str]  # {node_id: task_prompt}
    parallel: bool = True

# ═══ Response Models ═══

class NodeResponse(BaseModel):
    node_id: str
    role: str
    status: NodeStatus
    session_id: Optional[str] = None
    model: str
    messages_sent: int = 0
    messages_received: int = 0
    last_active: float = 0
    created_at: float = 0

class TaskResponse(BaseModel):
    task_id: str
    status: TaskStatus
    node_id: Optional[str] = None
    prompt_preview: str  # first 200 chars
    priority: int
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    output: Optional[str] = None
    elapsed_ms: Optional[float] = None

class MeshStateResponse(BaseModel):
    total_nodes: int
    active_nodes: int
    pending_messages: int
    total_messages: int
    uptime_seconds: float
    queued_tasks: int = 0
    running_tasks: int = 0
    budget_used_usd: float = 0
    budget_remaining_usd: float = 100.0

class HealthResponse(BaseModel):
    status: str  # "healthy" | "degraded" | "unhealthy"
    sdk: bool
    peers: bool
    agentmeet: bool
    mesh_nodes: int
    queued_tasks: int
    uptime_seconds: float
    timestamp: str
```

## 4. Endpoint Design

### 4.1 Node Lifecycle — `/api/v1/nodes`

| Method | Path | Description | Returns |
|--------|------|-------------|---------|
| `GET` | `/nodes` | List all nodes (optional `?status=active`) | `list[NodeResponse]` |
| `GET` | `/nodes/{node_id}` | Get single node | `NodeResponse` |
| `POST` | `/nodes` | Register a node (no spawn) | `NodeResponse` |
| `POST` | `/nodes/{node_id}/spawn` | Spawn node with task → returns `task_id` | `TaskResponse` |
| `POST` | `/nodes/{node_id}/wake` | Wake idle node with new prompt | `TaskResponse` |
| `DELETE` | `/nodes/{node_id}` | Remove node from mesh | `{"removed": true}` |

**Spawn is async**: `POST /nodes/{node_id}/spawn` enqueues the spawn and returns a `task_id` immediately. The client polls `GET /tasks/{task_id}` or subscribes to WebSocket.

```python
@router.post("/nodes/{node_id}/spawn", response_model=TaskResponse)
async def spawn_node(node_id: str, req: SpawnNodeRequest, bg: BackgroundTasks):
    task = task_queue.enqueue(
        task_type="spawn",
        node_id=node_id,
        prompt=req.task,
        role=req.role,
        tools=req.tools,
        model=req.model,
        governed=req.governed,
    )
    bg.add_task(_execute_spawn, task)
    return task.to_response()
```

### 4.2 Task Queue — `/api/v1/tasks`

The task queue decouples submission from execution. Critical because node spawning takes 7-120 seconds.

| Method | Path | Description | Returns |
|--------|------|-------------|---------|
| `POST` | `/tasks` | Submit a task | `TaskResponse` |
| `GET` | `/tasks` | List tasks (`?status=queued&limit=50`) | `list[TaskResponse]` |
| `GET` | `/tasks/{task_id}` | Get task status + output | `TaskResponse` |
| `POST` | `/tasks/{task_id}/cancel` | Cancel a queued/running task | `TaskResponse` |
| `GET` | `/tasks/queue` | Queue depth + estimated wait | `QueueStats` |

**Implementation**: `core/task_queue.py` (new module)

```python
class TaskQueue:
    """Persistent priority queue backed by JSON files.

    Storage: logs/factory/queue/{task_id}.json
    Processing: asyncio worker pool (max 4 concurrent)
    """

    def __init__(self, mesh: NodeMesh, commander: ClaudeCommander,
                 max_concurrent: int = 4,
                 queue_dir: str = "logs/factory/queue"):
        self.mesh = mesh
        self.commander = commander
        self.max_concurrent = max_concurrent  # M4 Max limit
        self.queue_dir = Path(queue_dir)
        self._workers: dict[str, asyncio.Task] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)

    def enqueue(self, task_type: str, prompt: str, **kwargs) -> FactoryTask:
        """Add task to queue. Returns immediately."""
        task_id = hashlib.sha256(f"{time.time()}-{prompt[:50]}".encode()).hexdigest()[:16]
        task = FactoryTask(
            task_id=task_id,
            task_type=task_type,
            prompt=prompt,
            status="queued",
            priority=kwargs.get("priority", 5),
            created_at=time.time(),
            **kwargs,
        )
        self._persist(task)
        return task

    async def process(self, task: FactoryTask):
        """Execute a task through the mesh/commander."""
        async with self._semaphore:
            task.status = "running"
            task.started_at = time.time()
            self._persist(task)

            try:
                if task.task_type == "spawn":
                    node = await self.mesh.spawn_node(
                        node_id=task.node_id,
                        task=task.prompt,
                        role=task.role,
                        tools=task.tools,
                        model=task.model,
                    )
                    task.output = self.mesh._get_last_output(task.node_id)
                    task.status = "completed" if node.status != "error" else "failed"

                elif task.task_type == "command":
                    if task.governed:
                        result = await self.commander.governed_command(task.prompt, tools=task.tools)
                    else:
                        result = await self.commander.command(task.prompt, tools=task.tools)
                    task.output = result.output
                    task.status = "completed" if result.status == "success" else "failed"

                elif task.task_type == "team":
                    result = await self.mesh.spawn_team(task.nodes, parallel=task.parallel)
                    task.output = json.dumps({nid: n.status for nid, n in result.items()})
                    task.status = "completed"

                elif task.task_type == "pipeline":
                    nodes = await self.mesh.pipeline(task.steps)
                    task.output = json.dumps([n.status for n in nodes])
                    task.status = "completed"

            except Exception as e:
                task.status = "failed"
                task.output = str(e)
            finally:
                task.completed_at = time.time()
                task.elapsed_ms = (task.completed_at - task.started_at) * 1000
                self._persist(task)

                # Fire webhook if configured
                if task.callback_url:
                    await self._fire_webhook(task)
```

### 4.3 Messages — `/api/v1/messages`

| Method | Path | Description | Returns |
|--------|------|-------------|---------|
| `POST` | `/messages` | Send message between nodes | `MeshMessage` |
| `POST` | `/messages/broadcast` | Broadcast to all nodes | `MeshMessage` |
| `GET` | `/messages/inbox/{node_id}` | Read node inbox | `list[MeshMessage]` |
| `GET` | `/messages/conversation/{node_a}/{node_b}` | Chat history | `list[MeshMessage]` |

### 4.4 Pipelines & Teams — `/api/v1/pipelines`

| Method | Path | Description | Returns |
|--------|------|-------------|---------|
| `POST` | `/pipelines` | Run sequential pipeline | `TaskResponse` |
| `POST` | `/teams` | Spawn parallel team | `TaskResponse` |

Both return a `task_id` since they're long-running.

### 4.5 Monitoring — `/api/v1/monitor`

| Method | Path | Description | Returns |
|--------|------|-------------|---------|
| `GET` | `/monitor/health` | Full health check (SDK, peers, AgentMeet) | `HealthResponse` |
| `GET` | `/monitor/state` | Mesh state (nodes, messages, queue) | `MeshStateResponse` |
| `GET` | `/monitor/events` | Audit log (`?limit=100&event=spawn`) | `list[MeshEvent]` |
| `GET` | `/monitor/budget` | Budget usage breakdown | `BudgetResponse` |

### 4.6 Sessions — `/api/v1/sessions`

| Method | Path | Description | Returns |
|--------|------|-------------|---------|
| `GET` | `/sessions` | List all persisted sessions | `dict[str, str]` |
| `GET` | `/sessions/discover` | Scan ~/.claude/ for active sessions | `list[SessionInfo]` |
| `POST` | `/sessions/import` | Import discovered sessions as nodes | `{"imported": int}` |

### 4.7 WebSocket — `/ws/events`

Real-time event stream for dashboards and bots.

```python
@app.websocket("/ws/events")
async def websocket_events(ws: WebSocket):
    await ws.accept()
    # Subscribe to mesh events
    async for event in event_bus.subscribe():
        await ws.send_json(event)
```

Events emitted:
- `node.spawned` — node came online
- `node.error` — node failed
- `task.queued` — new task in queue
- `task.started` — task execution began
- `task.completed` — task finished (with output preview)
- `task.failed` — task errored
- `message.sent` — inter-node message
- `mesh.cycle` — daemon cycle completed

## 5. New Module: `core/task_queue.py`

This is the only new module needed. Everything else wraps existing NodeMesh/ClaudeCommander APIs.

```
core/task_queue.py
├── FactoryTask (dataclass)
│   ├── task_id, task_type, prompt, status, priority
│   ├── node_id, role, tools, model, governed
│   ├── nodes (for team), steps (for pipeline)
│   ├── callback_url, output, elapsed_ms
│   └── created_at, started_at, completed_at
├── TaskQueue
│   ├── enqueue() → FactoryTask
│   ├── process() → updates task in-place
│   ├── get(task_id) → FactoryTask
│   ├── list(status, limit) → list[FactoryTask]
│   ├── cancel(task_id) → bool
│   ├── queue_stats() → QueueStats
│   └── _fire_webhook(task) → sends POST to callback_url
└── EventBus
    ├── emit(event_type, data)
    ├── subscribe() → AsyncIterator[dict]
    └── history(limit) → list[dict]
```

## 6. FastAPI App Structure

```
api/
├── __init__.py
├── app.py              ← FastAPI app, lifespan, CORS, middleware
├── deps.py             ← Dependency injection (mesh, commander, queue)
├── routers/
│   ├── nodes.py        ← /api/v1/nodes/*
│   ├── tasks.py        ← /api/v1/tasks/*
│   ├── messages.py     ← /api/v1/messages/*
│   ├── pipelines.py    ← /api/v1/pipelines/* + /api/v1/teams/*
│   ├── monitor.py      ← /api/v1/monitor/*
│   ├── sessions.py     ← /api/v1/sessions/*
│   └── ws.py           ← /ws/events
└── models.py           ← All Pydantic models from §3
```

### `api/app.py` skeleton:

```python
from fastapi import FastAPI
from contextlib import asynccontextmanager
from core.node_mesh import NodeMesh
from core.claude_commander import ClaudeCommander
from core.task_queue import TaskQueue

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: init mesh + commander + queue worker
    mesh = NodeMesh(cwd="/Users/jquiceva/equipo de agentes")
    commander = ClaudeCommander(cwd="/Users/jquiceva/equipo de agentes")
    queue = TaskQueue(mesh=mesh, commander=commander, max_concurrent=4)

    app.state.mesh = mesh
    app.state.commander = commander
    app.state.queue = queue

    # Start queue worker
    worker = asyncio.create_task(queue.run_worker())

    yield

    # Shutdown
    worker.cancel()

app = FastAPI(
    title="DOF Software Factory",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow dashboard
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], ...)

# Mount routers
app.include_router(nodes_router, prefix="/api/v1")
app.include_router(tasks_router, prefix="/api/v1")
app.include_router(messages_router, prefix="/api/v1")
app.include_router(pipelines_router, prefix="/api/v1")
app.include_router(monitor_router, prefix="/api/v1")
app.include_router(sessions_router, prefix="/api/v1")
app.include_router(ws_router)
```

## 7. Security & Auth

For local-first operation (M4 Max, single user):

| Layer | Mechanism |
|-------|-----------|
| **API Key** | `X-Factory-Key` header, stored in `.env` as `FACTORY_API_KEY` |
| **Rate limiting** | 60 req/min per key (SlowAPI) |
| **Governance** | All commands pass through `governed_command()` by default |
| **Budget ceiling** | Hard $100 cap, tracked per-task |
| **Output sanitization** | Strip API keys, wallet keys from outputs |
| **CORS** | Localhost + Vercel dashboard domain only |

For production/multi-user (future):
- JWT auth with scopes (`nodes:read`, `nodes:spawn`, `tasks:write`, `admin`)
- Webhook signature verification (HMAC-SHA256)

## 8. Integration Points

### 8.1 Telegram Bot → Factory API
```python
# In interfaces/telegram_bot.py
# Replace direct ClaudeCommander calls with HTTP:
async def handle_claude_command(update, context):
    resp = await httpx.post("http://localhost:8420/api/v1/tasks", json={
        "prompt": update.message.text,
        "governed": True,
        "callback_url": f"http://localhost:8443/telegram/webhook/{chat_id}"
    })
    task = resp.json()
    await update.message.reply_text(f"⏳ Task queued: {task['task_id']}")
```

### 8.2 Dashboard → Factory API
The existing Next.js dashboard (port 3000) can poll `/monitor/state` and subscribe to `/ws/events` for real-time updates.

### 8.3 CI/CD → Factory API
```bash
# In GitHub Actions or local scripts:
curl -X POST http://localhost:8420/api/v1/nodes/guardian/spawn \
  -H "X-Factory-Key: $FACTORY_KEY" \
  -d '{"task": "Run full test suite and security audit", "governed": true}'
```

### 8.4 Mesh Daemon Integration
The existing `run_mesh()` daemon continues running. The Factory API reads the same `logs/mesh/` files, providing a read/write HTTP interface on top.

## 9. Concurrency Constraints

| Resource | Limit | Rationale |
|----------|-------|-----------|
| Concurrent spawns | 4 | M4 Max 36GB — each Claude session ~2-4GB |
| Task queue depth | 100 | Prevent unbounded growth |
| WebSocket clients | 20 | Memory bound |
| Message bus rate | 100 msg/s | JSONL write throughput |
| Budget per task | $10 default | Prevent runaway |

## 10. File Layout Summary

```
equipo-de-agentes/
├── api/                          ← NEW: FastAPI app
│   ├── __init__.py
│   ├── app.py
│   ├── deps.py
│   ├── models.py
│   └── routers/
│       ├── nodes.py
│       ├── tasks.py
│       ├── messages.py
│       ├── pipelines.py
│       ├── monitor.py
│       ├── sessions.py
│       └── ws.py
├── core/
│   ├── node_mesh.py              ← EXISTING (no changes)
│   ├── claude_commander.py       ← EXISTING (no changes)
│   └── task_queue.py             ← NEW: task queue + event bus
├── logs/
│   ├── mesh/                     ← EXISTING mesh logs
│   └── factory/                  ← NEW: factory-specific logs
│       └── queue/                ← task JSON files
└── scripts/
    └── factory_server.py         ← NEW: uvicorn launcher
```

## 11. Launch Command

```bash
# Start the Software Factory
uvicorn api.app:app --host 0.0.0.0 --port 8420 --reload

# Or via script:
python3 scripts/factory_server.py --port 8420 --workers 1
```

Port **8420** chosen to avoid conflicts with: dashboard (3000), peers broker (7899), Telegram webhook (8443).

## 12. Implementation Priority

| Phase | What | Effort | Depends on |
|-------|------|--------|------------|
| **P0** | `core/task_queue.py` + `api/app.py` + nodes router | 2h | — |
| **P1** | tasks + messages + monitor routers | 2h | P0 |
| **P2** | WebSocket events + EventBus | 1h | P1 |
| **P3** | pipelines + teams routers | 1h | P1 |
| **P4** | Auth (API key) + rate limiting | 1h | P0 |
| **P5** | Telegram integration refactor | 2h | P1 |
| **P6** | Dashboard WebSocket integration | 2h | P2 |

**Total estimated: ~11 hours** for full implementation.

---

*Designed by architect node. Ready for guardian security review and commander approval.*
