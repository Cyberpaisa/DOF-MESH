"""
DOF REST API — FastAPI endpoints for all DOF governance functions.

14 endpoints covering governance, AST, Z3, memory, metrics, attestation, OAGS.

Usage:
    python -m api.server                          # default port 8080
    uvicorn api.server:app --host 0.0.0.0 --port 8080
"""

import json
import os
import sys
import time
import logging
from datetime import datetime

logger = logging.getLogger("dof.api")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

try:
    from fastapi import FastAPI, Query, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
except ImportError:
    raise ImportError(
        "FastAPI is required for the REST API. Install with: pip install fastapi uvicorn"
    )

from mcp_server import (
    tool_verify_governance,
    tool_verify_ast,
    tool_run_z3,
    tool_memory_add,
    tool_memory_query,
    tool_memory_snapshot,
    tool_get_metrics,
    tool_create_attestation,
    tool_oags_identity,
    tool_conformance_check,
    resource_constitution,
)


# ─────────────────────────────────────────────────────────────────────
# App setup
# ─────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="DOF Governance API",
    description="Deterministic Observability Framework — REST API for governance, verification, and observability",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_LOG = os.path.join(BASE_DIR, "logs", "api_requests.jsonl")


# ─────────────────────────────────────────────────────────────────────
# Middleware: request logging
# ─────────────────────────────────────────────────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed_ms = (time.time() - start) * 1000

    entry = {
        "timestamp": datetime.now().isoformat(),
        "method": request.method,
        "path": str(request.url.path),
        "status": response.status_code,
        "elapsed_ms": round(elapsed_ms, 1),
    }
    try:
        os.makedirs(os.path.dirname(API_LOG), exist_ok=True)
        with open(API_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass

    return response


# ─────────────────────────────────────────────────────────────────────
# Global error handler
# ─────────────────────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "path": str(request.url.path)},
    )


# ─────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────

@app.get("/api/v1/health")
async def health():
    return {
        "status": "ok",
        "version": "0.1.0",
        "tests": 350,
        "modules": 30,
    }


@app.post("/api/v1/governance/verify")
async def governance_verify(request: Request):
    body = await request.json()
    return tool_verify_governance(body)


@app.post("/api/v1/ast/verify")
async def ast_verify(request: Request):
    body = await request.json()
    return tool_verify_ast(body)


@app.get("/api/v1/z3/verify")
async def z3_verify():
    return tool_run_z3({})


@app.post("/api/v1/memory")
async def memory_add(request: Request):
    body = await request.json()
    return tool_memory_add(body)


@app.get("/api/v1/memory")
async def memory_query(
    query: str = Query(default="", description="Search query"),
    category: str = Query(default="", description="Filter by category"),
):
    return tool_memory_query({"query": query, "category": category})


@app.get("/api/v1/memory/snapshot")
async def memory_snapshot(
    as_of: str = Query(default="", description="ISO datetime for point-in-time query"),
):
    return tool_memory_snapshot({"as_of": as_of})


@app.get("/api/v1/memory/stats")
async def memory_stats():
    from core.memory_governance import GovernedMemoryStore
    try:
        store = GovernedMemoryStore()
        return store.get_stats()
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/v1/metrics")
async def metrics():
    return tool_get_metrics({})


@app.post("/api/v1/attestation")
async def attestation_create(request: Request):
    body = await request.json()
    return tool_create_attestation(body)


@app.get("/api/v1/attestation/history")
async def attestation_history():
    from core.oracle_bridge import AttestationRegistry
    try:
        registry = AttestationRegistry()
        certs = registry._certs
        from dataclasses import asdict
        return {
            "attestations": [asdict(c) for c in certs[-50:]],
            "compliance_rate": registry.get_compliance_rate(),
            "total": len(certs),
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/v1/oags/identity")
async def oags_identity(
    model: str = Query(default="", description="Model name"),
    tools: str = Query(default="", description="Comma-separated tool names"),
):
    tool_list = [t.strip() for t in tools.split(",") if t.strip()] if tools else []
    return tool_oags_identity({"model": model, "tools": tool_list})


@app.get("/api/v1/oags/conformance")
async def oags_conformance():
    return tool_conformance_check({})


@app.get("/api/v1/constitution")
async def constitution():
    result = resource_constitution()
    if "error" in result:
        return JSONResponse(status_code=500, content={"error": result["error"]})
    return result.get("data", {})


# ─────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────

def start_server(host: str = "0.0.0.0", port: int = 8080):
    """Start the API server."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="DOF REST API Server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    start_server(args.host, args.port)
