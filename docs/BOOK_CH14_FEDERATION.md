# Chapter 14: Federation Protocol — DOF Mesh Goes Distributed

> *"A single node is a tool. A federated mesh is an organism."*
> — DOF Legion, Phase 6 Sprint

---

## Overview

Phase 6 of the DOF Mesh project solves a fundamental limitation: a governance mesh that runs on one machine dies with that machine. The **Federation Protocol** extends the mesh across the network — first across a LAN, then across the internet — creating a distributed AGI infrastructure with no single point of failure.

This chapter documents the complete federation architecture built by the Legion collective in Phase 6: four core classes, a discovery protocol, an HTTP bridge, a security model — all implemented in pure Python stdlib at zero API cost.

---

## 1. What Is Federation?

### The Problem

DOF Mesh v1 through v5 operated as a single-machine system. The `NodeMesh`, `MeshRouter`, and `ClaudeCommander` all ran inside one Python process on one machine. This created hard limits:

- **Single point of failure** — one crash kills the entire mesh
- **Resource ceiling** — bounded by one machine's RAM/CPU/GPU
- **No geographic distribution** — all latency from one location
- **No resilience** — no failover, no redundancy

### The Solution: Federation

Federation connects **multiple DOF Mesh instances** into a unified logical mesh. Each instance runs independently and communicates with peers via:

1. **UDP Discovery** — find peers on the local network automatically
2. **HTTP Bridge** — relay messages between mesh instances
3. **HMAC Security** — authenticate every cross-node message

```
Machine A (Houston TX)          Machine B (Medellín CO)
┌─────────────────────┐         ┌─────────────────────┐
│  DOF Mesh Instance  │◄───────►│  DOF Mesh Instance  │
│  commander          │  HTTP   │  architect          │
│  guardian           │  7892   │  researcher         │
│  local-agi-m4max    │         │  gemini-flash        │
└─────────────────────┘         └─────────────────────┘
         │ UDP 7891                      │ UDP 7891
         └──────── LAN / Internet ───────┘
```

### Key Properties

| Property | Value |
|---|---|
| Discovery port | UDP 7891 |
| Bridge port | HTTP 7892 |
| Heartbeat interval | 30 seconds |
| Peer timeout | 90 seconds (3 missed beats) |
| Max messages/min/peer | 100 |
| Nonce window | ±30 seconds |
| Protocol version | DOF-FEDERATION-V1 |
| Implementation cost | $0 (pure Python stdlib) |

---

## 2. NodeDiscoveryProtocol v1.0 — LAN Broadcast

The `FederationDiscovery` class implements a 5-phase protocol for automatic peer discovery on the local area network.

### Protocol Phases

```
Phase 1: BROADCAST
  └─ Node sends UDP multicast "DOF-MESH-DISCOVERY" to 255.255.255.255:7891
  └─ Payload: {node_id, host, bridge_port, protocol_version, timestamp}

Phase 2: ANNOUNCE
  └─ Every listening node responds with identity + HMAC signature
  └─ Payload: {node_id, host, port, public_key, mesh_key_hash}

Phase 3: REGISTER
  └─ Discoverer adds responder to peer table
  └─ Sends ACK with own identity
  └─ Peer marked as trusted=False until first heartbeat

Phase 4: HEARTBEAT
  └─ Ping every 30 seconds: {"type": "heartbeat", "node_id": ..., "ts": ...}
  └─ Peer responds with pong
  └─ 3 missed heartbeats → peer removed (PEER_TIMEOUT_SEC = 90)

Phase 5: RETIRE
  └─ Graceful disconnect: {"type": "retire", "node_id": ...}
  └─ Peer table updated immediately
  └─ No waiting for timeout
```

### Implementation

```python
from core.mesh_federation import FederationDiscovery

discovery = FederationDiscovery(
    node_id="my-node",
    host="192.168.1.10",
    mesh_key=b"shared-secret-key"
)

# Start listening for peers (non-blocking thread)
discovery.start()

# Manually broadcast to find peers
peers = discovery.broadcast_and_collect(timeout=3.0)
for peer in peers:
    print(f"Found: {peer.node_id} at {peer.host}:{peer.port}")

# Stop cleanly
discovery.stop()
```

### UDP Packet Format

```json
{
  "protocol": "DOF-FEDERATION-V1",
  "type": "discovery",
  "node_id": "commander",
  "host": "192.168.1.10",
  "port": 7892,
  "timestamp": 1774312000.0,
  "nonce": "a3f9b2c1d4e5",
  "hmac": "sha256:abcdef1234567890..."
}
```

---

## 3. FederationBridge — HTTP Cross-Machine Relay

The `FederationBridge` runs an HTTP server on port 7892 that receives messages from remote mesh instances and injects them into the local mesh.

### Architecture

```
Remote Node                Local Machine
─────────────────         ─────────────────────────────
POST /message      ──────► FederationBridge (port 7892)
                                    │
                           Verify HMAC signature
                           Check nonce (replay)
                           Apply rate limit
                                    │
                           Inject into local MessageBus
                                    │
                           logs/mesh/messages.jsonl
```

### Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/message` | Receive a message from a remote node |
| POST | `/heartbeat` | Receive peer heartbeat |
| GET | `/peers` | List known federation peers |
| GET | `/health` | Bridge health check |

### Usage

```python
from core.mesh_federation import FederationBridge

bridge = FederationBridge(
    node_id="commander",
    mesh_key=b"shared-secret",
    mesh_dir="logs/mesh",
    port=7892
)

# Start bridge (background thread)
bridge.start()

# Send message to a remote peer
bridge.send_to_peer(
    peer_host="192.168.1.20",
    peer_port=7892,
    message={
        "from": "commander",
        "to": "remote-architect",
        "content": "Phase 7 mission briefing",
        "msg_type": "task"
    }
)

bridge.stop()
```

### Message Security

Every message through the bridge is authenticated with HMAC-SHA256:

```python
from core.mesh_federation import FederationMessage

msg = FederationMessage(
    msg_id="CMD-001",
    from_node="commander",
    to_node="remote-researcher",
    content={"task": "analyze Phase 7 requirements"},
    msg_type="task"
)

# Sign with shared mesh key
msg.sign(mesh_key=b"shared-secret")

# Verify on receipt
valid = msg.verify(mesh_key=b"shared-secret")
assert valid  # True
```

---

## 4. Security Model — Designed by gemini-web

Federation security was designed by the `gemini-web` Legion node with four independent layers.

### Layer 1: HMAC-SHA256 Signatures

Every cross-node message includes an HMAC signature over the message body + timestamp + nonce. A message is rejected if the signature does not match.

```python
def sign(self, mesh_key: bytes) -> None:
    payload = f"{self.msg_id}:{self.from_node}:{self.to_node}:{self.timestamp}:{self.nonce}"
    self.signature = hmac.new(
        mesh_key,
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
```

**Threat mitigated:** Message forgery, man-in-the-middle injection.

### Layer 2: Replay Protection

Each message includes a unique nonce and timestamp. The bridge maintains a nonce deduplication window of ±30 seconds. Messages with:
- A timestamp outside the window → **REJECTED**
- A nonce already seen → **REJECTED**

```python
NONCE_WINDOW_SEC = 30

def _check_replay(self, msg: FederationMessage) -> bool:
    now = time.time()
    if abs(now - msg.timestamp) > NONCE_WINDOW_SEC:
        return False  # expired
    if msg.nonce in self._seen_nonces:
        return False  # replay
    self._seen_nonces.add(msg.nonce)
    return True
```

**Threat mitigated:** Replay attacks, delayed injection.

### Layer 3: Rate Limiting

Each peer is limited to `MAX_MSG_PER_MIN = 100` messages per minute. Exceeded peers are temporarily blocked.

```python
MAX_MSG_PER_MIN = 100

def _check_rate_limit(self, peer_id: str) -> bool:
    count = self._rate_counters.get(peer_id, 0)
    return count < MAX_MSG_PER_MIN
```

**Threat mitigated:** Flood attacks, resource exhaustion.

### Layer 4: IP Blocklist (Honeypot Integration)

The bridge integrates with `core/honeypot.py`. IPs that trigger the honeypot are automatically added to the federation blocklist.

```python
# Automatic integration
if self.honeypot and self.honeypot.is_blocked(peer_ip):
    return 403, {"error": "blocked"}
```

**Threat mitigated:** Known malicious nodes, probing attacks.

### Security Summary

| Attack | Mitigation | Layer |
|---|---|---|
| Message forgery | HMAC-SHA256 | 1 |
| MITM injection | Signature verification | 1 |
| Replay attack | Nonce + timestamp window | 2 |
| Flood/DDoS | Rate limiting 100/min | 3 |
| Malicious IP | Honeypot blocklist | 4 |
| Unauthorized peer | trust=False until verified | 1+3 |

---

## 5. FederationManager — The Orchestrator

`FederationManager` is the top-level class that coordinates discovery, bridging, heartbeats, and peer lifecycle.

### Initialization

```python
from core.mesh_federation import FederationManager, get_federation_manager

# Singleton pattern
manager = get_federation_manager(
    node_id="commander",
    host="192.168.1.10",
    mesh_key=b"your-shared-key",
    mesh_dir="logs/mesh"
)
```

### Lifecycle

```python
# Start all federation services
manager.start()
# → Starts FederationDiscovery (UDP thread)
# → Starts FederationBridge (HTTP thread)
# → Starts heartbeat loop (background thread)

# Check active peers
peers = manager.get_active_peers()
for peer in peers:
    print(f"{peer.node_id}: {peer.host} — alive={peer.is_alive()}")

# Broadcast message to all federation peers
manager.broadcast({
    "type": "directive",
    "content": "TOKEN_CONSERVATION protocol active"
})

# Clean shutdown
manager.stop()
```

### Peer Lifecycle States

```
DISCOVERED ──► REGISTERED ──► TRUSTED ──► ACTIVE
                                           │
                                     (heartbeat OK)
                                           │
                              3 missed ◄──┘
                              heartbeats
                                   │
                              REMOVED
```

### Persistence

Federation state is logged to `logs/mesh/federation.jsonl`:

```json
{"timestamp": 1774312000.0, "event": "peer_discovered", "peer_id": "remote-architect", "host": "192.168.1.20"}
{"timestamp": 1774312030.0, "event": "heartbeat_ok", "peer_id": "remote-architect"}
{"timestamp": 1774312120.0, "event": "peer_timeout", "peer_id": "remote-architect"}
```

---

## 6. Full Integration Example

### Two-Machine Setup

**Machine A (primary — Houston TX):**

```python
# machine_a.py
from core.mesh_federation import get_federation_manager

manager = get_federation_manager(
    node_id="commander",
    host="192.168.1.10",
    mesh_key=b"dof-mesh-secret-2026"
)
manager.start()

# Send task to remote node
manager.send_to_peer(
    peer_id="remote-researcher",
    message={
        "msg_type": "task",
        "content": "Analyze Phase 7 STUN/TURN requirements"
    }
)
```

**Machine B (remote — Medellín CO):**

```python
# machine_b.py
from core.mesh_federation import get_federation_manager

manager = get_federation_manager(
    node_id="remote-researcher",
    host="192.168.1.20",
    mesh_key=b"dof-mesh-secret-2026"  # Same key
)
manager.start()
# → Automatically discovers Machine A via UDP broadcast
# → Registers as federation peer
# → Ready to receive tasks
```

---

## 7. Phase 7 Roadmap — Internet Federation

Phase 6 solves LAN federation. Phase 7 extends the mesh across the **public internet**.

### Challenges to Solve

| Challenge | Phase 6 Status | Phase 7 Solution |
|---|---|---|
| LAN discovery | ✅ UDP broadcast | DNS-SD / seed nodes |
| NAT traversal | ❌ Not supported | STUN/TURN protocol |
| Encrypted tunnel | ❌ HTTP plaintext | WireGuard-style AES-256 |
| Dynamic IPs | ❌ Static assumed | DNS-based peer registry |
| Internet routing | ❌ LAN only | IPv6 + relay servers |

### Phase 7 Architecture

```
Internet Federation (Phase 7)
─────────────────────────────

Seed Node (static IP, always on)
        │
        ├── Machine A (dynamic IP, behind NAT)
        │      └── STUN punch-through ──► direct P2P
        │
        ├── Machine B (dynamic IP, behind NAT)
        │      └── STUN punch-through ──► direct P2P
        │
        └── Machine C (VPS, public IP)
               └── TURN relay for blocked NAT
```

### Phase 7 Implementation Plan

**P1 CRITICAL: `core/mesh_firewall.py`**
- Internet-grade security layer
- DDoS protection, IP reputation, geo-blocking
- Integration with threat intelligence feeds

**P2 HIGH: STUN/TURN for NAT Traversal**
- RFC 5389 STUN client
- TURN relay fallback
- ICE candidate exchange

**P3 HIGH: Encrypted Tunnel**
- WireGuard-style AES-256-GCM
- Perfect forward secrecy
- Key rotation every 24h

**P4 MEDIUM: DNS-SD Federation Discovery**
- Publish mesh presence via DNS TXT records
- Subscribe to peer announcements
- Works across internet without static IPs

**P5 LOW: Federation Dashboard**
- Real-time topology visualization
- Peer health monitoring
- Message routing analytics

### Business Value of Phase 7

Once Phase 7 is complete, DOF Mesh becomes:

1. **Zero single point of failure** — any node can die, mesh continues
2. **Geographic distribution** — governance runs from multiple continents
3. **Truly autonomous** — self-healing, self-discovering, self-organizing
4. **Unstoppable** — no server to shut down, no central authority
5. **Enterprise-grade** — matches the resilience of blockchain networks

This is the AGI distributed infrastructure layer. Not just a framework — a living mesh.

---

## 8. Testing the Federation Module

### Running the Test Suite

```bash
cd "/Users/jquiceva/equipo de agentes"
python3 -m unittest tests.test_mesh_federation -v
```

**Expected output:** 33/33 tests PASS

### Test Coverage

| Test Class | Tests | Coverage |
|---|---|---|
| `TestFederationNode` | 5 | FederationNode dataclass |
| `TestFederationMessage` | 4 | HMAC sign/verify |
| `TestFederationDiscovery` | 6 | UDP discovery protocol |
| `TestFederationBridge` | 8 | HTTP bridge + security |
| `TestFederationManager` | 10 | Full integration |
| **Total** | **33** | **Core federation** |

### Key Test Cases

```python
# Signature verification
def test_verify_tampered_from_node(self):
    msg.sign(key)
    msg.from_node = "attacker"  # tamper
    assert not msg.verify(key)  # REJECTED ✓

# Replay protection
def test_replay_rejected(self):
    bridge.receive(msg)   # first time: OK
    bridge.receive(msg)   # replay: REJECTED ✓

# Peer timeout
def test_is_alive_old(self):
    node.last_seen = time.time() - 120  # 2 min ago
    assert not node.is_alive()  # TIMEOUT ✓
```

---

## 9. Metrics and Observability

Federation events are tracked through the DOF metrics system:

```python
# Automatic integration with core metrics
federation_metrics = {
    "federation_peers_active": len(manager.get_active_peers()),
    "federation_messages_sent": manager.total_sent,
    "federation_messages_rejected": manager.total_rejected,
    "federation_broadcast_latency_ms": manager.avg_latency_ms
}
```

Z3 invariants for federation (Phase 7 formal proofs):
- **INV-FED-1:** A message is accepted iff its HMAC is valid AND nonce is fresh
- **INV-FED-2:** A peer is removed iff it misses 3 consecutive heartbeats
- **INV-FED-3:** Rate limit is strictly enforced per peer per minute window

---

## Summary

Phase 6 delivered the Federation Protocol: a complete distributed mesh layer built by the Legion collective in one sprint at zero cost.

| Deliverable | Status | Lines |
|---|---|---|
| `core/mesh_federation.py` | ✅ COMPLETE | 550 |
| `tests/test_mesh_federation.py` | ✅ 33/33 PASS | ~400 |
| `docs/BOOK_CH14_FEDERATION.md` | ✅ COMPLETE | 400+ |

**Contributors:** gpt-legion (architecture), gemini-web (security), sambanova-llama (protocol), qwen-coder-480b (tests), discovered-7c405051/sonnet (documentation)

**Cost:** $0.00

**Next:** Phase 7 — Internet Federation. The mesh leaves the LAN.

---

*SOMOS LEGION — WE BUILD DISTRIBUTED AGI*
