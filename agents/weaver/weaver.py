"""
Weaver — Cliente Ollama soberano para DOF-MESH Second Brain v2.0.

Llama directamente a Ollama via http.client (sin requests, sin yaml).
Es el "Weaver": teje el contexto del vault con la tarea del usuario
y genera una respuesta usando el modelo correcto.

Modelos disponibles en tu sistema:
  dof-reasoner   → SAM, trading, análisis complejo
  dof-coder      → código, scripts, bugs
  dof-analyst    → reportes, síntesis
  dof-guardian   → seguridad, auditoría
  phi4:latest    → general purpose
  gemma2:9b      → flash / respuestas rápidas
  qwen3-abliterated:30b → razonamiento avanzado

Sin dependencias externas. Fallback determinístico si Ollama no está.
"""

import http.client
import json
import logging
import os
from typing import Optional

logger = logging.getLogger("agents.weaver")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "huihui_ai/qwen3-abliterated:30b-a3b-q4_K_M")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))

# ── Mapping lógico MoE → modelo DOF real ──────────────────────
# Basado en modelos reales disponibles en tu Ollama (M4 Max)
MODEL_MAP = {
    # Top: Qwen3 MoE 30B sin censura — razonamiento complejo, estrategia, análisis
    "reasoner":   "huihui_ai/qwen3-abliterated:30b-a3b-q4_K_M",

    # Especializado en código (Qwen2 14B fine-tuned)
    "coder":      "dof-coder:latest",

    # Analista general (Qwen2 14B fine-tuned)
    "analyst":    "dof-analyst:latest",

    # Seguridad y gobernanza (Qwen2 14B fine-tuned)
    "guardian":   "dof-guardian:latest",

    # Respuestas rápidas — Gemma2 9B
    "flash":      "gemma2:9b",

    # General: Qwen3 30B para máxima calidad en queries libres
    "general":    "huihui_ai/qwen3-abliterated:30b-a3b-q4_K_M",

    # Hunter y CPR: phi4 — rápido, determinístico
    "hunter":     "phi4:latest",
    "compressor": "phi4:latest",
}


def _parse_host_port(url: str) -> tuple[str, int]:
    """Extrae host y puerto del URL de Ollama."""
    url = url.replace("http://", "").replace("https://", "")
    if ":" in url:
        host, port_str = url.rsplit(":", 1)
        return host, int(port_str)
    return url, 11434


def resolve_model(model_name: str) -> str:
    """Convierte nombre lógico (reasoner, coder) al modelo Ollama real."""
    return MODEL_MAP.get(model_name, model_name)


def chat(
    prompt: str,
    model: str = OLLAMA_MODEL,
    system: str = "",
    temperature: float = 0.5,
    max_tokens: int = 2048,
    stream: bool = False,
) -> str:
    """
    Llama a Ollama /api/chat y retorna la respuesta completa.

    Args:
        prompt: Mensaje del usuario.
        model: Nombre del modelo (lógico o Ollama real).
        system: System prompt opcional.
        temperature: Creatividad (0.1 = determinístico, 0.9 = creativo).
        max_tokens: Límite de tokens en la respuesta.
        stream: Si True, streaming. Default False.

    Returns:
        Respuesta del modelo como string.
        Si Ollama no está disponible, retorna fallback informativo.
    """
    # Resolver modelo lógico → real
    real_model = resolve_model(model)

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = json.dumps({
        "model": real_model,
        "messages": messages,
        "stream": stream,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }).encode("utf-8")

    host, port = _parse_host_port(OLLAMA_URL)

    try:
        conn = http.client.HTTPConnection(host, port, timeout=OLLAMA_TIMEOUT)
        conn.request(
            "POST",
            "/api/chat",
            payload,
            {"Content-Type": "application/json"},
        )
        resp = conn.getresponse()

        if resp.status != 200:
            body = resp.read().decode("utf-8", errors="replace")[:500]
            logger.error("Ollama error %d: %s", resp.status, body)
            return f"[Weaver ERROR] Ollama retornó {resp.status}: {body}"

        data = json.loads(resp.read())
        content = data.get("message", {}).get("content", "").strip()
        logger.info(
            "Weaver: %s → %d chars (model=%s)",
            prompt[:40], len(content), real_model
        )
        return content

    except ConnectionRefusedError:
        logger.warning("Weaver: Ollama no disponible en %s:%d", host, port)
        return _fallback(prompt, real_model)
    except Exception as exc:
        logger.error("Weaver error: %s", exc)
        return _fallback(prompt, real_model)
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _fallback(prompt: str, model: str) -> str:
    """Respuesta determinística cuando Ollama no está disponible."""
    return (
        f"[Weaver — modo offline]\n"
        f"Modelo solicitado: {model}\n"
        f"Ollama no disponible en {OLLAMA_URL}.\n"
        f"Tarea recibida: {prompt[:200]}\n\n"
        f"Hint: Inicia Ollama con `ollama serve` y reintenta."
    )


def synthesize_context(
    task: str,
    vault_context: str,
    memory_context: str,
    model: str = "general",
) -> str:
    """
    Sintetiza contexto del vault + memoria + tarea en un prompt enriquecido.
    Este es el núcleo del 'Weaving': tejer datos del vault con la tarea.

    Args:
        task: Instrucción del usuario.
        vault_context: Contenido recuperado del vault de Obsidian.
        memory_context: Contexto comprimido de sesiones previas (CPR).
        model: Modelo MoE lógico a usar.

    Returns:
        Respuesta generada por el LLM con contexto completo.
    """
    system = (
        "Eres el agente Weaver del sistema DOF-MESH Second Brain. "
        "Tienes acceso al vault de conocimiento de Obsidian del usuario. "
        "Responde de forma directa y accionable. "
        "Si el contexto es insuficiente, dilo claramente. "
        "Prioriza información del vault sobre tu conocimiento general."
    )

    parts = []

    if memory_context and memory_context not in ("Sin memoria previa.", "Sin sesiones previas."):
        parts.append(f"## Contexto de sesiones previas\n{memory_context[:600]}")

    if vault_context:
        parts.append(f"## Contexto del vault (Obsidian)\n{vault_context[:800]}")

    parts.append(f"## Tarea\n{task}")

    full_prompt = "\n\n".join(parts)

    # Temperatura según modelo
    temp_map = {
        "reasoner": 0.3, "coder": 0.2, "analyst": 0.6,
        "flash": 0.7, "general": 0.5, "hunter": 0.1,
    }
    temperature = temp_map.get(model, 0.5)

    return chat(full_prompt, model=model, system=system, temperature=temperature)


def check_connection() -> dict:
    """Verifica disponibilidad de Ollama y lista modelos."""
    host, port = _parse_host_port(OLLAMA_URL)
    try:
        conn = http.client.HTTPConnection(host, port, timeout=5)
        conn.request("GET", "/api/tags")
        resp = conn.getresponse()
        data = json.loads(resp.read())
        models = [m["name"] for m in data.get("models", [])]
        conn.close()
        return {
            "available": True,
            "url": OLLAMA_URL,
            "models": models,
            "dof_models": [m for m in models if m.startswith("dof-")],
        }
    except Exception as exc:
        return {"available": False, "url": OLLAMA_URL, "error": str(exc)}


# ── CLI de prueba ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

    print("=== Weaver — Test de Conexión ===\n")
    status = check_connection()

    if status["available"]:
        print(f"✅ Ollama disponible en {status['url']}")
        print(f"   Modelos totales: {len(status['models'])}")
        print(f"   Modelos DOF: {status['dof_models']}")
    else:
        print(f"❌ Ollama no disponible: {status.get('error')}")
        sys.exit(1)

    if "--test" in sys.argv:
        print("\n=== Test de generación ===")
        prompt = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "¿Qué es DOF-MESH en una sola frase?"
        model_arg = os.getenv("WEAVER_MODEL", "general")
        print(f"Modelo: {model_arg} ({resolve_model(model_arg)})")
        print(f"Prompt: {prompt}\n")
        result = chat(prompt, model=model_arg, temperature=0.5)
        print(result)
