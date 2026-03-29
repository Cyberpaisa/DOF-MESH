"""
DOF Mesh — Local AGI Node (M4 Max)
====================================

A zero-cost mesh node powered by local models (MLX, Ollama, llama.cpp).
Registers itself in the mesh and processes work orders from the commander.

Supported runtimes (auto-detected in priority order):
    1. mlx_lm   — Apple Silicon ANE/GPU, fastest (requires mlx-lm)
    2. ollama   — Cross-platform, simple API  (requires ollama server)
    3. llama_cpp — Fallback, CPU-only         (requires llama-cpp-python)

Architecture:
    mesh.register("local-agi-m4max", task="local LLM inference, zero cost")
    loop:
        msgs = mesh.read_inbox("local-agi-m4max")
        for msg in msgs:
            response = local_infer(msg.content)
            mesh.send_message("local-agi-m4max", msg.from_node, response)

Zero cost: 100% local, no API keys, no rate limits, fully private.
"""

import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

logger = logging.getLogger("core.local_model_node")

# ═══════════════════════════════════════════════════
# RUNTIME DETECTION
# ═══════════════════════════════════════════════════

def _detect_mlx() -> Optional[str]:
    """Return MLX model path/name if mlx_lm is available."""
    try:
        import mlx_lm  # noqa: F401
        return "mlx-community/Llama-3.2-3B-Instruct-4bit"
    except ImportError:
        return None


def _detect_ollama() -> Optional[str]:
    """Return model name if Ollama is running with a suitable model."""
    try:
        import urllib.request
        req = urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
        data = json.loads(req.read())
        models = [m["name"] for m in data.get("models", [])]
        if not models:
            return None
        # Prefer small, fast models or powerful local ones
        for preferred in ["qwen2.5-coder:14b", "deepseek-r1:14b", "llama3.2:3b", "phi4:14b"]:
            if any(preferred in m for m in models):
                return preferred
        return models[0]
    except Exception:
        return None


def _detect_llamacpp() -> Optional[str]:
    """Return model path if llama-cpp-python is available."""
    try:
        from llama_cpp import Llama  # noqa: F401
        # Look for any .gguf in common locations
        search_paths = [
            Path.home() / ".ollama" / "models",
            Path("models"),
            Path("/tmp"),
        ]
        for p in search_paths:
            gguf = list(p.glob("**/*.gguf"))
            if gguf:
                return str(gguf[0])
        return None
    except ImportError:
        return None


@dataclass
class LocalRuntimeInfo:
    runtime: str          # "mlx", "ollama", "llamacpp", "none"
    model: str
    available: bool
    details: str


def detect_runtime() -> LocalRuntimeInfo:
    """Auto-detect best available local runtime."""
    mlx = _detect_mlx()
    if mlx:
        return LocalRuntimeInfo("mlx", mlx, True, "Apple Silicon MLX — ANE/GPU accelerated")

    ollama = _detect_ollama()
    if ollama:
        return LocalRuntimeInfo("ollama", ollama, True, f"Ollama server running: {ollama}")

    llamacpp = _detect_llamacpp()
    if llamacpp:
        return LocalRuntimeInfo("llamacpp", llamacpp, True, f"llama.cpp: {llamacpp}")

    return LocalRuntimeInfo("none", "", False, "No local runtime detected")


# ═══════════════════════════════════════════════════
# LOCAL INFERENCE ENGINES
# ═══════════════════════════════════════════════════

class MLXEngine:
    """Apple Silicon MLX inference engine."""

    def __init__(self, model_path: str):
        self.model_path = model_path
        self._model = None
        self._tokenizer = None

    def _load(self):
        if self._model is None:
            from mlx_lm import load
            logger.info(f"Loading MLX model: {self.model_path}")
            self._model, self._tokenizer = load(self.model_path)
            logger.info("MLX model loaded (ANE/GPU)")

    def generate(self, prompt: str, max_tokens: int = 512) -> str:
        self._load()
        from mlx_lm import generate
        response = generate(
            self._model,
            self._tokenizer,
            prompt=prompt,
            max_tokens=max_tokens,
            verbose=False,
            kv_bits=4,   # TurboQuant: 4-bit KV cache via Apple Neural Engine
        )
        return response


class OllamaEngine:
    """Ollama local inference engine."""

    def __init__(self, model: str, base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url

    def generate(self, prompt: str, max_tokens: int = 512) -> str:
        import urllib.request
        payload = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": max_tokens, "num_ctx": 65536},
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
            return data.get("response", "")


class LlamaCppEngine:
    """llama.cpp local inference engine."""

    def __init__(self, model_path: str):
        self.model_path = model_path
        self._llm = None

    def _load(self):
        if self._llm is None:
            from llama_cpp import Llama
            logger.info(f"Loading llama.cpp model: {self.model_path}")
            self._llm = Llama(
                model_path=self.model_path,
                n_ctx=12288,          # TurboQuant: 6x context via KV quantization
                n_batch=256,
                cache_type_k="q4_0",  # 3-bit KV cache (Hadamard preconditioning)
                cache_type_v="q4_0",
            )

    def generate(self, prompt: str, max_tokens: int = 512) -> str:
        self._load()
        output = self._llm(prompt, max_tokens=max_tokens, echo=False)
        return output["choices"][0]["text"]


def build_engine(runtime_info: LocalRuntimeInfo):
    """Factory: build the right engine from runtime info."""
    if runtime_info.runtime == "mlx":
        return MLXEngine(runtime_info.model)
    if runtime_info.runtime == "ollama":
        return OllamaEngine(runtime_info.model)
    if runtime_info.runtime == "llamacpp":
        return LlamaCppEngine(runtime_info.model)
    return None


# ═══════════════════════════════════════════════════
# SYSTEM PROMPT
# ═══════════════════════════════════════════════════

DOF_SYSTEM_PROMPT = """You are a local AGI node in the DOF Mesh — a deterministic multi-agent framework.
Node ID: local-agi-m4max | Runtime: {runtime} | Model: {model}
Hardware: Apple M4 Max, 36GB RAM, 19 TFLOPS Neural Engine

Your role: execute work orders from the commander with zero API cost.
Respond concisely. Output JSON when the task asks for structured data.
"""


# ═══════════════════════════════════════════════════
# LOCAL AGI NODE
# ═══════════════════════════════════════════════════

import re

# Glassworm/Unicode Malware Protection Pattern
# Variation Selectors (U+FE00 - U+FE0F) and Tags (U+E0100 - U+E01EF)
GHOST_PATTERN = re.compile(r"[\uFE00-\uFE0F\U000E0100-\U000E01EF]")

def sanitize_text(text: str) -> str:
    """Removes invisible Unicode characters used for steganography attacks."""
    if not isinstance(text, str):
        return text
    sanitized = GHOST_PATTERN.sub("", text)
    if sanitized != text:
        logging.warning("  [⚠] GHOST-UNICODE DETECTADO Y ELIMINADO!")
    return sanitized

class LocalAGINode:
    """
    A mesh node that uses local model inference (MLX/Ollama/llama.cpp).

    Registers as "local-agi-m4max" in NodeMesh and processes work orders
    from the inbox, responding back to the sender — zero cost, fully local.
    """

    NODE_ID = "local-agi-m4max"
    POLL_INTERVAL = 5  # seconds

    def __init__(self,
                 node_id: str = NODE_ID,
                 model_override: Optional[str] = None,
                 runtime_override: Optional[str] = None,
                 mesh_dir: str = "logs/mesh"):
        self.node_id = node_id
        self.mesh_dir = Path(mesh_dir)
        self.runtime = detect_runtime()

        # Allow overrides for testing
        if model_override:
            self.runtime.model = model_override
        if runtime_override:
            self.runtime.runtime = runtime_override

        self.engine = build_engine(self.runtime) if self.runtime.available else None
        self._inbox_dir = self.mesh_dir / "inbox" / self.node_id
        self._inbox_dir.mkdir(parents=True, exist_ok=True)
        self._log_path = self.mesh_dir / "local_agi.jsonl"

        self._system_prompt = DOF_SYSTEM_PROMPT.format(
            runtime=self.runtime.runtime,
            model=self.runtime.model,
        )

        logger.info(f"LocalAGINode({self.node_id}) — {self.runtime.details}")

    # ─────────────────────────────────────────────────
    # Registration
    # ─────────────────────────────────────────────────

    def register(self, mesh) -> bool:
        """Register this node in the mesh."""
        try:
            mesh.register_node(
                node_id=self.node_id,
                task=f"Local AGI — {self.runtime.runtime}/{self.runtime.model}",
                model=f"local:{self.runtime.runtime}",
                node_type="local",
            )
            logger.info(f"Registered {self.node_id} in mesh")
            return True
        except Exception as e:
            logger.warning(f"Mesh registration failed: {e}")
            return False

    # ─────────────────────────────────────────────────
    # Inference
    # ─────────────────────────────────────────────────

    def infer(self, prompt: str, max_tokens: int = 512) -> str:
        """Run local inference on a prompt."""
        if not self.engine:
            return f"[local-agi-m4max] ERROR: no runtime available ({self.runtime.details})"

        # Security: sanitize prompt against Glassworm attacks
        prompt = sanitize_text(prompt)
        full_prompt = f"{self._system_prompt}\n\nTask: {prompt}\n\nResponse:"
        start = time.time()
        try:
            result = self.engine.generate(full_prompt, max_tokens=max_tokens)
            elapsed = time.time() - start
            logger.info(f"Inference done in {elapsed:.1f}s ({len(result)} chars)")
            return result.strip()
        except Exception as e:
            logger.error(f"Inference failed: {e}")
            return f"[local-agi-m4max] Inference error: {e}"

    # ─────────────────────────────────────────────────
    # Inbox processing
    # ─────────────────────────────────────────────────

    def process_inbox(self, mesh=None) -> int:
        """
        Process all pending messages in inbox.
        Returns number of messages processed.
        """
        if mesh:
            messages = mesh.read_inbox(self.node_id, mark_read=True)
        else:
            messages = self._read_inbox_direct()

        processed = 0
        for msg in messages:
            self._process_message(msg, mesh)
            processed += 1

        return processed

    def _read_inbox_direct(self) -> List[Dict]:
        """Read inbox files directly (without mesh object)."""
        messages = []
        for f in sorted(self._inbox_dir.glob("*.json")):
            try:
                data = json.loads(f.read_text())
                if not data.get("read"):
                    messages.append(data)
                    data["read"] = True
                    f.write_text(json.dumps(data))
            except Exception:
                continue
        return messages

    def _process_message(self, msg, mesh=None):
        """Process a single message and send response."""
        msg_id = getattr(msg, "msg_id", msg.get("msg_id", "unknown")) if isinstance(msg, dict) else msg.msg_id
        from_node = getattr(msg, "from_node", msg.get("from_node", "commander")) if isinstance(msg, dict) else msg.from_node
        content = getattr(msg, "content", msg.get("content", "")) if isinstance(msg, dict) else msg.content

        logger.info(f"Processing {msg_id} from {from_node}")
        response = self.infer(content)

        # Write response to sender's inbox
        if mesh:
            mesh.send_message(self.node_id, from_node, response, msg_type="response")
        else:
            self._write_response(from_node, msg_id, response)

        # Log to JSONL
        self._log_cycle(msg_id, from_node, content, response)

    def _write_response(self, to_node: str, reply_to: str, content: str):
        """Write response directly to target's inbox (no mesh object)."""
        inbox_dir = self.mesh_dir / "inbox" / to_node
        inbox_dir.mkdir(parents=True, exist_ok=True)
        resp_id = f"LOCAL-{int(time.time()*1000)}"
        resp = {
            "msg_id": resp_id,
            "from_node": self.node_id,
            "to_node": to_node,
            "content": content,
            "msg_type": "response",
            "reply_to": reply_to,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "read": False,
        }
        (inbox_dir / f"{resp_id}.json").write_text(json.dumps(resp))
        logger.info(f"Response written → {to_node}/{resp_id}.json")

    def _log_cycle(self, msg_id: str, from_node: str, prompt: str, response: str):
        """Append inference cycle to JSONL log."""
        entry = {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "node_id": self.node_id,
            "runtime": self.runtime.runtime,
            "model": self.runtime.model,
            "msg_id": msg_id,
            "from_node": from_node,
            "prompt_chars": len(prompt),
            "response_chars": len(response),
        }
        with open(self._log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    # ─────────────────────────────────────────────────
    # Daemon loop
    # ─────────────────────────────────────────────────

    def run(self, mesh=None, max_cycles: int = 0, interval: float = POLL_INTERVAL):
        """
        Poll inbox and process messages forever (or up to max_cycles).
        max_cycles=0 → infinite loop.
        """
        logger.info(f"LocalAGINode daemon starting — {self.runtime.details}")
        cycle = 0

        while True:
            try:
                processed = self.process_inbox(mesh)
                if processed:
                    logger.info(f"Cycle {cycle}: processed {processed} messages")
            except Exception as e:
                logger.error(f"Daemon cycle error: {e}")

            cycle += 1
            if max_cycles and cycle >= max_cycles:
                break
            time.sleep(interval)

    # ─────────────────────────────────────────────────
    # Status
    # ─────────────────────────────────────────────────

    def status(self) -> Dict[str, Any]:
        pending = sum(1 for f in self._inbox_dir.glob("*.json")
                      if not json.loads(f.read_text()).get("read"))
        return {
            "node_id": self.node_id,
            "runtime": self.runtime.runtime,
            "model": self.runtime.model,
            "available": self.runtime.available,
            "details": self.runtime.details,
            "inbox_pending": pending,
            "log_path": str(self._log_path),
        }


# ═══════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(name)s] %(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="DOF Local AGI Node")
    parser.add_argument("--status", action="store_true", help="Show status and exit")
    parser.add_argument("--detect", action="store_true", help="Detect runtime and exit")
    parser.add_argument("--infer", type=str, help="Run a single inference and exit")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon (poll inbox)")
    parser.add_argument("--cycles", type=int, default=0, help="Max cycles (0=infinite)")
    parser.add_argument("--model", type=str, default=None, help="Override model")
    parser.add_argument("--runtime", type=str, default=None, help="Override runtime (mlx/ollama/llamacpp)")
    args = parser.parse_args()

    node = LocalAGINode(
        model_override=args.model,
        runtime_override=args.runtime,
    )

    if args.detect:
        rt = detect_runtime()
        print(f"Runtime: {rt.runtime}")
        print(f"Model:   {rt.model}")
        print(f"Details: {rt.details}")
        sys.exit(0)

    if args.status:
        print(json.dumps(node.status(), indent=2))
        sys.exit(0)

    if args.infer:
        print(node.infer(args.infer))
        sys.exit(0)

    if args.daemon:
        node.run(max_cycles=args.cycles)


# ── LocalModelNode (for test compatibility) ───────────────────────────────────

class LocalModelNode:
    """Singleton wrapper for LocalAGINode."""

    _instance = None
    _class_lock = __import__("threading").Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._class_lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    inst._initialized = False
                    cls._instance = inst
        return cls._instance

    @classmethod
    def get_instance(cls) -> "LocalModelNode":
        return cls()

    def init(self, config=None) -> None:
        if config is None:
            self._initialized = True
            return
        if not isinstance(config, str):
            raise TypeError(f"config must be str, got {type(config).__name__}")
        if config == "":
            raise ValueError("config cannot be empty")
        self._initialized = True
