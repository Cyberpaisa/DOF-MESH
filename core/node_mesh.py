"""
Node Mesh — Red de Nodos Infinitos de Agentes Claude.

Evolución del ClaudeCommander: cada agente es un NODO con sesión persistente
que se comunica con otros nodos a través de un bus de mensajes compartido.

Arquitectura:
    NodeMesh (orquestador)
        ├── NodeRegistry  — registro de todos los nodos activos (sessions.json)
        ├── MessageBus    — cola de mensajes JSONL entre nodos
        ├── SessionScanner — descubre sesiones Claude en ~/.claude/projects/
        └── MeshDaemon    — loop autónomo que gestiona la red

Cada nodo tiene:
    - node_id: identificador único
    - session_id: sesión Claude persistente (memoria infinita)
    - role: especialización del agente
    - inbox: mensajes pendientes de otros nodos
    - status: active | idle | spawning | error

Comunicación:
    Nodo A → MessageBus (JSONL) → Nodo B lee inbox → responde → MessageBus → Nodo A

Usage:
    from core.node_mesh import NodeMesh

    mesh = NodeMesh()

    # Spawnar nodo con sesión persistente
    node = await mesh.spawn_node("architect", "Design the new API")

    # Enviar mensaje entre nodos
    await mesh.send_message("architect", "researcher", "Need threat model for new API")

    # Broadcast a todos los nodos
    await mesh.broadcast("architect", "New API design ready for review")

    # Correr mesh autónomo
    await mesh.run_mesh(max_cycles=100)
"""

import asyncio
import json
import os
import time
import logging
import fcntl
import threading
from collections import defaultdict, deque
from enum import Enum, auto
from uuid import uuid4
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Set
from pathlib import Path

# Remote node integration (autonomous mesh)
try:
    from core.remote_node_adapter import RemoteNodeAdapter, REMOTE_NODE_MAPPING
except ImportError:
    RemoteNodeAdapter = None
    REMOTE_NODE_MAPPING = {}

# E2E Encryption (NaCl Box — optional, graceful fallback to plaintext)
try:
    from core.e2e_encryption import MeshKeyManager, get_encryptor
    _E2E_AVAILABLE = True
except ImportError:
    _E2E_AVAILABLE = False

logger = logging.getLogger("core.node_mesh")

# ═══════════════════════════════════════════════════════
# SECURITY: RBAC + RATE LIMITING (by Kimi K2.5)
# ═══════════════════════════════════════════════════════

class NodeRole(Enum):
    """Node roles with specific permissions."""
    ARCHITECT = auto()
    RESEARCHER = auto()
    GUARDIAN = auto()
    WORKER = auto()
    COORDINATOR = auto()
    AUDITOR = auto()
    ADMIN = auto()
    SECURITY = auto()


# Roles that are allowed to send messages (all except read-only AUDITOR)
_MESSAGING_ROLES: set = {
    NodeRole.ARCHITECT, NodeRole.RESEARCHER, NodeRole.GUARDIAN,
    NodeRole.WORKER, NodeRole.COORDINATOR, NodeRole.ADMIN, NodeRole.SECURITY,
}

# Map common role-name substrings → NodeRole for auto-authentication
_ROLE_MAP: dict = {
    "commander":    NodeRole.COORDINATOR,
    "orchestrator": NodeRole.COORDINATOR,
    "architect":    NodeRole.ARCHITECT,
    "researcher":   NodeRole.RESEARCHER,
    "analyst":      NodeRole.RESEARCHER,
    "guardian":     NodeRole.GUARDIAN,
    "security":     NodeRole.SECURITY,
    "admin":        NodeRole.ADMIN,
    "auditor":      NodeRole.AUDITOR,
    "narrator":     NodeRole.WORKER,
    "reviewer":     NodeRole.AUDITOR,
    "worker":       NodeRole.WORKER,
}


def _infer_node_role(role_str: str) -> NodeRole:
    """Infer a NodeRole from a free-text role string (case-insensitive substring match)."""
    lower = role_str.lower()
    for keyword, node_role in _ROLE_MAP.items():
        if keyword in lower:
            return node_role
    return NodeRole.WORKER  # safe default


class Permission(Enum):
    """Fine-grained permissions."""
    NODE_CREATE = "node:create"
    NODE_DELETE = "node:delete"
    TASK_SPAWN = "task:spawn"
    TASK_EXECUTE = "task:execute"
    TASK_REPORT = "task:report"
    MESH_CONFIGURE = "mesh:configure"
    SECURITY_MODIFY = "security:modify"
    AUDIT_READ = "audit:read"
    AUDIT_WRITE = "audit:write"
    STATE_READ = "state:read"
    STATE_WRITE = "state:write"


class RBACPolicy:
    """Role-Based Access Control with separation of duties."""
    PERMISSIONS: Dict[NodeRole, Set[Permission]] = {
        NodeRole.ARCHITECT: {
            Permission.NODE_CREATE, Permission.MESH_CONFIGURE, Permission.STATE_READ,
            Permission.TASK_SPAWN, Permission.AUDIT_READ,
        },
        NodeRole.RESEARCHER: {
            Permission.TASK_EXECUTE, Permission.TASK_REPORT, Permission.STATE_READ,
            Permission.AUDIT_READ,
        },
        NodeRole.GUARDIAN: {
            Permission.SECURITY_MODIFY, Permission.AUDIT_READ, Permission.AUDIT_WRITE,
        },
        NodeRole.WORKER: {
            Permission.TASK_EXECUTE, Permission.TASK_REPORT, Permission.STATE_READ,
        },
        NodeRole.COORDINATOR: {
            Permission.TASK_SPAWN, Permission.NODE_DELETE, Permission.TASK_REPORT,
        },
        NodeRole.AUDITOR: {
            Permission.AUDIT_READ,
        },
        NodeRole.ADMIN: {
            Permission.NODE_CREATE, Permission.NODE_DELETE, Permission.TASK_SPAWN,
            Permission.MESH_CONFIGURE, Permission.STATE_WRITE, Permission.AUDIT_READ,
        },
        NodeRole.SECURITY: {
            Permission.SECURITY_MODIFY, Permission.AUDIT_WRITE, Permission.AUDIT_READ,
        },
    }

    @staticmethod
    def has_permission(role: NodeRole, permission: Permission) -> bool:
        """Check if role has permission."""
        return permission in RBACPolicy.PERMISSIONS.get(role, set())

    @staticmethod
    def require_permissions(*permissions: Permission):
        """Decorator to enforce RBAC."""
        def decorator(func):
            async def wrapper(self, node_id: str, *args, **kwargs):
                role = self._authenticated_nodes.get(node_id)
                if not role:
                    raise PermissionError(f"Node {node_id} not authenticated")
                for perm in permissions:
                    if not RBACPolicy.has_permission(role, perm):
                        logger.warning(f"RBAC DENIED: {node_id} ({role.name}) tried {perm.value}")
                        raise PermissionError(f"Permission denied: {perm.value}")
                return await func(self, node_id, *args, **kwargs)
            return wrapper
        return decorator


class RateLimiter:
    """Rate limiter with sliding window algorithm."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """Initialize the sliding-window rate limiter.

        Args:
            max_requests: Maximum number of requests allowed per window (default 100).
            window_seconds: Length of the sliding window in seconds (default 60).
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def is_allowed(self, node_id: str) -> bool:
        """Check if node_id is within rate limit."""
        with self._lock:
            now = time.time()
            cutoff = now - self.window_seconds

            # Remove expired requests
            self._requests[node_id] = deque(
                t for t in self._requests[node_id] if t > cutoff
            )

            if len(self._requests[node_id]) < self.max_requests:
                self._requests[node_id].append(now)
                return True
            return False

    def get_stats(self, node_id: str) -> Dict:
        """Get rate limit stats for node."""
        with self._lock:
            now = time.time()
            cutoff = now - self.window_seconds
            active = sum(1 for t in self._requests[node_id] if t > cutoff)
            return {
                "node_id": node_id,
                "requests_allowed": self.max_requests,
                "requests_used": active,
                "remaining": self.max_requests - active,
            }


class RateLimitExceededError(Exception):
    """Raised when rate limit is exceeded."""
    pass


class PermissionError(Exception):
    """Raised when permission is denied."""
    pass


# ═══════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════

@dataclass
class MeshNode:
    """A node in the agent mesh network."""
    node_id: str
    role: str
    session_id: Optional[str] = None
    status: str = "idle"  # idle | active | spawning | error
    last_active: float = 0
    messages_sent: int = 0
    messages_received: int = 0
    tools: list = field(default_factory=lambda: ["Read", "Edit", "Write", "Bash", "Glob", "Grep"])
    model: str = "claude-opus-4-6"
    created_at: float = field(default_factory=time.time)
    specialty: str = ""
    provider: str = ""
    context_window: int = 0
    cost_per_1k: float = 0.0
    notes: str = ""

@dataclass
class MeshMessage:
    """A message between nodes in the mesh."""
    msg_id: str
    from_node: str
    to_node: str  # "*" for broadcast
    content: str
    msg_type: str = "task"  # task | result | query | alert | sync
    timestamp: float = field(default_factory=time.time)
    read: bool = False
    reply_to: Optional[str] = None

@dataclass
class MeshState:
    """Current state of the entire mesh."""
    total_nodes: int = 0
    active_nodes: int = 0
    pending_messages: int = 0
    total_messages: int = 0
    uptime_seconds: float = 0
    cycles_completed: int = 0


# ═══════════════════════════════════════════════════════
# NODE MESH
# ═══════════════════════════════════════════════════════

class NodeMesh:
    """Orquestador de una red de nodos de agentes Claude.

    Cada nodo es una sesión Claude con memoria persistente.
    Los nodos se comunican a través de un bus de mensajes JSONL.
    El mesh escala infinitamente — spawn nodes on demand.
    """

    def __init__(self,
                 cwd: Optional[str] = None,
                 model: str = "claude-opus-4-6",
                 max_budget_usd: float = 100.0,
                 mesh_dir: str = "logs/mesh",
                 claude_home: Optional[str] = None):
        """Initialize the NodeMesh with registry, message bus, and security components.

        Args:
            cwd: Working directory for spawned Claude sessions (default: current dir).
            model: Default Claude model for new nodes (default: claude-opus-4-6).
            max_budget_usd: Per-session budget cap in USD (default: $100).
            mesh_dir: Directory for mesh state files — nodes.json, messages.jsonl,
                      inbox/, mesh_events.jsonl (default: 'logs/mesh').
            claude_home: Path to Claude config dir for session discovery (default: ~/.claude).
        """
        self.cwd = cwd or os.getcwd()
        self.model = model
        self.max_budget_usd = max_budget_usd
        self.mesh_dir = Path(mesh_dir)
        self.mesh_dir.mkdir(parents=True, exist_ok=True)
        self.claude_home = claude_home or os.path.expanduser("~/.claude")
        self.start_time = time.time()

        # Registry: node_id → MeshNode
        self._nodes: dict[str, MeshNode] = {}
        self._nodes_file = self.mesh_dir / "nodes.json"
        self._load_nodes()

        # Message bus
        self._messages_file = self.mesh_dir / "messages.jsonl"
        self._inbox_dir = self.mesh_dir / "inbox"
        self._inbox_dir.mkdir(parents=True, exist_ok=True)

        # Security: RBAC + Rate Limiting (by Kimi K2.5)
        self._authenticated_nodes: Dict[str, NodeRole] = {}
        self._rate_limiter = RateLimiter(max_requests=100, window_seconds=60)
        self._audit_log: list = []

        # Remote node adapter (autonomous mesh with free APIs)
        self._remote_adapter = RemoteNodeAdapter() if RemoteNodeAdapter else None

        # E2E Key Manager (shared across all nodes)
        self._key_manager = MeshKeyManager() if _E2E_AVAILABLE else None

        # Commander (lazy import to avoid circular)
        self._commander = None

    # ═══════════════════════════════════════════════════
    # COMMANDER ACCESS
    # ═══════════════════════════════════════════════════

    def _get_commander(self):
        """Lazy-load the ClaudeCommander."""
        if self._commander is None:
            import sys, os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from core.claude_commander import ClaudeCommander
            self._commander = ClaudeCommander(
                cwd=self.cwd,
                model=self.model,
                max_budget_usd=self.max_budget_usd,
            )
        return self._commander

    # ═══════════════════════════════════════════════════
    # NODE REGISTRY
    # ═══════════════════════════════════════════════════

    def _load_nodes(self):
        """Load node registry from disk with file locking (VULN-N004 fix)."""
        try:
            if self._nodes_file.exists():
                with open(self._nodes_file, "r") as f:
                    fcntl.flock(f, fcntl.LOCK_SH)
                    try:
                        data = json.loads(f.read())
                    finally:
                        fcntl.flock(f, fcntl.LOCK_UN)
                valid_fields = {f.name for f in MeshNode.__dataclass_fields__.values()}
                for nid, ndata in data.items():
                    filtered = {k: v for k, v in ndata.items() if k in valid_fields}
                    self._nodes[nid] = MeshNode(**filtered)
        except Exception as e:
            logger.warning(f"Failed to load nodes: {e}")
            self._nodes = {}

    def _save_nodes(self):
        """Persist node registry to disk with file locking (VULN-N004 fix)."""
        try:
            data = {nid: asdict(node) for nid, node in self._nodes.items()}
            tmp_file = self._nodes_file.with_suffix(".tmp")
            with open(tmp_file, "w") as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                try:
                    f.write(json.dumps(data, indent=2, default=str))
                    f.flush()
                finally:
                    fcntl.flock(f, fcntl.LOCK_UN)
            tmp_file.replace(self._nodes_file)  # atomic rename
        except Exception as e:
            logger.warning(f"Failed to save nodes: {e}")

    def register_node(self, node_id: str, role: str,
                      tools: Optional[list] = None,
                      model: Optional[str] = None) -> MeshNode:
        """Register a new node or update existing one."""
        if node_id in self._nodes:
            node = self._nodes[node_id]
            node.role = role
            if tools:
                node.tools = tools
            if model:
                node.model = model
        else:
            node = MeshNode(
                node_id=node_id,
                role=role,
                tools=tools or ["Read", "Edit", "Write", "Bash", "Glob", "Grep"],
                model=model or self.model,
            )
            self._nodes[node_id] = node

        # Auto-authenticate with inferred role so RBAC checks work immediately
        if node_id not in self._authenticated_nodes:
            inferred = _infer_node_role(role)
            self.authenticate_node(node_id, inferred)

        # Create inbox directory
        (self._inbox_dir / node_id).mkdir(parents=True, exist_ok=True)
        self._save_nodes()
        return node

    def get_node(self, node_id: str) -> Optional[MeshNode]:
        """Get a node by ID."""
        return self._nodes.get(node_id)

    def list_nodes(self, status: Optional[str] = None) -> list[MeshNode]:
        """List all nodes, optionally filtered by status."""
        nodes = list(self._nodes.values())
        if status:
            nodes = [n for n in nodes if n.status == status]
        return nodes

    def remove_node(self, node_id: str) -> bool:
        """Remove a node from the mesh."""
        if node_id in self._nodes:
            del self._nodes[node_id]
            self._save_nodes()
            return True
        return False

    # ═══════════════════════════════════════════════════
    # MESSAGE BUS
    # ═══════════════════════════════════════════════════

    def _gen_msg_id(self) -> str:
        """Generate a unique message ID using UUID4 (collision-safe)."""
        return uuid4().hex[:12]

    def authenticate_node(self, node_id: str, role: NodeRole) -> str:
        """Authenticate a node and assign a role (RBAC)."""
        self._authenticated_nodes[node_id] = role
        logger.info(f"Node {node_id} authenticated as {role.name}")
        self._audit_log.append({"event": "node_authenticated", "node_id": node_id, "role": role.name, "timestamp": time.time()})
        return node_id

    def check_rate_limit(self, node_id: str) -> bool:
        """Check if node is within rate limit."""
        allowed = self._rate_limiter.is_allowed(node_id)
        if not allowed:
            logger.warning(f"RATE_LIMIT_EXCEEDED: {node_id}")
            self._audit_log.append({"event": "rate_limit_exceeded", "node_id": node_id, "timestamp": time.time()})
            raise RateLimitExceededError(f"Node {node_id} exceeded 100 req/min limit")
        return allowed

    def send_message(self, from_node: str, to_node: str, content: str,
                     msg_type: str = "task", reply_to: Optional[str] = None,
                     route_task_type: Optional[str] = None) -> MeshMessage:
        """Send a message from one node to another (or broadcast with to_node='*').

        If route_task_type is provided and to_node is 'auto', MeshRouterV2 picks
        the optimal destination node based on task type, latency and cost.
        """
        # Smart routing: resolve 'auto' destination via MeshRouterV2
        if to_node == "auto" and route_task_type:
            try:
                from core.mesh_router_v2 import MeshRouterV2
                to_node = MeshRouterV2().route(route_task_type)
                logger.debug(f"MeshRouterV2 routed '{route_task_type}' → {to_node}")
            except Exception as exc:
                logger.warning(f"MeshRouterV2 routing failed, keeping 'auto': {exc}")

        # Rate limit check (VULN-N003 fix by Kimi K2.5)
        self.check_rate_limit(from_node)

        # RBAC: authenticated nodes must have a messaging-capable role
        _sender_role = self._authenticated_nodes.get(from_node)
        if _sender_role is not None and _sender_role not in _MESSAGING_ROLES:
            logger.warning("RBAC DENIED: %s (%s) attempted send_message", from_node, _sender_role.name)
            self._audit_log.append({
                "event": "rbac_denied",
                "node_id": from_node,
                "role": _sender_role.name,
                "action": "send_message",
                "timestamp": time.time(),
            })
            raise PermissionError(f"Node {from_node} ({_sender_role.name}) lacks permission to send messages")

        if to_node != "*" and to_node not in self._nodes:
            logger.warning(f"Sending message to unknown node '{to_node}' — not in registry")

        msg = MeshMessage(
            msg_id=self._gen_msg_id(),
            from_node=from_node,
            to_node=to_node,
            content=content,
            msg_type=msg_type,
            reply_to=reply_to,
        )

        # Write to global message log
        with open(self._messages_file, "a") as f:
            f.write(json.dumps(asdict(msg), default=str) + "\n")

        # Write to recipient inbox(es)
        if to_node == "*":
            # Broadcast to all nodes except sender
            for nid in self._nodes:
                if nid != from_node:
                    self._deliver_to_inbox(nid, msg)
        else:
            self._deliver_to_inbox(to_node, msg)

        # Update sender stats
        if from_node in self._nodes:
            self._nodes[from_node].messages_sent += 1
            self._save_nodes()

        logger.info(f"Message {msg.msg_id}: {from_node} → {to_node} [{msg_type}]")
        return msg

    def broadcast(self, from_node: str, content: str,
                  msg_type: str = "alert") -> MeshMessage:
        """Broadcast a message to all nodes."""
        return self.send_message(from_node, "*", content, msg_type)

    def _deliver_to_inbox(self, node_id: str, msg: MeshMessage):
        """Deliver a message to a node's inbox (E2E encrypted when pubkey available)."""
        inbox_dir = self._inbox_dir / node_id
        inbox_dir.mkdir(parents=True, exist_ok=True)

        # E2E encrypt when recipient has a registered pubkey
        if _E2E_AVAILABLE and self._key_manager:
            recipient_pub = self._key_manager.get_public_key(node_id)
            if recipient_pub:
                try:
                    encryptor = get_encryptor(msg.from_node, key_manager=self._key_manager)
                    payload = asdict(msg)
                    encryptor.send_encrypted(
                        msg.msg_id, node_id, payload,
                        inbox_base=str(self._inbox_dir)
                    )
                    logger.debug(f"E2E encrypted: {msg.msg_id} → {node_id}")
                    return  # skip plaintext write
                except Exception as e:
                    logger.warning(f"E2E encrypt failed ({e}), falling back to plaintext")

        # Plaintext fallback
        msg_file = inbox_dir / f"{msg.msg_id}.json"
        msg_file.write_text(json.dumps(asdict(msg), default=str))

    def read_inbox(self, node_id: str, mark_read: bool = True) -> list[MeshMessage]:
        """Read all unread messages from a node's inbox (decrypts .enc files automatically).

        Rate-limited per node to prevent inbox-flood DoS (same 100 req/min window as send).
        """
        try:
            self.check_rate_limit(node_id)
        except RateLimitExceededError:
            logger.warning("RATE_LIMIT read_inbox: %s", node_id)
            return []

        inbox_dir = self._inbox_dir / node_id
        if not inbox_dir.exists():
            return []

        messages = []

        # Decrypt E2E-encrypted messages (.enc files)
        if _E2E_AVAILABLE and self._key_manager:
            for enc_file in sorted(inbox_dir.glob("*.enc")):
                try:
                    encryptor = get_encryptor(node_id, key_manager=self._key_manager)
                    _from_node, payload = encryptor.read_encrypted(str(enc_file))
                    msg = MeshMessage(**payload)
                    if not msg.read:
                        messages.append(msg)
                        if mark_read:
                            msg.read = True
                            enc_file.write_text(json.dumps(asdict(msg), default=str))
                except Exception as e:
                    logger.warning(f"E2E decrypt failed {enc_file.name}: {e}")

        # Read plaintext messages (.json files)
        for f in sorted(inbox_dir.glob("*.json")):
            try:
                data = json.loads(f.read_text())
                msg = MeshMessage(**data)
                if not msg.read:
                    messages.append(msg)
                    if mark_read:
                        msg.read = True
                        f.write_text(json.dumps(asdict(msg), default=str))
            except Exception:
                continue

        # Update receiver stats
        if node_id in self._nodes:
            self._nodes[node_id].messages_received += len(messages)
            self._save_nodes()

        return messages

    def get_conversation(self, node_a: str, node_b: str, limit: int = 20) -> list[MeshMessage]:
        """Get the conversation history between two nodes."""
        all_msgs = []
        if self._messages_file.exists():
            with open(self._messages_file) as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        msg = MeshMessage(**data)
                        if (msg.from_node == node_a and msg.to_node == node_b) or \
                           (msg.from_node == node_b and msg.to_node == node_a):
                            all_msgs.append(msg)
                    except Exception:
                        continue
        return all_msgs[-limit:]

    # ═══════════════════════════════════════════════════
    # NODE SPAWNING — Claude Sessions
    # ═══════════════════════════════════════════════════

    async def spawn_node(self, node_id: str, task: str,
                         role: Optional[str] = None,
                         tools: Optional[list] = None,
                         model: Optional[str] = None) -> MeshNode:
        """Spawn a new node with a persistent Claude session.

        The node gets its own session_id for infinite memory.
        It reads its inbox before executing the task.
        """
        commander = self._get_commander()

        # Register or update node
        node = self.register_node(
            node_id=node_id,
            role=role or node_id,
            tools=tools,
            model=model,
        )
        node.status = "spawning"
        self._save_nodes()

        # Read inbox — inject pending messages into context
        inbox = self.read_inbox(node_id)
        inbox_context = ""
        if inbox:
            inbox_lines = []
            for msg in inbox[-10:]:  # Last 10 messages
                inbox_lines.append(f"[{msg.from_node} → you | {msg.msg_type}]: {msg.content}")
            inbox_context = f"\n\nINBOX ({len(inbox)} messages):\n" + "\n".join(inbox_lines)

        # Build the full prompt with mesh context
        mesh_prompt = (
            f"You are node '{node_id}' in the DOF Agent Mesh.\n"
            f"Role: {node.role}\n"
            f"Active nodes in mesh: {', '.join(self._nodes.keys())}\n"
            f"{inbox_context}\n\n"
            f"TASK: {task}\n\n"
            f"When done, summarize your result clearly. "
            f"If you need input from another node, say: NEED_INPUT(node_name): question"
        )

        # Execute with persistent session
        result = await commander.persistent_command(
            name=f"mesh-{node_id}",
            prompt=mesh_prompt,
            tools=tools or node.tools,
        )

        # Update node state
        node.status = "active" if result.status == "success" else "error"
        node.session_id = result.session_id
        node.last_active = time.time()
        self._save_nodes()

        # Check if node requested input from another node
        if "NEED_INPUT(" in result.output:
            await self._handle_input_requests(node_id, result.output)

        # Log to mesh audit
        self._log_mesh_event("spawn", {
            "node_id": node_id,
            "status": result.status,
            "elapsed_ms": result.elapsed_ms,
            "session_id": result.session_id,
            "output_preview": result.output[:200],
        })

        return node

    async def _handle_input_requests(self, from_node: str, output: str):
        """Parse NEED_INPUT requests and route them as messages."""
        import re
        pattern = r'NEED_INPUT\((\w+)\):\s*(.+?)(?=NEED_INPUT|\Z)'
        matches = re.findall(pattern, output, re.DOTALL)
        for target_node, question in matches:
            target_node = target_node.strip()
            question = question.strip()
            if target_node in self._nodes:
                self.send_message(from_node, target_node, question, msg_type="query")
                logger.info(f"Routed input request: {from_node} → {target_node}")

    async def wake_node(self, node_id: str, prompt: str) -> Optional[MeshNode]:
        """Wake up an existing node with a new prompt. Resumes its session."""
        node = self.get_node(node_id)
        if not node:
            logger.warning(f"Node {node_id} not found")
            return None

        return await self.spawn_node(
            node_id=node_id,
            task=prompt,
            role=node.role,
            tools=node.tools,
            model=node.model,
        )

    # ═══════════════════════════════════════════════════
    # PARALLEL EXECUTION
    # ═══════════════════════════════════════════════════

    async def spawn_team(self, nodes: dict[str, str],
                         parallel: bool = True) -> dict[str, MeshNode]:
        """Spawn multiple nodes with tasks.

        Args:
            nodes: Dict of {node_id: task_prompt}
            parallel: Run all nodes concurrently (True) or sequentially
        """
        results = {}

        if parallel:
            coros = [
                self.spawn_node(node_id=nid, task=task)
                for nid, task in nodes.items()
            ]
            node_results = await asyncio.gather(*coros, return_exceptions=True)
            for (nid, _), res in zip(nodes.items(), node_results):
                if isinstance(res, Exception):
                    logger.error(f"Node {nid} failed: {res}")
                    results[nid] = self.get_node(nid) or MeshNode(node_id=nid, role=nid, status="error")
                else:
                    results[nid] = res
        else:
            for nid, task in nodes.items():
                try:
                    results[nid] = await self.spawn_node(node_id=nid, task=task)
                except Exception as e:
                    logger.error(f"Node {nid} failed: {e}")
                    results[nid] = self.get_node(nid) or MeshNode(node_id=nid, role=nid, status="error")

        return results

    async def pipeline(self, steps: list[tuple[str, str]]) -> list[MeshNode]:
        """Run nodes in sequence, each getting the previous node's output as context.

        Args:
            steps: List of (node_id, task_prompt) tuples
        """
        results = []
        prev_output = ""

        for node_id, task in steps:
            if prev_output:
                task = f"{task}\n\nPrevious node output:\n{prev_output}"
            node = await self.spawn_node(node_id=node_id, task=task)
            results.append(node)

            # Get the output from the commander's session for chaining
            commander = self._get_commander()
            session_id = commander.get_session(f"mesh-{node_id}")
            if session_id:
                # The output was already captured during spawn_node
                # Read from the last command log
                prev_output = self._get_last_output(node_id)

        return results

    def _get_last_output(self, node_id: str) -> str:
        """Get the last output from a node's session."""
        log_file = Path("logs/commander/commands.jsonl")
        if not log_file.exists():
            return ""
        last_output = ""
        with open(log_file) as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if data.get("mode") == "sdk" and f"mesh-{node_id}" in str(data):
                        last_output = data.get("output_preview", "")
                except Exception:
                    continue
        return last_output

    # ═══════════════════════════════════════════════════
    # SESSION DISCOVERY — Scan ~/.claude/
    # ═══════════════════════════════════════════════════

    def discover_sessions(self) -> list[dict]:
        """Scan ~/.claude/projects/ for active Claude Code sessions.

        Returns list of discovered sessions with metadata.
        This connects with mission-control's claude-sessions.ts scanner.
        """
        projects_dir = Path(self.claude_home) / "projects"
        if not projects_dir.exists():
            return []

        sessions = []
        for project_dir in projects_dir.iterdir():
            if not project_dir.is_dir():
                continue

            for jsonl_file in project_dir.glob("*.jsonl"):
                try:
                    stat = jsonl_file.stat()
                    # Skip files older than 90 minutes (same as mission-control)
                    if (time.time() - stat.st_mtime) > 5400:
                        continue

                    # Read last few lines for session info
                    session_info = self._parse_session_tail(jsonl_file)
                    if session_info:
                        session_info["project"] = project_dir.name
                        session_info["file"] = str(jsonl_file)
                        session_info["last_modified"] = stat.st_mtime
                        sessions.append(session_info)
                except Exception:
                    continue

        return sessions

    def _parse_session_tail(self, jsonl_path: Path, tail_lines: int = 20) -> Optional[dict]:
        """Parse the tail of a JSONL session file for metadata."""
        try:
            lines = jsonl_path.read_text().strip().split("\n")
            if not lines:
                return None

            session_id = None
            model = None
            git_branch = None
            last_timestamp = None

            for line in lines[-tail_lines:]:
                try:
                    entry = json.loads(line)
                    if not session_id and entry.get("sessionId"):
                        session_id = entry["sessionId"]
                    if entry.get("gitBranch"):
                        git_branch = entry["gitBranch"]
                    if entry.get("timestamp"):
                        last_timestamp = entry["timestamp"]
                    if entry.get("message", {}).get("model"):
                        model = entry["message"]["model"]
                except Exception:
                    continue

            if not session_id:
                return None

            return {
                "session_id": session_id,
                "model": model,
                "git_branch": git_branch,
                "last_timestamp": last_timestamp,
            }
        except Exception:
            return None

    def import_discovered_sessions(self) -> int:
        """Discover active Claude sessions and register them as mesh nodes."""
        sessions = self.discover_sessions()
        imported = 0

        for session in sessions:
            sid = session["session_id"]
            # Use short hash as node_id
            node_id = f"discovered-{sid[:8]}"

            if node_id not in self._nodes:
                node = self.register_node(
                    node_id=node_id,
                    role=f"session-{session.get('project', 'unknown')}",
                    model=session.get("model", self.model),
                )
                node.session_id = sid
                node.status = "active"
                node.last_active = session.get("last_modified", time.time())
                imported += 1

        if imported > 0:
            self._save_nodes()
            logger.info(f"Imported {imported} discovered sessions into mesh")

        return imported

    # ═══════════════════════════════════════════════════
    # MESH DAEMON — Autonomous Operation
    # ═══════════════════════════════════════════════════

    async def run_mesh(self, max_cycles: int = 0, interval: int = 60,
                       dry_run: bool = False) -> MeshState:
        """Run the mesh daemon — manages nodes, routes messages, spawns on demand.

        Each cycle:
        1. Discover active Claude sessions
        2. Process pending messages (route, respond)
        3. Wake idle nodes with queued tasks
        4. Prune dead nodes
        5. Log mesh state

        Args:
            max_cycles: 0 = infinite
            interval: seconds between cycles
            dry_run: log decisions without executing
        """
        cycle = 0
        logger.info(f"Mesh daemon starting | nodes={len(self._nodes)} | interval={interval}s")

        while True:
            cycle += 1
            if max_cycles > 0 and cycle > max_cycles:
                break

            try:
                state = await self._mesh_cycle(cycle, dry_run)
                logger.info(
                    f"Mesh cycle {cycle} | "
                    f"nodes={state.total_nodes} active={state.active_nodes} "
                    f"pending_msgs={state.pending_messages}"
                )
            except Exception as e:
                logger.error(f"Mesh cycle {cycle} error: {e}")

            if max_cycles != 1:
                await asyncio.sleep(interval)

        return self.get_state()

    async def _mesh_cycle(self, cycle: int, dry_run: bool = False) -> MeshState:
        """Execute one mesh cycle."""
        # 1. Discover active sessions
        self.import_discovered_sessions()

        # 2. Process pending messages — find nodes with unread messages
        for node_id, node in list(self._nodes.items()):
            inbox = self.read_inbox(node_id, mark_read=False)
            unread = [m for m in inbox if not m.read]

            if unread and node.status in ("idle", "active"):
                # Wake node to process messages
                msg_summary = "; ".join(
                    f"[{m.from_node}|{m.msg_type}]: {m.content[:100]}"
                    for m in unread[:5]
                )

                if not dry_run:
                    await self.wake_node(
                        node_id,
                        f"Process these messages from your inbox:\n{msg_summary}"
                    )
                    # Mark as read after processing
                    self.read_inbox(node_id, mark_read=True)
                else:
                    logger.info(f"[DRY RUN] Would wake {node_id} with {len(unread)} messages")

        # 3. Prune dead nodes (no activity in 2 hours)
        now = time.time()
        for node_id, node in list(self._nodes.items()):
            if node.last_active and (now - node.last_active) > 7200:
                node.status = "idle"

        self._save_nodes()

        # 4. Log state
        state = self.get_state()
        self._log_mesh_event("cycle", {
            "cycle": cycle,
            "dry_run": dry_run,
            **asdict(state),
        })

        return state

    # ═══════════════════════════════════════════════════
    # STATE & LOGGING
    # ═══════════════════════════════════════════════════

    def get_state(self) -> MeshState:
        """Get current mesh state."""
        nodes = list(self._nodes.values())
        pending = 0
        for node_id in self._nodes:
            inbox = self.read_inbox(node_id, mark_read=False)
            pending += len([m for m in inbox if not m.read])

        total_msgs = 0
        if self._messages_file.exists():
            with open(self._messages_file) as f:
                total_msgs = sum(1 for _ in f)

        return MeshState(
            total_nodes=len(nodes),
            active_nodes=len([n for n in nodes if n.status == "active"]),
            pending_messages=pending,
            total_messages=total_msgs,
            uptime_seconds=time.time() - self.start_time,
        )

    def _log_mesh_event(self, event_type: str, data: dict):
        """Log mesh event to JSONL."""
        log_file = self.mesh_dir / "mesh_events.jsonl"
        entry = {
            "timestamp": time.time(),
            "iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "event": event_type,
            **data,
        }
        with open(log_file, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")

    def status_report(self) -> str:
        """Generate a human-readable mesh status report."""
        state = self.get_state()
        nodes = self.list_nodes()

        lines = [
            f"═══ DOF NODE MESH ═══",
            f"Nodes: {state.total_nodes} ({state.active_nodes} active)",
            f"Messages: {state.total_messages} total, {state.pending_messages} pending",
            f"Uptime: {state.uptime_seconds:.0f}s",
            f"",
            f"NODES:",
        ]
        for node in nodes:
            age = time.time() - node.last_active if node.last_active else 0
            lines.append(
                f"  [{node.status:8s}] {node.node_id:20s} | "
                f"role={node.role} | sent={node.messages_sent} recv={node.messages_received} | "
                f"session={node.session_id[:8] if node.session_id else 'none':8s} | "
                f"idle={age:.0f}s"
            )

        return "\n".join(lines)

    # ═══════════════════════════════════════════════════
    # AUTONOMOUS REMOTE NODE DISPATCH
    # ═══════════════════════════════════════════════════

    def dispatch_work_order(self, node_id: str, work_order: Dict) -> Optional[Dict]:
        """
        Dispatch work order to remote node via free APIs (Groq, Cerebras, etc).

        Returns the node's response as a dict, or None if dispatch failed.
        """
        if not self._remote_adapter:
            logger.error("RemoteNodeAdapter not initialized")
            return None

        if node_id not in REMOTE_NODE_MAPPING:
            logger.error(f"No provider mapping for remote node {node_id}")
            return None

        logger.info(f"📤 Dispatching work order to {node_id} via free API...")
        result = self._remote_adapter.dispatch(node_id, work_order)

        if result and result.status == "COMPLETED":
            logger.info(f"✓ {node_id} completed in {result.duration_seconds:.2f}s")
            # Deliver result to commander inbox
            msg = MeshMessage(
                msg_id=work_order.get("msg_id"),
                from_node=node_id,
                to_node="commander",
                content=result.response_text,
                msg_type="result",
            )
            self._deliver_to_inbox("commander", msg)
            return asdict(result)
        else:
            logger.error(f"✗ {node_id} dispatch failed")
            return None


# ═══════════════════════════════════════════════════════
# PREDEFINED MESH TOPOLOGIES
# ═══════════════════════════════════════════════════════

async def spawn_dof_mesh(dry_run: bool = False) -> NodeMesh:
    """Spawn the full DOF agent mesh with predefined roles.

    Topology:
        commander (orchestrator)
            ├── architect (builds features)
            ├── researcher (investigates, analyzes)
            ├── guardian (security, tests)
            ├── narrator (content, docs)
            └── reviewer (quality gate)

    All nodes communicate through the message bus.
    """
    mesh = NodeMesh(cwd="/Users/jquiceva/equipo-de-agentes")

    # Register all nodes
    mesh.register_node("commander", "orchestrator",
                        tools=["Read", "Edit", "Write", "Bash", "Glob", "Grep"])
    mesh.register_node("architect", "code architecture and implementation",
                        tools=["Read", "Edit", "Write", "Bash", "Glob", "Grep"])
    mesh.register_node("researcher", "research, analysis, intelligence gathering",
                        tools=["Read", "Glob", "Grep", "WebSearch", "WebFetch"])
    mesh.register_node("guardian", "security audit, testing, quality",
                        tools=["Read", "Bash", "Glob", "Grep"])
    mesh.register_node("narrator", "documentation, content, communication",
                        tools=["Read", "Write", "Glob", "Grep"])
    mesh.register_node("reviewer", "code review, quality gate",
                        tools=["Read", "Glob", "Grep"])

    if not dry_run:
        # Spawn commander first — it orchestrates the rest
        await mesh.spawn_node(
            "commander",
            "You are the DOF mesh commander. Check the state of the project, "
            "identify the most important tasks, and delegate to other nodes: "
            "architect (build), researcher (analyze), guardian (security), "
            "narrator (docs), reviewer (quality). Send messages via NEED_INPUT(node): task"
        )

    return mesh


# ═══════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════

async def _main():
    """CLI for the Node Mesh."""
    import sys

    args = sys.argv[1:]

    mesh = NodeMesh(cwd="/Users/jquiceva/equipo-de-agentes")

    if not args or args[0] == "status":
        print(mesh.status_report())

    elif args[0] == "discover":
        sessions = mesh.discover_sessions()
        print(f"Discovered {len(sessions)} active Claude sessions:")
        for s in sessions:
            print(f"  {s['session_id'][:12]} | {s.get('project', '?')} | {s.get('model', '?')}")

    elif args[0] == "spawn":
        if len(args) < 3:
            print("Usage: python3 core/node_mesh.py spawn <node_id> <task>")
            return
        node_id = args[1]
        task = " ".join(args[2:])
        node = await mesh.spawn_node(node_id, task)
        print(f"Node spawned: {node.node_id} | status={node.status} | session={node.session_id}")

    elif args[0] == "send":
        if len(args) < 4:
            print("Usage: python3 core/node_mesh.py send <from> <to> <message>")
            return
        msg = mesh.send_message(args[1], args[2], " ".join(args[3:]))
        print(f"Message sent: {msg.msg_id}")

    elif args[0] == "inbox":
        if len(args) < 2:
            print("Usage: python3 core/node_mesh.py inbox <node_id>")
            return
        messages = mesh.read_inbox(args[1], mark_read=False)
        print(f"Inbox for {args[1]}: {len(messages)} messages")
        for m in messages:
            print(f"  [{m.from_node}|{m.msg_type}] {m.content[:100]}")

    elif args[0] == "mesh":
        # Full mesh spawn
        dry_run = "--dry-run" in args
        m = await spawn_dof_mesh(dry_run=dry_run)
        print(m.status_report())

    elif args[0] == "daemon":
        cycles = int(args[1]) if len(args) > 1 else 0
        dry_run = "--dry-run" in args
        await mesh.run_mesh(max_cycles=cycles, dry_run=dry_run)

    else:
        print("Commands: status | discover | spawn | send | inbox | mesh | daemon")


if __name__ == "__main__":
    asyncio.run(_main())
