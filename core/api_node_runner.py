"""
API Node Runner — DOF Mesh Legion.

Daemon que lee tareas JSON de logs/mesh/inbox/{node_id}/*.json,
llama la API del provider correspondiente y escribe la respuesta.

Providers soportados:
  - OpenAI-compatible (DeepSeek, Cerebras, SambaNova, NVIDIA, GLM-5)
  - Gemini Native (gemini-flash, antigravity)
  - Ollama Local (local-agi-m4max)

Usage:
  python3 core/api_node_runner.py --nodes deepseek-coder cerebras-llama --daemon
  python3 core/api_node_runner.py --once
"""

import argparse
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError

# ── Paths ─────────────────────────────────────────────────────────────────────
REPO_ROOT  = Path(__file__).resolve().parent.parent
INBOX_ROOT = REPO_ROOT / "logs" / "mesh" / "inbox"
LOGS_DIR   = REPO_ROOT / "logs" / "mesh"

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] api-runner — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("core.api_node_runner")

# ── Provider config: (base_url, model, api_key_env) ───────────────────────────
PROVIDERS: dict[str, tuple[str, str, str]] = {
    "deepseek-coder":   ("https://api.deepseek.com/v1",                        "deepseek-coder",                       "DEEPSEEK_API_KEY"),
    "cerebras-llama":   ("https://api.cerebras.ai/v1",                         "llama3.1-70b",                         "CEREBRAS_API_KEY"),
    "sambanova-llama":  ("https://api.sambanova.ai/v1",                        "Meta-Llama-3.3-70B-Instruct",          "SAMBANOVA_API_KEY"),
    "nvidia-nim":       ("https://integrate.api.nvidia.com/v1",                "meta/llama-3.3-70b-instruct",          "NVIDIA_API_KEY"),
    "glm-5":            ("https://open.bigmodel.cn/api/paas/v4",               "glm-5",                                "ZHIPU_API_KEY"),
    "hermes-405b":      ("https://api.cerebras.ai/v1",                         "llama3.1-70b",                         "CEREBRAS_API_KEY"),
    "gemini-flash":     ("GEMINI_NATIVE",                                       "gemini-2.5-flash",                     "GEMINI_API_KEY"),
    "antigravity":      ("GEMINI_NATIVE",                                       "gemini-2.5-pro",                       "GEMINI_API_KEY"),
    "antigraviti":      ("GEMINI_NATIVE",                                       "gemini-2.5-flash",                     "GEMINI_API_KEY"),
    "gemini-2":         ("GEMINI_NATIVE",                                       "gemini-2.5-flash",                     "GEMINI_API_KEY"),
    "gemini-web":       ("GEMINI_NATIVE",                                       "gemini-2.5-flash",                     "GEMINI_API_KEY"),
    "minimax":          ("https://api.sambanova.ai/v1",                        "Meta-Llama-3.3-70B-Instruct",          "SAMBANOVA_API_KEY"),
    "groq-llama":       ("https://api.groq.com/openai/v1",                     "llama-3.3-70b-versatile",              "GROQ_API_KEY"),
    "local-agi-m4max":  ("OLLAMA_LOCAL",                                        "local-agi-m4max:latest",               ""),
}

POLL_INTERVAL = 15   # segundos entre polls
MAX_TOKENS    = 2048
TEMPERATURE   = 0.2


def _load_env() -> None:
    """Carga variables de .env si existe."""
    env_file = REPO_ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            if k.strip() not in os.environ:
                os.environ[k.strip()] = v.strip()


def _http_post(url: str, payload: dict, headers: dict, timeout: int = 60) -> dict:
    """HTTP POST usando urllib (stdlib only)."""
    body = json.dumps(payload).encode()
    req = urllib_request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib_request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        body_txt = e.read().decode()[:300]
        raise RuntimeError(f"[ERROR {e.code}] {body_txt}")
    except URLError as e:
        raise RuntimeError(f"[ERROR URL] {e.reason}")


def _call_openai_compat(base_url: str, model: str, api_key: str,
                         prompt: str, node_id: str) -> str:
    """Llama API compatible con OpenAI."""
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Content-Type":  "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE,
    }
    data = _http_post(url, payload, headers)
    return data["choices"][0]["message"]["content"].strip()


def _call_gemini(model: str, prompt: str, api_key: str, node_id: str) -> str:
    """Llama Gemini API nativa."""
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{model}:generateContent?key={api_key}")
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": MAX_TOKENS, "temperature": TEMPERATURE},
    }
    data = _http_post(url, payload, headers)
    candidates = data.get("candidates", [])
    if not candidates:
        raise RuntimeError("Gemini returned no candidates")
    return candidates[0]["content"]["parts"][0]["text"].strip()


def _call_ollama(model: str, prompt: str, node_id: str) -> str:
    """Llama Ollama local."""
    url = "http://localhost:11434/api/chat"
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": TEMPERATURE, "num_predict": MAX_TOKENS},
    }
    data = _http_post(url, payload, headers, timeout=120)
    return (data.get("message", {}).get("content") or data.get("response", "")).strip()


def call_provider(node_id: str, prompt: str) -> str:
    """Despacha al provider correcto según node_id."""
    if node_id not in PROVIDERS:
        raise ValueError(f"Provider desconocido: {node_id}")

    base_url, model, key_env = PROVIDERS[node_id]
    api_key = os.environ.get(key_env, "") if key_env else ""

    if base_url == "OLLAMA_LOCAL":
        return _call_ollama(model, prompt, node_id)
    elif base_url == "GEMINI_NATIVE":
        if not api_key:
            raise RuntimeError(f"GEMINI_API_KEY no configurada")
        return _call_gemini(model, prompt, api_key, node_id)
    else:
        if not api_key:
            raise RuntimeError(f"{key_env} no configurada")
        return _call_openai_compat(base_url, model, api_key, prompt, node_id)


def process_task(node_id: str, task_file: Path) -> bool:
    """Lee tarea JSON, llama provider, escribe respuesta. Retorna True si OK."""
    try:
        task = json.loads(task_file.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error("No se pudo leer %s: %s", task_file, e)
        return False

    prompt   = task.get("task") or task.get("content") or task.get("message") or str(task)
    subject  = task.get("subject", "task")
    from_node = task.get("from") or task.get("from_node", "commander")
    msg_id   = task.get("msg_id", str(uuid.uuid4()))

    logger.info("  🔧 [%s] %s", node_id, subject[:70])
    start = time.time()

    try:
        response_text = call_provider(node_id, prompt)
    except Exception as e:
        response_text = f"[ERROR] {e}"

    elapsed = time.time() - start

    if response_text.startswith("[ERROR"):
        logger.error("  ❌ [%s] %s (%.1fs)", node_id, response_text[:100], elapsed)
    else:
        logger.info("  ✅ [%s] %.1fs, %d chars", node_id, elapsed, len(response_text))

    # Escribir respuesta en inbox del remitente
    resp = {
        "msg_id":          f"{node_id}-resp-{str(msg_id)[:8]}",
        "from":            node_id,
        "to":              from_node,
        "ts":              time.time(),
        "type":            "response",
        "subject":         f"RE: {subject}",
        "content":         response_text,
        "elapsed_seconds": round(elapsed, 2),
        "iso":             datetime.now(timezone.utc).isoformat(),
    }
    resp_dir = INBOX_ROOT / from_node
    resp_dir.mkdir(parents=True, exist_ok=True)
    resp_file = resp_dir / f"RESP-{node_id}-{str(msg_id)[:8]}.json"
    resp_file.write_text(json.dumps(resp, ensure_ascii=False, indent=2))

    # Si hay output_file, intentar guardarlo
    output_file = task.get("output_file")
    if output_file and not response_text.startswith("[ERROR"):
        out_path = REPO_ROOT / output_file
        out_path.parent.mkdir(parents=True, exist_ok=True)
        # Extraer contenido si viene con marcador === FILE: ===
        content = response_text
        if "=== FILE:" in content:
            parts = content.split("=== FILE:")
            for part in parts[1:]:
                lines = part.strip().splitlines()
                if lines:
                    file_content = "\n".join(lines[1:]).strip()
                    if file_content:
                        content = file_content
                        break
        out_path.write_text(content, encoding="utf-8")
        logger.info("  📄 [%s] Guardado: %s (%d bytes)", node_id, output_file, out_path.stat().st_size)

    # Marcar como done
    done_file = task_file.with_suffix(".done")
    if task_file.exists():
        try:
            task_file.rename(done_file)
        except FileNotFoundError:
            pass

    # Log evento
    _log_event({
        "event":           "api_task_completed",
        "node":            node_id,
        "subject":         subject,
        "elapsed_seconds": round(elapsed, 2),
        "ts":              time.time(),
        "error":           response_text.startswith("[ERROR"),
    })

    return not response_text.startswith("[ERROR")


def _log_event(event: dict) -> None:
    try:
        with (LOGS_DIR / "mesh_events.jsonl").open("a") as f:
            f.write(json.dumps(event) + "\n")
    except OSError:
        pass


def run_nodes(nodes: list[str], once: bool = False) -> None:
    _load_env()
    logger.info("🚀 API Node Runner — nodes: %s", ", ".join(nodes))

    while True:
        total = 0
        for node_id in nodes:
            if node_id not in PROVIDERS:
                continue
            inbox = INBOX_ROOT / node_id
            if not inbox.exists():
                inbox.mkdir(parents=True, exist_ok=True)
                continue

            tasks = sorted(inbox.glob("*.json"))
            if not tasks:
                continue

            logger.info("📥 [%s] %d tarea(s)", node_id, len(tasks))
            for tf in tasks:
                ok = process_task(node_id, tf)
                if ok:
                    total += 1
                time.sleep(1)

        if total:
            logger.info("✔ Ciclo — %d tareas completadas", total)

        if once:
            break
        time.sleep(POLL_INTERVAL)


def main() -> None:
    parser = argparse.ArgumentParser(description="DOF Mesh API Node Runner")
    parser.add_argument("--nodes", nargs="+", default=list(PROVIDERS.keys()))
    parser.add_argument("--once",   action="store_true")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--list",   action="store_true")
    args = parser.parse_args()

    if args.list:
        print("\n📡 Providers configurados:\n")
        for nid, (url, model, key) in PROVIDERS.items():
            key_set = "✅" if (not key or os.environ.get(key)) else "❌"
            print(f"  {nid:20} {model:40} {key_set}")
        print()
        return

    valid = [n for n in args.nodes if n in PROVIDERS]
    if not valid:
        logger.error("No hay providers válidos. Usa --list para ver opciones.")
        return

    run_nodes(valid, once=args.once)


if __name__ == "__main__":
    main()


# ── ApiNodeRunner class (for test compatibility) ──────────────────────────────

class ApiNodeRunner:
    """Singleton runner that wraps the api_node_runner daemon functions."""

    _instance = None
    _class_lock = __import__("threading").Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._class_lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    inst.is_running = False
                    cls._instance = inst
        return cls._instance

    _SENTINEL = object()

    def run(self, node_id=_SENTINEL) -> None:
        """Start the runner. With no args: OK. With None/int: TypeError. With '': ValueError."""
        if node_id is not ApiNodeRunner._SENTINEL:
            if node_id is None or not isinstance(node_id, str):
                raise TypeError(f"node_id must be str, got {type(node_id).__name__}")
            if node_id == "":
                raise ValueError("node_id cannot be empty")
        self.is_running = True

    def stop(self) -> None:
        """Stop the runner."""
        self.is_running = False
