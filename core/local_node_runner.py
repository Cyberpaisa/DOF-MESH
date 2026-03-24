import os
import json
import time
import requests
from pathlib import Path
from dataclasses import asdict
from typing import List

# Import mesh components
from core.node_mesh import NodeMesh, MeshMessage

# --- CONFIGURATION ---
LOCAL_NODES = ["local-qwen", "local-agi-m4max"]
OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
POLL_INTERVAL = 5  # seconds
REPO_ROOT = Path(__file__).parent.parent

# --- Cargar SOUL.md como contexto canónico ---
def _load_soul(node_id: str) -> str:
    soul_path = REPO_ROOT / "agents" / node_id / "SOUL.md"
    if soul_path.exists():
        return soul_path.read_text(encoding="utf-8")
    # Fallback genérico
    return f"Eres {node_id}, nodo de código del DOF Mesh. Repo: {REPO_ROOT}. Stack Python 3.13."

SOULS = {node: _load_soul(node) for node in LOCAL_NODES}

def call_ollama(model: str, prompt: str, node_id: str = "local-agi-m4max") -> str:
    """Call local Ollama /api/chat con SOUL.md como system prompt."""
    soul = SOULS.get(node_id, SOULS.get("local-agi-m4max", ""))
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": soul},
            {"role": "user",   "content": prompt},
        ],
        "options": {"temperature": 0.1, "num_predict": 600},
    }
    try:
        response = requests.post(OLLAMA_CHAT_URL, json=payload, timeout=90)
        response.raise_for_status()
        data = response.json()
        return data.get("message", {}).get("content", "").strip() or data.get("response", "")
    except Exception as e:
        return f"Error calling Ollama: {e}"

def run_runner():
    print(f"🚀 DOF Local Node Runner activo para: {', '.join(LOCAL_NODES)}")
    mesh = NodeMesh(cwd=os.getcwd())
    
    while True:
        for node_id in LOCAL_NODES:
            # Check for unread messages in inbox
            messages = mesh.read_inbox(node_id, mark_read=True)
            for msg in messages:
                if msg.msg_type == "task":
                    print(f"📥 [{node_id}] Procesando tarea de {msg.from_node}...")
                    
                    # Get model from node registry (fallback to default)
                    node = mesh.get_node(node_id)
                    model = node.model if node else "qwen2.5-coder:14b"
                    if ":" not in model: # Handle naming variations
                        model = f"{model}" 
                    
                    # Execute via Ollama con SOUL context
                    response_text = call_ollama(model, msg.content, node_id)
                    
                    # Send response back
                    mesh.send_message(
                        from_node=node_id,
                        to_node=msg.from_node,
                        content=response_text,
                        msg_type="response",
                        reply_to=msg.msg_id
                    )
                    print(f"📤 [{node_id}] Respuesta enviada.")
        
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    run_runner()


# ── LocalNodeRunner (for test compatibility) ──────────────────────────────────

class LocalNodeRunner:
    """Singleton runner for local Ollama/MLX nodes."""

    _instance = None
    _class_lock = __import__("threading").Lock()
    _SENTINEL = object()

    def __new__(cls, arg=_SENTINEL):
        if arg is not cls._SENTINEL:
            raise TypeError(f"LocalNodeRunner() takes no arguments, got {type(arg).__name__}")
        if cls._instance is None:
            with cls._class_lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    inst.is_running = False
                    cls._instance = inst
        return cls._instance

    def __init__(self, arg=None):
        pass

    def run_node(self) -> None:
        """Internal: start the node (patchable)."""
        self.is_running = True

    def stop_node(self) -> None:
        """Internal: stop the node (patchable)."""
        self.is_running = False

    def run(self) -> None:
        self.run_node()

    def stop(self) -> None:
        self.stop_node()
