#!/usr/bin/env python3
"""
DOF MCP Server — Deterministic Observability Framework as MCP tools.

Exposes DOF governance functions via Model Context Protocol (JSON-RPC 2.0
over stdio).  Compatible with Claude Desktop, Cursor, Windsurf, and any
MCP-compatible client.

15 tools:
  Governance: dof_verify_governance, dof_verify_ast, dof_run_z3
  Memory:     dof_memory_add, dof_memory_query, dof_memory_snapshot
  Metrics:    dof_get_metrics, dof_create_attestation
  Identity:   dof_oags_identity, dof_conformance_check
  Mesh:       mesh_send_task, mesh_broadcast, mesh_route_smart,
              mesh_read_inbox, mesh_consensus

3 resources:
  dof://constitution, dof://metrics/latest, dof://memory/stats

Usage:
    python mcp_server.py          # stdio transport (MCP standard)
    python mcp_server.py --list   # list available tools
"""

import json
import os
import sys

from dof import __version__ as DOF_VERSION
import time
import tempfile
import logging

logger = logging.getLogger("mcp_server")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)


# ─────────────────────────────────────────────────────────────────────
# Tool implementations
# ─────────────────────────────────────────────────────────────────────

def tool_verify_governance(params: dict) -> dict:
    """Verify output text against DOF constitutional governance rules."""
    from core.governance import ConstitutionEnforcer
    output_text = params.get("output_text", "")
    enforcer = ConstitutionEnforcer()
    result = enforcer.check(output_text)
    return {
        "status": "pass" if result.passed else "fail",
        "hard_violations": [v for v in result.violations if not v.startswith("[AST")],
        "soft_violations": result.warnings,
        "score": result.score,
    }


def tool_verify_ast(params: dict) -> dict:
    """Verify Python code against AST security rules."""
    from core.ast_verifier import ASTVerifier
    code = params.get("code", "")
    verifier = ASTVerifier()
    result = verifier.verify(code)
    categories = {}
    for v in result.violations:
        cat = v.get("rule_id", "unknown")
        categories[cat] = categories.get(cat, 0) + 1
    return {
        "score": result.score,
        "passed": result.passed,
        "violations": result.violations,
        "categories": categories,
    }


def tool_run_z3(params: dict) -> dict:
    """Run Z3 formal verification of DOF invariants."""
    from core.z3_verifier import Z3Verifier
    from dataclasses import asdict
    verifier = Z3Verifier()
    start = time.time()
    results = verifier.verify_all()
    elapsed_ms = (time.time() - start) * 1000
    theorems = []
    for r in results:
        d = asdict(r)
        theorems.append({
            "theorem_name": d["theorem_name"],
            "result": d["result"],
            "description": d["description"],
            "proof_time_ms": d["proof_time_ms"],
        })
    return {
        "theorems": theorems,
        "all_verified": all(r.result == "VERIFIED" for r in results),
        "elapsed_ms": round(elapsed_ms, 1),
        "count": len(results),
    }


def tool_memory_add(params: dict) -> dict:
    """Add a governed memory entry."""
    from core.memory_governance import GovernedMemoryStore
    content = params.get("content", "")
    category = params.get("category", "")
    metadata = params.get("metadata", {})
    store = GovernedMemoryStore()
    entry = store.add(content=content, category=category, metadata=metadata)
    return {
        "memory_id": entry.id,
        "status": entry.governance_status,
        "category": entry.category,
        "relevance_score": entry.relevance_score,
    }


def tool_memory_query(params: dict) -> dict:
    """Query governed memory store."""
    from core.memory_governance import GovernedMemoryStore
    query = params.get("query", "")
    category = params.get("category", "")
    store = GovernedMemoryStore()
    results = store.query(query=query, category=category)
    entries = []
    for e in results[:20]:  # limit to 20
        entries.append({
            "memory_id": e.id,
            "content": e.content[:500],
            "category": e.category,
            "governance_status": e.governance_status,
            "relevance_score": e.relevance_score,
        })
    return {"results": entries, "count": len(results)}


def tool_memory_snapshot(params: dict) -> dict:
    """Get memory state at a specific point in time."""
    from core.memory_governance import GovernedMemoryStore, TemporalGraph
    from datetime import datetime
    as_of_str = params.get("as_of", "")
    store = GovernedMemoryStore()
    graph = TemporalGraph(store)
    if as_of_str:
        as_of = datetime.fromisoformat(as_of_str)
    else:
        as_of = datetime.now()
    memories = graph.snapshot(as_of)
    entries = []
    for e in memories[:50]:
        entries.append({
            "memory_id": e.id,
            "content": e.content[:300],
            "category": e.category,
            "governance_status": e.governance_status,
        })
    return {"memories": entries, "count": len(memories), "as_of": as_of.isoformat()}


def tool_get_metrics(params: dict) -> dict:
    """Compute DOF derived metrics (SS, GCR, PFI, RP, SSR)."""
    from core.observability import RunTrace, compute_derived_metrics, get_session_id
    run_trace_path = params.get("run_trace_path", "")
    if run_trace_path and os.path.exists(run_trace_path):
        with open(run_trace_path, "r") as f:
            data = json.load(f)
        # Reconstruct RunTrace from JSON
        trace = RunTrace(
            run_id=data.get("run_id", ""),
            session_id=data.get("session_id", ""),
            crew_name=data.get("crew_name", ""),
            mode=data.get("mode", ""),
            timestamp_start=data.get("timestamp_start", ""),
            start_epoch=data.get("start_epoch", 0),
            deterministic=data.get("deterministic", False),
            input_text=data.get("input_text", ""),
            input_hash=data.get("input_hash", ""),
        )
        metrics = compute_derived_metrics(trace)
    else:
        # Return default metrics
        metrics = {
            "stability_score": 0.0,
            "governance_compliance_rate": 1.0,
            "provider_failure_index": 0.0,
            "recovery_probability": 0.0,
            "supervisor_score_reliability": 0.0,
        }
    return {
        "SS": metrics.get("stability_score", 0.0),
        "GCR": metrics.get("governance_compliance_rate", 1.0),
        "PFI": metrics.get("provider_failure_index", 0.0),
        "RP": metrics.get("recovery_probability", 0.0),
        "SSR": metrics.get("supervisor_score_reliability", 0.0),
    }


def tool_create_attestation(params: dict) -> dict:
    """Create an ERC-8004 attestation certificate."""
    from core.oracle_bridge import OracleBridge, CertificateSigner
    from core.oags_bridge import OAGSIdentity
    task_id = params.get("task_id", "")
    metrics = params.get("metrics", {})
    tmpdir = tempfile.mkdtemp()
    signer = CertificateSigner(key_path=os.path.join(tmpdir, "mcp_key.json"))
    identity = OAGSIdentity()
    bridge = OracleBridge(signer, identity)
    cert = bridge.create_attestation(task_id=task_id, metrics=metrics)
    return {
        "certificate_hash": cert.certificate_hash,
        "governance_status": cert.governance_status,
        "should_publish": bridge.should_publish(cert),
        "z3_verified": cert.z3_verified,
        "agent_identity": cert.agent_identity,
    }


def tool_oags_identity(params: dict) -> dict:
    """Compute deterministic OAGS agent identity."""
    from core.oags_bridge import OAGSIdentity
    model = params.get("model", "")
    tools = params.get("tools", [])
    identity = OAGSIdentity(model=model, tools=tools)
    card = identity.get_agent_card()
    return {
        "identity_hash": card["identity_hash"],
        "constitution_hash": card["constitution_hash"],
        "agent_card": card,
    }


def tool_conformance_check(params: dict) -> dict:
    """Validate OAGS conformance at all 3 levels."""
    from core.oags_bridge import OAGSPolicyBridge
    result = OAGSPolicyBridge.validate_conformance(level=3)
    return {
        "level_1": result["level_1"],
        "level_2": result["level_2"],
        "level_3": result["level_3"],
        "max_level": result["max_level_passed"],
    }


# ─────────────────────────────────────────────────────────────────────
# Mesh Communication Tools (Agent Teams ↔ DOF Mesh bridge)
# ─────────────────────────────────────────────────────────────────────

def _get_mesh():
    """Lazy-load NodeMesh singleton."""
    from core.node_mesh import NodeMesh
    return NodeMesh()


def tool_mesh_send_task(params: dict) -> dict:
    """Send a task to a specific mesh node and return its response."""
    node_id = params.get("node_id", "")
    task = params.get("task", "")
    task_type = params.get("task_type", "task")

    if not node_id or not task:
        return {"error": "node_id and task are required"}

    mesh = _get_mesh()

    # Send message via MessageBus
    msg_id = mesh.send_message(
        from_node="agent-teams-bridge",
        to_node=node_id,
        content=task,
        msg_type=task_type,
    )

    # Check if node is registered
    nodes = mesh.list_nodes()
    node_info = None
    for n in nodes:
        if n.node_id == node_id:
            node_info = {
                "node_id": n.node_id,
                "role": n.role,
                "status": n.status,
            }
            break

    return {
        "msg_id": msg_id,
        "to_node": node_id,
        "task_type": task_type,
        "node_info": node_info or {"error": f"Node {node_id} not in registry"},
        "status": "delivered",
    }


def tool_mesh_broadcast(params: dict) -> dict:
    """Broadcast a message to ALL active mesh nodes."""
    content = params.get("content", "")
    task_type = params.get("task_type", "query")

    if not content:
        return {"error": "content is required"}

    mesh = _get_mesh()
    msg_id = mesh.broadcast(
        from_node="agent-teams-bridge",
        content=content,
    )

    nodes = mesh.list_nodes()
    node_ids = [n.node_id for n in nodes if n.status != "error"]

    return {
        "msg_id": msg_id,
        "broadcast_to": node_ids,
        "node_count": len(node_ids),
        "status": "broadcast_sent",
    }


def tool_mesh_route_smart(params: dict) -> dict:
    """Use MeshRouterV2 to find the best node for a task type, then send it."""
    task_type = params.get("task_type", "")
    task = params.get("task", "")

    if not task_type or not task:
        return {"error": "task_type and task are required"}

    try:
        from core.mesh_router_v2 import MeshRouterV2
        router = MeshRouterV2()
        best_node = router.route(task_type)
    except Exception as e:
        return {"error": f"Router failed: {e}", "fallback": "use mesh_send_task directly"}

    if not best_node:
        return {"error": f"No suitable node for task_type={task_type}"}

    # Send to the best node
    mesh = _get_mesh()
    msg_id = mesh.send_message(
        from_node="agent-teams-bridge",
        to_node=best_node,
        content=task,
        msg_type="task",
    )

    return {
        "routed_to": best_node,
        "task_type": task_type,
        "msg_id": msg_id,
        "routing": "MeshRouterV2 (specialty + latency + load)",
        "status": "routed_and_sent",
    }


def tool_mesh_read_inbox(params: dict) -> dict:
    """Read pending messages from a node's inbox."""
    node_id = params.get("node_id", "agent-teams-bridge")
    mark_read = params.get("mark_read", True)

    mesh = _get_mesh()
    messages = mesh.read_inbox(node_id, mark_read=mark_read)

    results = []
    for msg in messages[:20]:  # limit to 20
        results.append({
            "msg_id": getattr(msg, "msg_id", ""),
            "from_node": getattr(msg, "from_node", ""),
            "content": str(getattr(msg, "content", ""))[:1000],
            "msg_type": getattr(msg, "msg_type", ""),
            "timestamp": str(getattr(msg, "timestamp", "")),
        })

    return {
        "node_id": node_id,
        "messages": results,
        "count": len(results),
        "total_unread": len(messages),
    }


def tool_mesh_consensus(params: dict) -> dict:
    """Send a question to N nodes and compare responses for consensus."""
    question = params.get("question", "")
    node_ids = params.get("node_ids", [])
    min_nodes = params.get("min_nodes", 3)

    if not question:
        return {"error": "question is required"}

    mesh = _get_mesh()

    # If no specific nodes, pick from active nodes
    if not node_ids:
        nodes = mesh.list_nodes()
        active = [n.node_id for n in nodes if n.status != "error"]
        node_ids = active[:min_nodes]

    if len(node_ids) < 2:
        return {"error": f"Need at least 2 nodes for consensus, found {len(node_ids)}"}

    # Send to all selected nodes
    sent = []
    for nid in node_ids:
        msg_id = mesh.send_message(
            from_node="agent-teams-bridge",
            to_node=nid,
            content=question,
            msg_type="query",
        )
        sent.append({"node_id": nid, "msg_id": msg_id})

    # Apply governance check to the question itself
    from core.governance import ConstitutionEnforcer
    enforcer = ConstitutionEnforcer()
    gov_check = enforcer.check(question)

    return {
        "question": question[:200],
        "sent_to": sent,
        "node_count": len(sent),
        "governance_pre_check": {
            "passed": gov_check.passed,
            "score": gov_check.score,
        },
        "status": "consensus_initiated",
        "next_step": "Use mesh_read_inbox to collect responses, then compare",
    }


# ─────────────────────────────────────────────────────────────────────
# Resource implementations
# ─────────────────────────────────────────────────────────────────────

def resource_constitution() -> dict:
    """Return the DOF constitution as structured data."""
    import yaml
    path = os.path.join(BASE_DIR, "dof.constitution.yml")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return {"uri": "dof://constitution", "data": data}
    except Exception as e:
        return {"uri": "dof://constitution", "error": str(e)}


def resource_metrics_latest() -> dict:
    """Return the latest computed metrics."""
    metrics = tool_get_metrics({})
    return {"uri": "dof://metrics/latest", "data": metrics}


def resource_memory_stats() -> dict:
    """Return memory store statistics."""
    from core.memory_governance import GovernedMemoryStore
    try:
        store = GovernedMemoryStore()
        stats = store.get_stats()
        return {"uri": "dof://memory/stats", "data": stats}
    except Exception as e:
        return {"uri": "dof://memory/stats", "error": str(e)}


# ─────────────────────────────────────────────────────────────────────
# Tool & Resource registry
# ─────────────────────────────────────────────────────────────────────

TOOLS = {
    "dof_verify_governance": {
        "handler": tool_verify_governance,
        "description": "Verify output text against DOF constitutional governance rules (hard + soft)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "output_text": {"type": "string", "description": "The text to verify"}
            },
            "required": ["output_text"],
        },
    },
    "dof_verify_ast": {
        "handler": tool_verify_ast,
        "description": "Verify Python code against AST security rules (blocked imports, unsafe calls, secrets)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python source code to verify"}
            },
            "required": ["code"],
        },
    },
    "dof_run_z3": {
        "handler": tool_run_z3,
        "description": "Run Z3 SMT formal verification of DOF invariants (4 theorems)",
        "inputSchema": {"type": "object", "properties": {}},
    },
    "dof_memory_add": {
        "handler": tool_memory_add,
        "description": "Add a governed memory entry with constitutional governance checks",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Memory content"},
                "category": {"type": "string", "description": "Category: knowledge, preferences, context, decisions, errors"},
                "metadata": {"type": "object", "description": "Optional metadata dict"},
            },
            "required": ["content"],
        },
    },
    "dof_memory_query": {
        "handler": tool_memory_query,
        "description": "Query the governed memory store with optional category filter",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "category": {"type": "string", "description": "Filter by category"},
            },
        },
    },
    "dof_memory_snapshot": {
        "handler": tool_memory_snapshot,
        "description": "Get memory state at a specific point in time (bi-temporal query)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "as_of": {"type": "string", "description": "ISO datetime for point-in-time query"},
            },
        },
    },
    "dof_get_metrics": {
        "handler": tool_get_metrics,
        "description": "Compute DOF derived metrics: SS, GCR, PFI, RP, SSR",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_trace_path": {"type": "string", "description": "Optional path to RunTrace JSON"},
            },
        },
    },
    "dof_create_attestation": {
        "handler": tool_create_attestation,
        "description": "Create an ERC-8004 attestation certificate for governance metrics",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Unique task identifier"},
                "metrics": {"type": "object", "description": "Dict with SS, GCR, PFI, RP, SSR values"},
            },
            "required": ["task_id", "metrics"],
        },
    },
    "dof_oags_identity": {
        "handler": tool_oags_identity,
        "description": "Compute deterministic OAGS agent identity via BLAKE3 hash",
        "inputSchema": {
            "type": "object",
            "properties": {
                "model": {"type": "string", "description": "Model name"},
                "tools": {"type": "array", "items": {"type": "string"}, "description": "List of tool names"},
            },
        },
    },
    "dof_conformance_check": {
        "handler": tool_conformance_check,
        "description": "Validate OAGS conformance at Levels 1-3 (declarative, runtime, attestation)",
        "inputSchema": {"type": "object", "properties": {}},
    },
    # ── Mesh Communication Tools (Agent Teams ↔ DOF Mesh) ──
    "mesh_send_task": {
        "handler": tool_mesh_send_task,
        "description": "Send a task to a specific DOF mesh node (DeepSeek, SambaNova, MiMo, Kimi, etc.)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node_id": {"type": "string", "description": "Target mesh node ID"},
                "task": {"type": "string", "description": "Task prompt to send"},
                "task_type": {"type": "string", "description": "Type: task, query, alert, sync (default: task)"},
            },
            "required": ["node_id", "task"],
        },
    },
    "mesh_broadcast": {
        "handler": tool_mesh_broadcast,
        "description": "Broadcast a message to ALL active mesh nodes simultaneously",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Message to broadcast"},
                "task_type": {"type": "string", "description": "Type: task, query, alert (default: query)"},
            },
            "required": ["content"],
        },
    },
    "mesh_route_smart": {
        "handler": tool_mesh_route_smart,
        "description": "Smart-route a task to the best mesh node using MeshRouterV2 (specialty + latency + load)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_type": {"type": "string", "description": "Type: code, test, security, research, docs, consensus"},
                "task": {"type": "string", "description": "Task prompt to send"},
            },
            "required": ["task_type", "task"],
        },
    },
    "mesh_read_inbox": {
        "handler": tool_mesh_read_inbox,
        "description": "Read pending messages from a mesh node inbox (responses, results, alerts)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node_id": {"type": "string", "description": "Node ID to read inbox (default: agent-teams-bridge)"},
                "mark_read": {"type": "boolean", "description": "Mark messages as read (default: true)"},
            },
        },
    },
    "mesh_consensus": {
        "handler": tool_mesh_consensus,
        "description": "Send a question to multiple nodes for consensus — governance pre-check included",
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "Question to send for multi-node consensus"},
                "node_ids": {"type": "array", "items": {"type": "string"}, "description": "Specific nodes (optional, auto-selects if empty)"},
                "min_nodes": {"type": "integer", "description": "Minimum nodes for consensus (default: 3)"},
            },
            "required": ["question"],
        },
    },
}

RESOURCES = {
    "dof://constitution": {
        "handler": resource_constitution,
        "name": "DOF Constitution",
        "description": "The DOF governance constitution (dof.constitution.yml)",
        "mimeType": "application/json",
    },
    "dof://metrics/latest": {
        "handler": resource_metrics_latest,
        "name": "Latest Metrics",
        "description": "Latest computed DOF metrics (SS, GCR, PFI, RP, SSR)",
        "mimeType": "application/json",
    },
    "dof://memory/stats": {
        "handler": resource_memory_stats,
        "name": "Memory Stats",
        "description": "Governed memory store statistics",
        "mimeType": "application/json",
    },
}


# ─────────────────────────────────────────────────────────────────────
# MCP JSON-RPC 2.0 Protocol (stdlib-only implementation)
# ─────────────────────────────────────────────────────────────────────

SERVER_INFO = {
    "name": "dof-governance",
    "version": DOF_VERSION,
}

CAPABILITIES = {
    "tools": {},
    "resources": {},
}


def handle_initialize(params: dict) -> dict:
    """Handle MCP initialize request."""
    return {
        "protocolVersion": "2024-11-05",
        "capabilities": CAPABILITIES,
        "serverInfo": SERVER_INFO,
    }


def handle_tools_list(params: dict) -> dict:
    """Handle tools/list request."""
    tools = []
    for name, spec in TOOLS.items():
        tools.append({
            "name": name,
            "description": spec["description"],
            "inputSchema": spec["inputSchema"],
        })
    return {"tools": tools}


_MESH_TOOL_NAMES = {"mesh_send_task", "mesh_broadcast", "mesh_route_smart", "mesh_read_inbox", "mesh_consensus"}


def handle_tools_call(params: dict) -> dict:
    """Handle tools/call request. Mesh tools get DOF governance post-check."""
    tool_name = params.get("name", "")
    arguments = params.get("arguments", {})
    if tool_name not in TOOLS:
        return {
            "content": [{"type": "text", "text": json.dumps({"error": f"Unknown tool: {tool_name}"})}],
            "isError": True,
        }
    try:
        result = TOOLS[tool_name]["handler"](arguments)
        # Governance post-check for mesh tools
        if tool_name in _MESH_TOOL_NAMES:
            try:
                from core.governance import ConstitutionEnforcer
                enforcer = ConstitutionEnforcer()
                gov = enforcer.check(json.dumps(result, default=str))
                result["_dof_governance"] = {
                    "checked": True,
                    "passed": gov.passed,
                    "score": gov.score,
                    "violations": len(gov.violations),
                    "warnings": len(gov.warnings),
                }
            except Exception as ge:
                result["_dof_governance"] = {"checked": False, "error": str(ge)}
        return {
            "content": [{"type": "text", "text": json.dumps(result, default=str)}],
            "isError": False,
        }
    except Exception as e:
        return {
            "content": [{"type": "text", "text": json.dumps({"error": str(e)})}],
            "isError": True,
        }


def handle_resources_list(params: dict) -> dict:
    """Handle resources/list request."""
    resources = []
    for uri, spec in RESOURCES.items():
        resources.append({
            "uri": uri,
            "name": spec["name"],
            "description": spec["description"],
            "mimeType": spec["mimeType"],
        })
    return {"resources": resources}


def handle_resources_read(params: dict) -> dict:
    """Handle resources/read request."""
    uri = params.get("uri", "")
    if uri not in RESOURCES:
        return {"contents": [{"uri": uri, "text": json.dumps({"error": f"Unknown resource: {uri}"})}]}
    try:
        result = RESOURCES[uri]["handler"]()
        return {"contents": [{"uri": uri, "text": json.dumps(result.get("data", result), default=str)}]}
    except Exception as e:
        return {"contents": [{"uri": uri, "text": json.dumps({"error": str(e)})}]}


# JSON-RPC method dispatch
METHODS = {
    "initialize": handle_initialize,
    "tools/list": handle_tools_list,
    "tools/call": handle_tools_call,
    "resources/list": handle_resources_list,
    "resources/read": handle_resources_read,
}


def handle_request(request: dict) -> dict | None:
    """Process a single JSON-RPC 2.0 request. Returns response or None for notifications."""
    method = request.get("method", "")
    params = request.get("params", {})
    req_id = request.get("id")

    # Notifications (no id) — acknowledge silently
    if req_id is None:
        if method == "notifications/initialized":
            return None  # no response for notifications
        return None

    if method not in METHODS:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }

    try:
        result = METHODS[method](params)
        return {"jsonrpc": "2.0", "id": req_id, "result": result}
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32603, "message": str(e)},
        }


def run_stdio():
    """Run the MCP server on stdio (JSON-RPC 2.0 over stdin/stdout)."""
    # Redirect logging to stderr so it doesn't interfere with JSON-RPC
    logging.basicConfig(stream=sys.stderr, level=logging.WARNING)

    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue

            request = json.loads(line)
            response = handle_request(request)

            if response is not None:
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()

        except json.JSONDecodeError:
            error_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error"},
            }
            sys.stdout.write(json.dumps(error_resp) + "\n")
            sys.stdout.flush()
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Server error: {e}")
            continue


def list_tools():
    """Print available tools to stdout."""
    print(f"\nDOF MCP Server — {SERVER_INFO['name']} v{SERVER_INFO['version']}")
    print(f"\n{'='*60}")
    print(f"{'TOOLS':^60}")
    print(f"{'='*60}")
    for name, spec in TOOLS.items():
        print(f"\n  {name}")
        print(f"    {spec['description']}")
        required = spec['inputSchema'].get('required', [])
        props = spec['inputSchema'].get('properties', {})
        if props:
            for pname, pspec in props.items():
                req = " (required)" if pname in required else ""
                print(f"    - {pname}: {pspec.get('type', '?')}{req}")

    print(f"\n{'='*60}")
    print(f"{'RESOURCES':^60}")
    print(f"{'='*60}")
    for uri, spec in RESOURCES.items():
        print(f"\n  {uri}")
        print(f"    {spec['description']}")

    print(f"\n{len(TOOLS)} tools, {len(RESOURCES)} resources")


if __name__ == "__main__":
    if "--list" in sys.argv:
        list_tools()
    else:
        run_stdio()
