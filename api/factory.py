"""
DOF Software Factory API — Node Mesh + Commander endpoints.

Turns the DOF agent mesh into a programmable HTTP platform.
Any client (Telegram, dashboard, CI/CD) can spawn nodes, queue tasks,
monitor execution, and read results via REST.

Usage:
    # Mount on existing server:
    from api.factory import factory_router
    app.include_router(factory_router, prefix="/api/v1")

    # Or run standalone:
    uvicorn api.factory:app --host 0.0.0.0 --port 8001
"""

import asyncio
import json
import os
import sys
import time
import uuid
import logging
from datetime import datetime
from typing import Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

logger = logging.getLogger("dof.factory")

try:
    from fastapi import FastAPI, HTTPException, BackgroundTasks
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel, Field
except ImportError:
    raise ImportError("pip install fastapi uvicorn")

from core.node_mesh import NodeMesh
from core.claude_commander import ClaudeCommander

# ─────────────────────────────────────────────────────────────────────
# Pydantic models
# ─────────────────────────────────────────────────────────────────────

class SpawnNodeRequest(BaseModel):
    node_id: str = Field(..., description="Unique node identifier")
    role: str = Field(..., description="Node role description")
    task: str = Field(..., description="Task/prompt for the node")
    model: str = Field("claude-sonnet-4-6", description="Claude model to use")
    tools: list[str] = Field(default_factory=list, description="Tools available to node")

class QueueTaskRequest(BaseModel):
    prompt: str = Field(..., description="Task prompt")
    model: str = Field("claude-sonnet-4-6")
    max_turns: int = Field(10)

class SpawnTeamRequest(BaseModel):
    nodes: dict[str, str] = Field(..., description="Dict of node_id → task prompt")
    model: str = Field("claude-sonnet-4-6")
    parallel: bool = Field(True)

class SendMessageRequest(BaseModel):
    from_node: str
    to_node: str
    content: str

class PipelineRequest(BaseModel):
    steps: list[dict] = Field(..., description="List of {node_id, task} steps")
    model: str = Field("claude-sonnet-4-6")


# ─────────────────────────────────────────────────────────────────────
# In-memory task registry (replace with Redis in production)
# ─────────────────────────────────────────────────────────────────────

_tasks: dict[str, dict] = {}  # task_id → {status, result, created_at, ...}
_mesh = NodeMesh()


def _new_task(kind: str, params: dict) -> str:
    task_id = str(uuid.uuid4())[:8]
    _tasks[task_id] = {
        "task_id": task_id,
        "kind": kind,
        "params": params,
        "status": "queued",
        "result": None,
        "error": None,
        "created_at": datetime.utcnow().isoformat(),
        "completed_at": None,
    }
    return task_id


# ─────────────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────────────

from fastapi import APIRouter
factory_router = APIRouter(tags=["factory"])


# ── Mesh status ──────────────────────────────────────────────────────

@factory_router.get("/mesh/status")
async def mesh_status():
    """Get current state of the node mesh."""
    nodes = {}
    for nid, node in _mesh.nodes.items():
        nodes[nid] = {
            "id": nid,
            "role": node.get("role", "unknown"),
            "status": node.get("status", "idle"),
            "model": node.get("model", "?"),
            "last_active": node.get("last_active"),
        }
    return {
        "node_count": len(nodes),
        "nodes": nodes,
        "task_count": len(_tasks),
        "timestamp": datetime.utcnow().isoformat(),
    }


# ── Node lifecycle ───────────────────────────────────────────────────

@factory_router.get("/nodes")
async def list_nodes():
    """List all registered nodes."""
    return {"nodes": list(_mesh.nodes.keys()), "count": len(_mesh.nodes)}


@factory_router.post("/nodes/spawn")
async def spawn_node(req: SpawnNodeRequest, background_tasks: BackgroundTasks):
    """Spawn a single node with a task. Returns task_id immediately."""
    task_id = _new_task("spawn_node", req.dict())

    async def _run():
        try:
            _tasks[task_id]["status"] = "running"
            _mesh.register_node(req.node_id, req.role, tools=req.tools, model=req.model)
            result = await _mesh.spawn_node(req.node_id, req.task)
            _tasks[task_id].update({"status": "completed", "result": result,
                                    "completed_at": datetime.utcnow().isoformat()})
        except Exception as e:
            _tasks[task_id].update({"status": "failed", "error": str(e),
                                    "completed_at": datetime.utcnow().isoformat()})
            logger.error(f"spawn_node {req.node_id} failed: {e}")

    background_tasks.add_task(_run)
    return {"task_id": task_id, "node_id": req.node_id, "status": "queued"}


@factory_router.delete("/nodes/{node_id}")
async def remove_node(node_id: str):
    """Unregister a node from the mesh."""
    if node_id not in _mesh.nodes:
        raise HTTPException(404, f"Node {node_id} not found")
    del _mesh.nodes[node_id]
    return {"removed": node_id}


# ── Team spawn ───────────────────────────────────────────────────────

@factory_router.post("/nodes/spawn-team")
async def spawn_team(req: SpawnTeamRequest, background_tasks: BackgroundTasks):
    """Spawn multiple nodes in parallel. Returns task_id."""
    task_id = _new_task("spawn_team", {"node_count": len(req.nodes)})

    async def _run():
        try:
            _tasks[task_id]["status"] = "running"
            # Register all nodes first
            for nid, task in req.nodes.items():
                _mesh.register_node(nid, f"agent-{nid}", model=req.model)
            results = await _mesh.spawn_team(req.nodes, parallel=req.parallel)
            _tasks[task_id].update({
                "status": "completed",
                "result": {k: bool(v) for k, v in results.items()},
                "completed_at": datetime.utcnow().isoformat(),
            })
        except Exception as e:
            _tasks[task_id].update({"status": "failed", "error": str(e),
                                    "completed_at": datetime.utcnow().isoformat()})

    background_tasks.add_task(_run)
    return {"task_id": task_id, "nodes": list(req.nodes.keys()), "status": "queued"}


# ── Task queue ───────────────────────────────────────────────────────

@factory_router.post("/tasks/queue")
async def queue_task(req: QueueTaskRequest, background_tasks: BackgroundTasks):
    """Queue a single Claude Commander task. Returns task_id immediately."""
    task_id = _new_task("command", {"prompt": req.prompt[:100]})

    async def _run():
        try:
            _tasks[task_id]["status"] = "running"
            commander = ClaudeCommander(model=req.model)
            result = await commander.command(req.prompt)
            _tasks[task_id].update({
                "status": "completed",
                "result": {"output": result.output if hasattr(result, 'output') else str(result),
                           "cost": getattr(result, 'cost_usd', 0)},
                "completed_at": datetime.utcnow().isoformat(),
            })
        except Exception as e:
            _tasks[task_id].update({"status": "failed", "error": str(e),
                                    "completed_at": datetime.utcnow().isoformat()})

    background_tasks.add_task(_run)
    return {"task_id": task_id, "status": "queued"}


@factory_router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Get status and result of a task."""
    if task_id not in _tasks:
        raise HTTPException(404, f"Task {task_id} not found")
    return _tasks[task_id]


@factory_router.get("/tasks")
async def list_tasks(limit: int = 20):
    """List recent tasks."""
    tasks = sorted(_tasks.values(), key=lambda t: t["created_at"], reverse=True)
    return {"tasks": tasks[:limit], "total": len(_tasks)}


# ── Message bus ──────────────────────────────────────────────────────

@factory_router.post("/messages/send")
async def send_message(req: SendMessageRequest):
    """Send a message between nodes via the mesh message bus."""
    _mesh.send_message(req.from_node, req.to_node, req.content)
    return {"sent": True, "from": req.from_node, "to": req.to_node}


@factory_router.get("/messages/inbox/{node_id}")
async def read_inbox(node_id: str):
    """Read messages in a node's inbox."""
    messages = _mesh.read_inbox(node_id)
    return {"node_id": node_id, "messages": messages, "count": len(messages)}


@factory_router.post("/messages/broadcast")
async def broadcast(req: SendMessageRequest):
    """Broadcast a message to all nodes."""
    _mesh.broadcast(req.from_node, req.content)
    return {"broadcast": True, "from": req.from_node, "recipients": len(_mesh.nodes)}


# ── Pipeline ─────────────────────────────────────────────────────────

@factory_router.post("/pipelines/run")
async def run_pipeline(req: PipelineRequest, background_tasks: BackgroundTasks):
    """Run a sequential pipeline where each step's output feeds the next."""
    task_id = _new_task("pipeline", {"steps": len(req.steps)})

    async def _run():
        try:
            _tasks[task_id]["status"] = "running"
            result = await _mesh.pipeline(req.steps)
            _tasks[task_id].update({
                "status": "completed",
                "result": result,
                "completed_at": datetime.utcnow().isoformat(),
            })
        except Exception as e:
            _tasks[task_id].update({"status": "failed", "error": str(e),
                                    "completed_at": datetime.utcnow().isoformat()})

    background_tasks.add_task(_run)
    return {"task_id": task_id, "steps": len(req.steps), "status": "queued"}


# ── Monitor ──────────────────────────────────────────────────────────

@factory_router.get("/monitor/health")
async def health():
    """Factory health check."""
    return {
        "status": "ok",
        "nodes": len(_mesh.nodes),
        "tasks_total": len(_tasks),
        "tasks_running": sum(1 for t in _tasks.values() if t["status"] == "running"),
        "tasks_completed": sum(1 for t in _tasks.values() if t["status"] == "completed"),
        "tasks_failed": sum(1 for t in _tasks.values() if t["status"] == "failed"),
        "timestamp": datetime.utcnow().isoformat(),
    }


@factory_router.get("/monitor/logs")
async def get_logs(lines: int = 50):
    """Get recent daemon cycle logs."""
    log_path = os.path.join(BASE_DIR, "logs", "daemon", "cycles.jsonl")
    if not os.path.exists(log_path):
        return {"logs": [], "message": "No daemon logs yet"}
    with open(log_path) as f:
        raw = f.readlines()
    recent = raw[-lines:]
    parsed = []
    for line in recent:
        try:
            parsed.append(json.loads(line.strip()))
        except Exception:
            parsed.append({"raw": line.strip()})
    return {"logs": parsed, "total_lines": len(raw)}


@factory_router.get("/monitor/mesh-logs")
async def get_mesh_logs(lines: int = 50):
    """Get recent mesh message logs."""
    log_path = os.path.join(BASE_DIR, "logs", "mesh", "messages.jsonl")
    if not os.path.exists(log_path):
        return {"messages": [], "message": "No mesh logs yet"}
    with open(log_path) as f:
        raw = f.readlines()
    recent = raw[-lines:]
    parsed = []
    for line in recent:
        try:
            parsed.append(json.loads(line.strip()))
        except Exception:
            parsed.append({"raw": line.strip()})
    return {"messages": parsed}


# ── Sessions ─────────────────────────────────────────────────────────

@factory_router.get("/sessions")
async def list_sessions():
    """List persisted Claude Commander sessions."""
    sessions_path = os.path.join(BASE_DIR, "logs", "commander", "sessions.json")
    if not os.path.exists(sessions_path):
        return {"sessions": {}}
    with open(sessions_path) as f:
        return {"sessions": json.load(f)}


@factory_router.post("/sessions/discover")
async def discover_sessions():
    """Scan ~/.claude/projects/ and import existing sessions as mesh nodes."""
    discovered = _mesh.discover_sessions()
    _mesh.import_discovered_sessions()
    return {"discovered": discovered, "imported": len(discovered)}


# ─────────────────────────────────────────────────────────────────────
# Standalone app (for development / direct deployment)
# ─────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="DOF Software Factory",
    description="Node Mesh + Claude Commander as HTTP API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(factory_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "name": "DOF Software Factory",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/api/v1/monitor/health",
        "mesh": "/api/v1/mesh/status",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.factory:app", host="0.0.0.0", port=8001, reload=True)
