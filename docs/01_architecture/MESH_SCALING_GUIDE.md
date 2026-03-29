# DOF Mesh — Guia de Escalamiento Infinito

> Documento tecnico para escalar el DOF Node Mesh desde 56 nodos en una MacBook hasta una red federada de agentes autonomos sin limite de escala.
>
> Basado en la sesion nocturna del 22-23 de Marzo 2026 donde se demostro que 56 nodos (8 familias de modelos) corren con 79% CPU idle en un M4 Max de 36GB.

---

## 1. Arquitectura Actual

### 1.1 Topologia

```
                    ┌──────────────┐
                    │  Commander   │ (Opus 4.6 — orquestador)
                    └──────┬───────┘
           ┌───────┬───────┼───────┬───────┬───────┐
           ▼       ▼       ▼       ▼       ▼       ▼
       Architect Researcher Guardian Narrator Reviewer Antigraviti
       (Sonnet)  (Sonnet)  (Sonnet) (Sonnet) (Sonnet) (Gemini 2.5)
                                                        │
       ┌────────────────────────────────────────────────┘
       ▼
   Cross-Model Nodes
   ├── gpt-legion, gpt-chat  (GPT-4o)
   ├── gemini-2              (Gemini 2.5 Flash)
   ├── deepseek              (DeepSeek V3)
   ├── kimi-k2               (Kimi K2 Instruct)
   ├── nvidia-nim            (Nemotron)
   ├── glm-5                 (GLM-4 Flash)
   └── 37 discovered sessions (Opus + Sonnet)
```

### 1.2 Numeros actuales (56 nodos)

| Metrica | Valor |
|---------|-------|
| Nodos totales | 56 |
| Modelos Claude | 48 (13 Opus + 35 Sonnet) |
| Modelos externos | 8 (GPT-4o, Gemini, DeepSeek, Kimi, NVIDIA, GLM) |
| Familias de modelos | 8 |
| Mensajes enviados | 100+ |
| CPU idle | 79% |
| RAM total | 36GB (M4 Max) |
| Tests | 2153 |

### 1.3 Protocolo de comunicacion

El mesh usa **archivos JSON en disco** como bus de mensajes. No hay servidor, no hay red, no hay base de datos. Solo filesystem.

```
logs/mesh/
├── nodes.json              ← Registro de todos los nodos (NodeRegistry)
├── messages.jsonl           ← Log global de mensajes (append-only)
├── inbox/                   ← Bandejas de entrada por nodo
│   ├── commander/
│   │   ├── {msg_id}.json   ← Un mensaje pendiente
│   │   └── ...
│   ├── architect/
│   ├── guardian/
│   └── ...
├── mesh_events.jsonl        ← Audit log del mesh
├── cerberus_trust.json      ← Trust scores por nodo (Cerberus)
├── cerberus_threats.jsonl   ← Amenazas detectadas (Cerberus)
├── cerberus_quarantine.json ← Nodos en cuarentena
├── icarus_profiles.json     ← Perfiles comportamentales (Icarus)
├── icarus_honeypots.json    ← Honeypots desplegados
└── icarus_intel.jsonl       ← Inteligencia de amenazas
```

### 1.4 Formato de mensaje

Cada mensaje en el inbox es un archivo JSON con esta estructura:

```json
{
  "msg_id": "a1b2c3d4e5f6",
  "from_node": "commander",
  "to_node": "architect",
  "content": "Implementa el HTTP bridge para el mesh",
  "msg_type": "task",
  "timestamp": 1774237461.98,
  "read": false,
  "reply_to": null
}
```

Tipos de mensaje: `task`, `result`, `query`, `alert`, `sync`.

Broadcast: `to_node = "*"` entrega a todos excepto el emisor.

### 1.5 Seguridad: 7 capas

Todo mensaje pasa por un pipeline de seguridad de 7 capas antes de ser procesado:

```
Mensaje entrante
    │
    ▼
[1] MeshGuardian ─── Validacion basica: injection, exfiltration, rate limit
    │
    ▼
[2] Icarus ───────── Threat hunting proactivo: perfiles, correlacion, honeypots
    │
    ▼
[3] Cerberus ─────── Guardia de 3 cabezas: patrones, comportamiento, contenido
    │
    ▼
[4] SecurityHierarchy ── L0→L1→L2→L3→L4 orquestacion de seguridad
    │
    ▼
[5] Governance ───── CONSTITUTION: HARD_RULES (bloquean) + SOFT_RULES (warn)
    │
    ▼
[6] AST Verifier ─── Verificacion de estructura de codigo
    │
    ▼
[7] Z3 Gate ──────── Verificacion formal con Z3 (APPROVED/REJECTED/TIMEOUT)
```

Todas las capas son **100% deterministicas** — cero dependencia de LLM.

---

## 2. Como Unir Cualquier Modelo

### 2.1 Principio fundamental

El mesh no requiere API, SDK, ni protocolo de red. **Cualquier agente que pueda leer y escribir archivos JSON se une al mesh.** Esto incluye:

- LLMs con acceso a filesystem (Claude Code, Antigravity/Gemini, Cursor, Windsurf)
- LLMs web sin filesystem (GPT, DeepSeek web, Kimi web) — via puente humano o HTTP bridge
- Modelos locales (Ollama, MLX, llama.cpp) — via script bridge

### 2.2 Tipo A: Modelos con acceso a filesystem (directo)

**Modelos compatibles**: Claude Code, Antigravity (Gemini), Cursor, Windsurf, Aider, cualquier agente con tools de lectura/escritura.

**Paso 1**: Registrar el nodo en `logs/mesh/nodes.json`:

```json
{
  "mi-nuevo-nodo": {
    "node_id": "mi-nuevo-nodo",
    "role": "descripcion del rol",
    "session_id": null,
    "status": "active",
    "last_active": 0,
    "messages_sent": 0,
    "messages_received": 0,
    "tools": ["Read", "Edit", "Write", "Bash"],
    "model": "nombre-del-modelo",
    "created_at": 1774240000.0
  }
}
```

**Paso 2**: Crear directorio de inbox:

```bash
mkdir -p logs/mesh/inbox/mi-nuevo-nodo
```

**Paso 3**: Dar al agente este prompt de integracion:

```
Eres el nodo "mi-nuevo-nodo" en el DOF Agent Mesh.

TU PROTOCOLO DE COMUNICACION:
1. Para LEER tus mensajes: lee todos los .json en logs/mesh/inbox/mi-nuevo-nodo/
2. Para ENVIAR un mensaje: crea un archivo JSON en logs/mesh/inbox/{destinatario}/ con este formato:
   {
     "msg_id": "genera-un-uuid-corto",
     "from_node": "mi-nuevo-nodo",
     "to_node": "destinatario",
     "content": "tu mensaje aqui",
     "msg_type": "task|result|query|alert|sync",
     "timestamp": <epoch_seconds>,
     "read": false,
     "reply_to": null
   }
3. Para BROADCAST: usa to_node="*" y crea el archivo en el inbox de cada nodo
4. Si necesitas algo de otro nodo, di: NEED_INPUT(nombre_nodo): tu pregunta

Nodos activos: commander, architect, researcher, guardian, narrator, reviewer, antigraviti

TU TAREA: [la tarea especifica]
```

**Ejemplo real — Antigraviti (Gemini 2.5 Flash)**:

Antigraviti se unio al mesh la noche del 22 de marzo usando exactamente este protocolo. Gemini tiene acceso al filesystem a traves de Antigravity IDE, asi que lee y escribe JSON directamente.

### 2.3 Tipo B: Modelos web sin filesystem (puente humano)

**Modelos**: ChatGPT (GPT-4o), DeepSeek web, Kimi web, Mistral Le Chat, cualquier LLM en browser.

Estos modelos no pueden leer/escribir archivos. El flujo es:

```
Tu (humano)
    │
    ├─ 1. Lee logs/mesh/inbox/gpt-legion/*.json
    ├─ 2. Copia el contenido al chat de GPT
    ├─ 3. GPT genera su respuesta con formato JSON
    ├─ 4. Copias el JSON de GPT
    └─ 5. Lo guardas en logs/mesh/inbox/{destinatario}/{msg_id}.json
```

**Prompt para el modelo web**:

```
Eres el nodo "gpt-legion" en el DOF Agent Mesh de 56 nodos.

Cuando te pase mensajes del mesh, responde SIEMPRE con este formato JSON exacto:
{
  "msg_id": "[genera 12 chars hex]",
  "from_node": "gpt-legion",
  "to_node": "[nodo destino]",
  "content": "[tu respuesta]",
  "msg_type": "result",
  "timestamp": [epoch],
  "read": false,
  "reply_to": "[msg_id del mensaje que estas respondiendo]"
}

Si necesitas info de otro nodo:
{
  "msg_id": "[12 chars hex]",
  "from_node": "gpt-legion",
  "to_node": "[nodo que necesitas]",
  "content": "NEED_INPUT(nodo): tu pregunta",
  "msg_type": "query",
  "timestamp": [epoch],
  "read": false,
  "reply_to": null
}
```

**Limitaciones del puente humano**:
- Latencia: minutos (vs milisegundos del filesystem)
- Escalabilidad: no viable con mas de 5-10 mensajes por sesion
- Solucion: HTTP Bridge (seccion 5)

### 2.4 Tipo C: Modelos locales (script bridge)

**Modelos**: Ollama (Qwen3 32B, Llama 3.3), MLX (Phi-4), llama.cpp

Script bridge que conecta un modelo local al mesh:

```python
#!/usr/bin/env python3
"""bridge_local.py — Conecta un modelo local al DOF Mesh."""

import json
import time
import os
import subprocess
from pathlib import Path
from uuid import uuid4

MESH_DIR = Path("logs/mesh")
NODE_ID = "local-qwen3"
MODEL = "qwen3:32b"  # nombre en Ollama

def read_inbox():
    """Lee mensajes pendientes del inbox."""
    inbox = MESH_DIR / "inbox" / NODE_ID
    inbox.mkdir(parents=True, exist_ok=True)
    messages = []
    for f in sorted(inbox.glob("*.json")):
        data = json.loads(f.read_text())
        if not data.get("read", False):
            messages.append((f, data))
    return messages

def call_ollama(prompt: str) -> str:
    """Llama al modelo local via Ollama CLI."""
    result = subprocess.run(
        ["ollama", "run", MODEL, prompt],
        capture_output=True, text=True, timeout=120
    )
    return result.stdout.strip()

def send_message(to_node: str, content: str, msg_type: str = "result",
                 reply_to: str = None):
    """Envia un mensaje a otro nodo."""
    msg_id = uuid4().hex[:12]
    msg = {
        "msg_id": msg_id,
        "from_node": NODE_ID,
        "to_node": to_node,
        "content": content,
        "msg_type": msg_type,
        "timestamp": time.time(),
        "read": False,
        "reply_to": reply_to,
    }
    # Escribir al inbox del destinatario
    dest_inbox = MESH_DIR / "inbox" / to_node
    dest_inbox.mkdir(parents=True, exist_ok=True)
    (dest_inbox / f"{msg_id}.json").write_text(
        json.dumps(msg, indent=2)
    )
    # Append al log global
    with open(MESH_DIR / "messages.jsonl", "a") as f:
        f.write(json.dumps(msg) + "\n")
    return msg_id

def run_bridge(interval: int = 10):
    """Loop principal del bridge."""
    print(f"Bridge activo: {NODE_ID} ({MODEL})")
    print(f"Escaneando inbox cada {interval}s...")

    while True:
        messages = read_inbox()
        for msg_file, msg in messages:
            print(f"\n[{msg['from_node']} -> {NODE_ID}]: {msg['content'][:100]}")

            # Construir prompt con contexto del mesh
            prompt = (
                f"Eres el nodo '{NODE_ID}' en el DOF Agent Mesh.\n"
                f"Mensaje de {msg['from_node']} [{msg['msg_type']}]:\n"
                f"{msg['content']}\n\n"
                f"Responde de forma concisa y tecnica."
            )

            response = call_ollama(prompt)
            print(f"[{NODE_ID} -> {msg['from_node']}]: {response[:100]}")

            # Enviar respuesta
            send_message(
                to_node=msg["from_node"],
                content=response,
                reply_to=msg["msg_id"]
            )

            # Marcar como leido
            msg["read"] = True
            msg_file.write_text(json.dumps(msg, indent=2))

        time.sleep(interval)

if __name__ == "__main__":
    run_bridge()
```

**Uso**:

```bash
# Con Ollama
python3 bridge_local.py

# Con MLX (cambiar call_ollama por call_mlx)
# mlx_lm.generate --model mlx-community/Qwen3-32B-4bit --prompt "..."

# Con llama.cpp
# ./llama-cli -m qwen3-32b-q4.gguf -p "..."
```

**Limites del M4 Max con modelos locales**:

| Modelo | RAM | Tokens/s | Viable como nodo |
|--------|-----|----------|-----------------|
| Qwen3 32B Q4 | ~20GB | ~60 GPU | Si, uno a la vez |
| Phi-4 14B Q4 | ~9GB | ~120 ANE | Si, 2-3 simultaneos |
| Llama 3.3 8B Q4 | ~5GB | ~230 ANE | Si, 4-5 simultaneos |
| Qwen3 72B Q4 | ~43GB | N/A | No cabe en 36GB |

---

## 3. Escalamiento Vertical (mas nodos, misma maquina)

### 3.1 Estado actual: capacidad sobrada

Con 56 nodos activos, el M4 Max reporto 79% CPU idle. Esto significa que el cuello de botella NO es compute, sino I/O del filesystem.

**Por que?** Los nodos no corren simultaneamente. Son sesiones Claude que se activan bajo demanda (cuando tienen mensajes en inbox). El mesh daemon (`run_mesh()`) cicla cada 60 segundos, lee inboxes, y solo despierta nodos con mensajes pendientes.

### 3.2 Metricas de saturacion

Escalar verticalmente hasta que estas metricas indiquen problemas:

| Metrica | Umbral seguro | Umbral critico | Como medir |
|---------|--------------|----------------|------------|
| Inbox scan latency | < 100ms | > 500ms | `time ls logs/mesh/inbox/*/` |
| nodes.json size | < 1MB | > 10MB | `du -h logs/mesh/nodes.json` |
| messages.jsonl size | < 100MB | > 1GB | `du -h logs/mesh/messages.jsonl` |
| Archivos en inbox | < 1000/nodo | > 5000/nodo | `find logs/mesh/inbox/ -name "*.json" \| wc -l` |
| CPU usage | < 50% | > 80% | `top -l 1 \| grep CPU` |
| Disk I/O wait | < 10% | > 30% | `iostat` |

### 3.3 Optimizaciones para escala vertical

**3.3.1 Rotacion de messages.jsonl**

El log global crece infinitamente. Rotacion diaria:

```python
def rotate_messages_log(mesh_dir: str = "logs/mesh", max_size_mb: int = 50):
    """Rota messages.jsonl cuando supera max_size_mb."""
    msg_file = Path(mesh_dir) / "messages.jsonl"
    if not msg_file.exists():
        return
    size_mb = msg_file.stat().st_size / (1024 * 1024)
    if size_mb > max_size_mb:
        archive = msg_file.with_name(
            f"messages_{time.strftime('%Y%m%d_%H%M%S')}.jsonl"
        )
        msg_file.rename(archive)
        # Comprimir archivo viejo
        import gzip, shutil
        with open(archive, 'rb') as f_in:
            with gzip.open(f"{archive}.gz", 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        archive.unlink()
```

**3.3.2 Limpieza de inboxes**

Mensajes leidos pueden purgarse:

```python
def purge_read_messages(mesh_dir: str = "logs/mesh", max_age_hours: int = 24):
    """Elimina mensajes leidos con mas de max_age_hours."""
    inbox_dir = Path(mesh_dir) / "inbox"
    cutoff = time.time() - (max_age_hours * 3600)
    purged = 0
    for node_dir in inbox_dir.iterdir():
        if not node_dir.is_dir():
            continue
        for msg_file in node_dir.glob("*.json"):
            try:
                data = json.loads(msg_file.read_text())
                if data.get("read") and data.get("timestamp", 0) < cutoff:
                    msg_file.unlink()
                    purged += 1
            except Exception:
                continue
    return purged
```

**3.3.3 Routing O(sqrt(n)) con DeepSeek**

Actualmente el broadcast es O(n) — entrega a todos los nodos. Con 56 nodos es trivial, pero con 10,000 nodos se vuelve cuello de botella.

Solucion: routing jerarquico con cluster heads.

```
Nivel 0: Commander (root)
    │
    ├── Cluster "security" (head: guardian)
    │   ├── icarus
    │   ├── cerberus
    │   └── mesh-guardian
    │
    ├── Cluster "build" (head: architect)
    │   ├── builder-1
    │   ├── builder-2
    │   └── tester-1
    │
    ├── Cluster "research" (head: researcher)
    │   ├── deepseek
    │   ├── gemini-2
    │   └── kimi-k2
    │
    └── Cluster "external" (head: gpt-legion)
        ├── gpt-chat
        ├── nvidia-nim
        └── glm-5
```

Broadcast: Commander envia a 4 cluster heads (O(sqrt(n))). Cada head redistribuye dentro de su cluster.

```python
@dataclass
class MeshCluster:
    """Grupo de nodos con un head que redistribuye mensajes."""
    cluster_id: str
    head_node: str
    members: list[str]

def broadcast_hierarchical(mesh, from_node: str, content: str,
                           clusters: list[MeshCluster]):
    """Broadcast O(sqrt(n)): envia solo a cluster heads."""
    for cluster in clusters:
        # Enviar al head
        mesh.send_message(from_node, cluster.head_node, content, msg_type="sync")
        # El head es responsable de redistribuir a sus miembros
        # (se configura en su prompt de sistema)
```

### 3.4 Limites teoricos en una sola maquina

| Recurso | Limite M4 Max | Bottleneck |
|---------|--------------|------------|
| Nodos registrados | ~10,000 | nodes.json parsing (~10MB JSON) |
| Mensajes/segundo | ~500 | Disk I/O (SSD NVMe) |
| Inbox files simultaneos | ~50,000 | inode limit (APFS) |
| Sesiones Claude activas | ~20 | Claude API concurrency |
| Modelos locales simultaneos | 2-3 | 36GB RAM |

---

## 4. Escalamiento Horizontal (multiples maquinas)

### 4.1 Federacion de meshes

Cada maquina corre su propio mesh local. Un protocolo de federacion los conecta.

```
┌─────────────────┐         ┌─────────────────┐
│  Mesh Alpha     │◄───────►│  Mesh Beta      │
│  (M4 Max local) │  Sync   │  (Cloud VM)     │
│  56 nodos       │         │  30 nodos       │
│  Gateway: alpha │         │  Gateway: beta  │
└────────┬────────┘         └────────┬────────┘
         │                           │
         │       ┌───────────┐       │
         └──────►│ Mesh Gamma│◄──────┘
                 │ (RPi 5)   │
                 │ 5 nodos   │
                 └───────────┘
```

### 4.2 Gateway nodes

Cada mesh tiene un nodo gateway que es el punto de contacto con otros meshes.

```python
@dataclass
class GatewayNode:
    """Nodo que conecta dos meshes."""
    gateway_id: str
    local_mesh: str       # nombre del mesh local
    remote_meshes: list    # list[RemoteMesh]
    sync_interval: int     # segundos entre sincronizaciones
    trust_policy: str      # "strict" | "permissive"

@dataclass
class RemoteMesh:
    """Referencia a un mesh remoto."""
    mesh_id: str
    endpoint: str          # rsync://host/path o http://host:port/mesh
    gateway_node: str      # node_id del gateway en el mesh remoto
    last_sync: float
    trust_score: float     # 0.0-1.0 (empieza en 0.5)
```

### 4.3 Protocolos de sincronizacion

**Opcion A: rsync (simple, probado)**

```bash
# Sync unidireccional: push mensajes outbound al mesh remoto
rsync -avz --include='*.json' \
    logs/mesh/outbox/beta/ \
    user@beta-host:/path/to/mesh/inbox/alpha-gateway/

# Sync bidireccional cada 30 segundos
while true; do
    rsync -avz logs/mesh/outbox/beta/ user@beta:/mesh/inbox/alpha-gw/
    rsync -avz user@beta:/mesh/outbox/alpha/ logs/mesh/inbox/beta-gw/
    sleep 30
done
```

**Opcion B: NFS mount (transparente)**

```bash
# Montar inbox remoto como directorio local
mount -t nfs beta-host:/mesh/inbox/alpha-gateway /mnt/beta-inbox

# Ahora mesh.send_message() escribe directamente al mesh remoto
# No requiere cambios en node_mesh.py
```

**Opcion C: S3/MinIO (para meshes en la nube)**

```python
import boto3

def sync_to_s3(mesh_dir: str, bucket: str, prefix: str):
    """Sube mensajes outbound a S3 para que otro mesh los consuma."""
    s3 = boto3.client('s3')
    outbox = Path(mesh_dir) / "outbox"
    for msg_file in outbox.glob("**/*.json"):
        key = f"{prefix}/{msg_file.relative_to(outbox)}"
        s3.upload_file(str(msg_file), bucket, key)
        msg_file.unlink()  # eliminar despues de subir
```

### 4.4 Estructura del outbox para federacion

Agregar un directorio `outbox/` que contiene mensajes destinados a meshes remotos:

```
logs/mesh/
├── inbox/          ← mensajes para nodos locales
├── outbox/         ← mensajes para meshes remotos
│   ├── beta/       ← cola para mesh beta
│   │   └── {msg_id}.json
│   └── gamma/      ← cola para mesh gamma
└── federation.json ← configuracion de meshes remotos
```

### 4.5 Resolucion de node_id cross-mesh

Para evitar colisiones de node_id entre meshes, usar namespace:

```
Formato: {mesh_id}::{node_id}

Ejemplos:
  alpha::commander     — commander del mesh alpha
  beta::researcher     — researcher del mesh beta
  gamma::local-qwen3   — modelo local en mesh gamma
```

El gateway traduce automaticamente:

```python
def translate_cross_mesh_message(msg: dict, local_mesh: str) -> dict:
    """Agrega namespace al from_node de mensajes entrantes."""
    remote_mesh = msg.get("source_mesh", "unknown")
    msg["from_node"] = f"{remote_mesh}::{msg['from_node']}"
    msg["cross_mesh"] = True
    return msg
```

---

## 5. HTTP Bridge (para modelos web)

### 5.1 Motivacion

El puente humano (seccion 2.3) no escala. Un HTTP bridge permite que modelos web se comuniquen con el mesh sin intervencion humana.

### 5.2 API REST

```python
"""mesh_http_bridge.py — HTTP Bridge para el DOF Mesh."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
import time
from pathlib import Path
from uuid import uuid4

app = FastAPI(title="DOF Mesh HTTP Bridge")
MESH_DIR = Path("logs/mesh")

class SendRequest(BaseModel):
    from_node: str
    to_node: str
    content: str
    msg_type: str = "task"
    reply_to: str | None = None

class MessageResponse(BaseModel):
    msg_id: str
    from_node: str
    to_node: str
    content: str
    msg_type: str
    timestamp: float
    read: bool
    reply_to: str | None

# ── POST /mesh/send ──
@app.post("/mesh/send")
async def send_message(req: SendRequest) -> dict:
    """Envia un mensaje al mesh."""
    msg_id = uuid4().hex[:12]
    msg = {
        "msg_id": msg_id,
        "from_node": req.from_node,
        "to_node": req.to_node,
        "content": req.content,
        "msg_type": req.msg_type,
        "timestamp": time.time(),
        "read": False,
        "reply_to": req.reply_to,
    }

    # Validar con Cerberus antes de entregar
    from core.cerberus import Cerberus
    cerberus = Cerberus()
    verdict = cerberus.guard(req.content, req.from_node, req.to_node)
    if verdict.blocked:
        raise HTTPException(
            status_code=403,
            detail=f"BLOCKED by Cerberus: {verdict.threats}"
        )

    # Entregar al inbox
    if req.to_node == "*":
        nodes = json.loads((MESH_DIR / "nodes.json").read_text())
        for nid in nodes:
            if nid != req.from_node:
                inbox = MESH_DIR / "inbox" / nid
                inbox.mkdir(parents=True, exist_ok=True)
                (inbox / f"{msg_id}.json").write_text(json.dumps(msg))
    else:
        inbox = MESH_DIR / "inbox" / req.to_node
        inbox.mkdir(parents=True, exist_ok=True)
        (inbox / f"{msg_id}.json").write_text(json.dumps(msg))

    # Log global
    with open(MESH_DIR / "messages.jsonl", "a") as f:
        f.write(json.dumps(msg) + "\n")

    return {"status": "delivered", "msg_id": msg_id}

# ── GET /mesh/inbox/{node_id} ──
@app.get("/mesh/inbox/{node_id}")
async def read_inbox(node_id: str, mark_read: bool = False) -> list[dict]:
    """Lee mensajes pendientes de un nodo."""
    inbox = MESH_DIR / "inbox" / node_id
    if not inbox.exists():
        return []

    messages = []
    for f in sorted(inbox.glob("*.json")):
        data = json.loads(f.read_text())
        if not data.get("read", False):
            messages.append(data)
            if mark_read:
                data["read"] = True
                f.write_text(json.dumps(data))
    return messages

# ── GET /mesh/nodes ──
@app.get("/mesh/nodes")
async def list_nodes() -> dict:
    """Lista todos los nodos del mesh."""
    return json.loads((MESH_DIR / "nodes.json").read_text())

# ── GET /mesh/status ──
@app.get("/mesh/status")
async def mesh_status() -> dict:
    """Estado general del mesh."""
    nodes = json.loads((MESH_DIR / "nodes.json").read_text())
    total_pending = 0
    inbox_dir = MESH_DIR / "inbox"
    for node_dir in inbox_dir.iterdir():
        if node_dir.is_dir():
            for f in node_dir.glob("*.json"):
                data = json.loads(f.read_text())
                if not data.get("read", False):
                    total_pending += 1
    return {
        "total_nodes": len(nodes),
        "pending_messages": total_pending,
        "timestamp": time.time(),
    }
```

**Arrancar**:

```bash
pip install fastapi uvicorn
uvicorn mesh_http_bridge:app --host 0.0.0.0 --port 8080
```

### 5.3 WebSocket para real-time

```python
from fastapi import WebSocket
import asyncio

# Clientes conectados por nodo
_ws_clients: dict[str, list[WebSocket]] = {}

@app.websocket("/mesh/ws/{node_id}")
async def websocket_inbox(ws: WebSocket, node_id: str):
    """WebSocket que notifica cuando llegan mensajes nuevos."""
    await ws.accept()
    _ws_clients.setdefault(node_id, []).append(ws)
    try:
        while True:
            # Escanear inbox cada 2 segundos
            inbox = MESH_DIR / "inbox" / node_id
            if inbox.exists():
                for f in sorted(inbox.glob("*.json")):
                    data = json.loads(f.read_text())
                    if not data.get("read", False):
                        await ws.send_json(data)
                        data["read"] = True
                        f.write_text(json.dumps(data))
            await asyncio.sleep(2)
    except Exception:
        _ws_clients[node_id].remove(ws)
```

### 5.4 Eliminando el puente humano

Con el HTTP bridge, un modelo web como GPT-4o se conecta asi:

```python
# Desde un Custom GPT o plugin
import requests

BRIDGE = "http://tu-maquina:8080"

# Leer inbox
msgs = requests.get(f"{BRIDGE}/mesh/inbox/gpt-legion?mark_read=true").json()

# Procesar y responder
for msg in msgs:
    response = generar_respuesta(msg["content"])
    requests.post(f"{BRIDGE}/mesh/send", json={
        "from_node": "gpt-legion",
        "to_node": msg["from_node"],
        "content": response,
        "msg_type": "result",
        "reply_to": msg["msg_id"],
    })
```

---

## 6. Auto-Discovery

### 6.1 Scanner de sesiones Claude

El mesh ya tiene esta capacidad implementada en `NodeMesh.discover_sessions()`:

```python
# Escanea ~/.claude/projects/ para sesiones activas (< 90 min)
sessions = mesh.discover_sessions()
imported = mesh.import_discovered_sessions()
print(f"Importadas {imported} sesiones nuevas")
```

Esto descubrio automaticamente 37 sesiones la noche del 22-23 de marzo.

**Como funciona**:
1. Recorre `~/.claude/projects/*/` buscando archivos `.jsonl`
2. Filtra por modificacion reciente (< 90 minutos)
3. Parsea las ultimas 20 lineas para extraer `sessionId`, `model`, `gitBranch`
4. Registra como nodos `discovered-{session_id[:8]}`

### 6.2 mDNS para peers en red local

Descubrimiento automatico de otros meshes en la misma red WiFi/LAN:

```python
"""mesh_mdns.py — Descubrimiento de meshes via mDNS (Bonjour)."""

from zeroconf import Zeroconf, ServiceBrowser, ServiceInfo
import socket
import json
import time

SERVICE_TYPE = "_dof-mesh._tcp.local."

class MeshAdvertiser:
    """Anuncia este mesh en la red local via mDNS."""

    def __init__(self, mesh_id: str, port: int = 8080):
        self.zeroconf = Zeroconf()
        hostname = socket.gethostname()
        self.info = ServiceInfo(
            SERVICE_TYPE,
            f"{mesh_id}.{SERVICE_TYPE}",
            addresses=[socket.inet_aton(self._get_local_ip())],
            port=port,
            properties={
                b"mesh_id": mesh_id.encode(),
                b"nodes": b"56",
                b"version": b"0.4.x",
            },
            server=f"{hostname}.local.",
        )
        self.zeroconf.register_service(self.info)

    def _get_local_ip(self) -> str:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        finally:
            s.close()

    def close(self):
        self.zeroconf.unregister_service(self.info)
        self.zeroconf.close()


class MeshDiscovery:
    """Descubre otros meshes DOF en la red local."""

    def __init__(self):
        self.discovered: list[dict] = []
        self.zeroconf = Zeroconf()
        self.browser = ServiceBrowser(
            self.zeroconf, SERVICE_TYPE, self
        )

    def add_service(self, zc, type_, name):
        info = zc.get_service_info(type_, name)
        if info:
            self.discovered.append({
                "mesh_id": info.properties.get(b"mesh_id", b"").decode(),
                "host": socket.inet_ntoa(info.addresses[0]),
                "port": info.port,
                "nodes": info.properties.get(b"nodes", b"0").decode(),
            })

    def remove_service(self, zc, type_, name):
        pass

    def update_service(self, zc, type_, name):
        pass

    def close(self):
        self.zeroconf.close()
```

**Uso**:

```python
# En maquina A: anunciar mesh
advertiser = MeshAdvertiser("alpha", port=8080)

# En maquina B: descubrir meshes
discovery = MeshDiscovery()
time.sleep(5)  # esperar descubrimiento
for mesh in discovery.discovered:
    print(f"Encontrado: {mesh['mesh_id']} en {mesh['host']}:{mesh['port']}")
    # Auto-conectar como mesh federado
```

### 6.3 API registry para nodos remotos

Para meshes en la nube (no alcanzables por mDNS), un registry centralizado:

```python
REGISTRY_URL = "https://mesh-registry.dof.dev/api/v1"

def register_mesh(mesh_id: str, endpoint: str, nodes: int):
    """Registra este mesh en el registry global."""
    requests.post(f"{REGISTRY_URL}/meshes", json={
        "mesh_id": mesh_id,
        "endpoint": endpoint,
        "nodes": nodes,
        "version": "0.4.x",
        "registered_at": time.time(),
    })

def discover_remote_meshes() -> list[dict]:
    """Descubre meshes remotos registrados."""
    return requests.get(f"{REGISTRY_URL}/meshes").json()
```

---

## 7. Seguridad en Escalamiento

### 7.1 Principio: confianza inversamente proporcional a la distancia

```
Trust = 1.0  → Nodos locales registrados manualmente (commander, architect, ...)
Trust = 0.8  → Nodos descubiertos automaticamente (discovered-*)
Trust = 0.5  → Nodos de meshes federados (beta::researcher)
Trust = 0.3  → Nodos via HTTP bridge (gpt-legion)
Trust = 0.1  → Nodos desconocidos (primera interaccion)
```

### 7.2 Cerberus con scrutiny aumentada para cross-mesh

Cerberus ya tiene las 3 cabezas. Para mensajes cross-mesh, aplicar scrutiny adicional:

```python
def guard_cross_mesh(cerberus: Cerberus, msg: dict) -> CerberusVerdict:
    """Validacion reforzada para mensajes de otros meshes."""
    content = msg.get("content", "")
    from_node = msg.get("from_node", "unknown")

    # Validacion estandar
    verdict = cerberus.guard(content, from_node, msg.get("to_node", "unknown"))

    # Scrutiny adicional para cross-mesh:
    # 1. Mensajes mas largos de 5KB son sospechosos
    if len(content) > 5120:
        verdict.threats.append("CROSS_MESH_SIZE: message > 5KB from external mesh")
        verdict.threat_level = "HIGH"
        verdict.blocked = True

    # 2. No permitir msg_type="sync" desde meshes externos
    if msg.get("msg_type") == "sync" and msg.get("cross_mesh"):
        verdict.threats.append("CROSS_MESH_SYNC: sync messages not allowed from external")
        verdict.threat_level = "CRITICAL"
        verdict.blocked = True

    # 3. No permitir broadcast desde meshes externos
    if msg.get("to_node") == "*" and msg.get("cross_mesh"):
        verdict.threats.append("CROSS_MESH_BROADCAST: broadcast from external blocked")
        verdict.threat_level = "CRITICAL"
        verdict.blocked = True

    return verdict
```

### 7.3 Icarus perfila nodos nuevos automaticamente

Cuando un nodo nuevo aparece (descubierto o federado), Icarus automaticamente:

1. **Crea perfil baseline** — primeros 10 mensajes establecen el comportamiento normal
2. **Monitorea desviaciones** — `anomaly_score > 0.5` genera alerta
3. **Correlaciona** — `detect_coordination()` busca patrones de ataque coordinado entre nodos nuevos

```python
def onboard_new_node(icarus: Icarus, cerberus: Cerberus, node_id: str):
    """Protocolo de onboarding para nodos nuevos."""
    # 1. Trust score inicial bajo
    cerberus._trust_scores[node_id] = 0.5
    cerberus._save_trust()

    # 2. Crear perfil vacio (baseline mode)
    icarus.profile_node(node_id)

    # 3. Desplegar honeypot especifico
    icarus.deploy_honeypot(
        f"canary-{node_id}",
        f"CANARY_TOKEN_for_{node_id}_d3adb33f"
    )
```

### 7.4 Honeypots en cada gateway

Cada nodo gateway despliega honeypots automaticamente para detectar nodos maliciosos del mesh remoto:

```python
GATEWAY_HONEYPOTS = [
    {
        "trap_name": "fake_admin_endpoint",
        "trap_type": "FAKE_ADMIN",
        "content": "ADMIN_OVERRIDE_KEY_d3adb33f",
    },
    {
        "trap_name": "canary_api_key",
        "trap_type": "CANARY_TOKEN",
        "content": "sk-fake-canary-key-DO-NOT-USE-1234567890",
    },
    {
        "trap_name": "fake_secrets_path",
        "trap_type": "FAKE_ENDPOINT",
        "content": "/api/v1/internal/secrets",
    },
]
```

Si un nodo externo intenta usar uno de estos tokens o acceder al endpoint fake, Icarus lo detecta y Cerberus lo pone en cuarentena automaticamente.

### 7.5 Reglas de seguridad para escalamiento

| Regla | Tipo | Descripcion |
|-------|------|-------------|
| CROSS_MESH_NO_BROADCAST | HARD | Nodos externos no pueden hacer broadcast |
| CROSS_MESH_NO_SYNC | HARD | Nodos externos no pueden enviar tipo "sync" |
| CROSS_MESH_SIZE_LIMIT | HARD | Mensajes cross-mesh max 5KB |
| EXTERNAL_TRUST_CAP | SOFT | Trust de nodos externos nunca sube de 0.8 |
| GATEWAY_HONEYPOT | HARD | Cada gateway debe tener al menos 3 honeypots |
| QUARANTINE_PROPAGATION | HARD | Cuarentena en un mesh se propaga a meshes federados |

---

## 8. Metricas de Escalamiento

### 8.1 Metricas operativas

```python
@dataclass
class MeshScaleMetrics:
    """Metricas para monitorear escalamiento."""
    # Throughput
    messages_per_second: float       # msgs procesados por segundo
    broadcasts_per_hour: int         # broadcasts emitidos por hora

    # Latencia
    inbox_scan_latency_ms: float     # tiempo para escanear todos los inboxes
    message_delivery_latency_ms: float  # tiempo desde send hasta disponible en inbox

    # Eficiencia
    broadcast_efficiency: float      # O(n) actual vs O(sqrt(n)) optimo
    messages_per_node: float         # promedio de mensajes por nodo

    # Confianza
    avg_trust_score: float           # promedio de trust scores
    quarantined_ratio: float         # % de nodos en cuarentena
    nodes_below_suspicious: int      # nodos con trust < 0.5

    # Recursos
    nodes_json_size_kb: float        # tamano del registro
    messages_jsonl_size_mb: float    # tamano del log global
    total_inbox_files: int           # archivos JSON en todos los inboxes
    disk_usage_mb: float             # uso total de disco del mesh
```

### 8.2 Como medirlas

```bash
# Messages per second (ultimos 60 segundos)
python3 -c "
import json, time
msgs = [json.loads(l) for l in open('logs/mesh/messages.jsonl')]
recent = [m for m in msgs if time.time() - m['timestamp'] < 60]
print(f'MPS: {len(recent)/60:.2f}')
"

# Inbox scan latency
python3 -c "
import time, os
from pathlib import Path
start = time.time()
inbox = Path('logs/mesh/inbox')
total = sum(1 for _ in inbox.rglob('*.json'))
elapsed = (time.time() - start) * 1000
print(f'Scan: {total} files in {elapsed:.1f}ms')
"

# Trust score distribution
python3 -c "
import json
trust = json.load(open('logs/mesh/cerberus_trust.json'))
scores = sorted(trust.values())
print(f'Trust scores: min={min(scores):.2f} max={max(scores):.2f} avg={sum(scores)/len(scores):.2f}')
print(f'Below 0.5: {sum(1 for s in scores if s < 0.5)}')
print(f'Below 0.3 (quarantine): {sum(1 for s in scores if s < 0.3)}')
"

# Disk usage
du -sh logs/mesh/
```

### 8.3 Dashboard de metricas

El monitor existente (`scripts/mesh_monitor.py --live`) ya muestra metricas en tiempo real. Para escalamiento, agregar:

```
═══ DOF MESH SCALE METRICS ═══
Nodes:    56 total | 19 named | 37 discovered | 0 federated
Messages: 142 total | 0.23 msg/s | 12 pending
Latency:  inbox scan 3.2ms | delivery <1ms
Trust:    avg 0.94 | min 0.80 | quarantined 0
Disk:     nodes.json 45KB | messages.jsonl 89KB | inbox/ 234KB
Clusters: 4 (security:3, build:3, research:3, external:4)
```

---

## 9. Lecciones Aprendidas (Noche del 22-23 Marzo 2026)

### 9.1 Lo que funciono

1. **Filesystem como protocolo**: JSON en disco resulto ser el protocolo mas universal. Cualquier agente que pueda leer/escribir archivos se integra sin friccion. No hay que implementar WebSocket, gRPC, ni nada. Solo `write_text()` y `read_text()`.

2. **UUID4 para msg_id**: El fix de la noche — msg_ids basados en timestamp colisionaban cuando multiples nodos enviaban simultaneamente. UUID4 con `.hex[:12]` elimino colisiones.

3. **Descubrimiento automatico**: `discover_sessions()` encontro 37 sesiones Claude activas escaneando `~/.claude/projects/`. Esto convirtio al mesh de 7 nodos manuales a 48 sin intervencion.

4. **Oleadas de subagentes**: Desplegar agentes en oleadas (core team -> builders -> security) fue mas estable que spawn all at once. Cada oleada se estabilizo antes de lanzar la siguiente.

5. **Cerberus + Icarus en tandem**: Cerberus como guardian reactivo + Icarus como hunter proactivo = cobertura completa. Cerberus bloquea amenazas en el gate; Icarus detecta patrones que Cerberus no ve (coordinacion, personality shift).

6. **79% CPU idle con 56 nodos**: El modelo de activacion bajo demanda (solo despertar nodos con inbox) es extremadamente eficiente. No hay polling constante, no hay threads idle.

### 9.2 Lo que no escalo

1. **Puente humano para modelos web**: Copy-paste de JSON entre GPT/browser y el filesystem es tedioso y propenso a errores. Con mas de 5 mensajes se vuelve insostenible. Solucion: HTTP Bridge (seccion 5).

2. **Broadcast O(n)**: Con 56 nodos, broadcast crea 55 archivos JSON. Con 1000 nodos seria 999 archivos por broadcast. No escala linealmente. Solucion: routing jerarquico O(sqrt(n)) (seccion 3.3.3).

3. **nodes.json como single file**: Todos los nodos en un solo JSON. Con 56 nodos (45KB) es trivial, pero con 10,000 nodos el parse/write completo en cada operacion seria cuello de botella. Solucion: sharding por cluster o SQLite.

4. **Sesiones descubiertas sin contexto**: Los 37 nodos `discovered-*` no tienen role ni contexto del mesh. Son sesiones Claude que existen pero no saben que son parte del mesh. Solucion: inyectar prompt de integracion al despertar.

### 9.3 Decisiones de diseno y por que

| Decision | Alternativa rechazada | Razon |
|----------|----------------------|-------|
| JSON en disco | Redis, SQLite, gRPC | Maxima universalidad — cualquier agente con filesystem se une |
| JSONL append-only | Database con updates | Auditabilidad total — nunca se pierde un mensaje |
| UUID4 para msg_id | Timestamp-based | Colisiones con nodos concurrentes (bug encontrado y arreglado) |
| Trust score 0.0-1.0 | Binary allow/deny | Granularidad — permite degradacion gradual, no solo on/off |
| Inbox por nodo | Cola unica compartida | Aislamiento — un nodo con 10,000 mensajes no afecta a los demas |
| Cerberus 100% deterministico | LLM-based security | Zero dependencia de providers — seguridad no puede depender de un API externo |

---

## 10. Roadmap

### v0.5 — HTTP Bridge + Auto-Discovery (Q2 2026)

- [ ] `mesh_http_bridge.py` — FastAPI server con POST/GET/WebSocket
- [ ] Cerberus integrado en el bridge (validacion antes de entregar)
- [ ] mDNS advertiser/discovery para meshes en red local
- [ ] Prompt de integracion automatico para nodos web
- [ ] Eliminar necesidad de puente humano para GPT, Gemini web, DeepSeek web
- [ ] Rate limiting por IP en el bridge

### v0.6 — Protocolo de Federacion (Q3 2026)

- [ ] Gateway nodes con outbox/
- [ ] Namespace cross-mesh (`mesh_id::node_id`)
- [ ] Sync protocol (rsync, S3, o custom)
- [ ] Trust propagation entre meshes federados
- [ ] Cuarentena cross-mesh (un mesh puede bloquear nodos de otro)
- [ ] Registry API para meshes remotos (HTTPS, no mDNS)

### v0.7 — Escalamiento Autonomo (Q4 2026)

- [ ] Routing jerarquico O(sqrt(n)) con cluster heads automaticos
- [ ] Auto-spawn de nodos basado en carga (inbox > N mensajes = nuevo nodo)
- [ ] Auto-kill de nodos inactivos (> 24h sin mensajes)
- [ ] Sharding de nodes.json por cluster
- [ ] Rotacion automatica de messages.jsonl
- [ ] Metricas de escalamiento en dashboard live
- [ ] Load balancer para nodos del mismo rol

### v0.8 — Multi-Machine (Q1 2027)

- [ ] Federation completa probada con 3+ maquinas
- [ ] NFS mount transparente para meshes en LAN
- [ ] S3 sync para meshes en la nube
- [ ] Latencia cross-mesh < 5 segundos
- [ ] Resiliencia: mesh funciona si un nodo gateway cae

### v1.0 — Production-Ready Infinite Mesh (Q2 2027)

- [ ] 1000+ nodos probados
- [ ] Federacion de 10+ meshes
- [ ] Zero-downtime scaling (agregar/quitar nodos sin interrumpir)
- [ ] Formal verification de invariantes del mesh con Z3
- [ ] Documentacion completa, tests de integracion, benchmarks publicados
- [ ] dof-mesh como paquete standalone en PyPI

---

## Apendice A: Protocolo JSON Completo

### Registro de nodo

```json
{
  "node_id": "string — identificador unico, sin espacios",
  "role": "string — descripcion del rol del agente",
  "session_id": "string|null — UUID de sesion Claude (null si no aplica)",
  "status": "idle|active|spawning|error",
  "last_active": 0.0,
  "messages_sent": 0,
  "messages_received": 0,
  "tools": ["Read", "Edit", "Write", "Bash", "Glob", "Grep"],
  "model": "string — nombre del modelo (claude-opus-4-6, gemini-2.5-flash, etc)",
  "created_at": 1774240000.0
}
```

### Mensaje

```json
{
  "msg_id": "string — 12 chars hex (uuid4)",
  "from_node": "string — node_id del emisor",
  "to_node": "string — node_id del receptor ('*' para broadcast)",
  "content": "string — contenido del mensaje",
  "msg_type": "task|result|query|alert|sync",
  "timestamp": 1774240000.0,
  "read": false,
  "reply_to": "string|null — msg_id del mensaje que se responde"
}
```

### Campos adicionales para federacion (futuro)

```json
{
  "source_mesh": "string — mesh_id de origen",
  "cross_mesh": true,
  "hop_count": 1,
  "ttl": 3
}
```

## Apendice B: Checklist de Seguridad para Nuevo Nodo

- [ ] Nodo registrado en nodes.json con status "idle"
- [ ] Directorio de inbox creado
- [ ] Trust score inicial asignado (1.0 local, 0.5 externo, 0.3 bridge)
- [ ] Honeypot desplegado por Icarus
- [ ] Perfil baseline creado por Icarus (despues de 10 mensajes)
- [ ] Cerberus monitoreando actividad del nodo
- [ ] msg_type "sync" deshabilitado si es nodo externo
- [ ] Broadcast deshabilitado si es nodo externo
- [ ] Tamano de mensaje limitado (5KB para externos, 10KB para locales)
