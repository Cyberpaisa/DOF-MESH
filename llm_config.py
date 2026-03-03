"""
Configuración de LLMs — 7 proveedores gratuitos + Smart Router + Retry.

Distribución de carga (Research Crew):
  Researcher:  Groq Llama 3.3         (tool-calling)
  Strategist:  NVIDIA Qwen3.5-397B    (razonamiento)
  QA Reviewer: Cerebras GPT-OSS 120B  (tool-calling)
  Verifier:    Cerebras GPT-OSS 120B  (libera Groq TPM)

Proveedores activos (7):
  GROQ:       Llama 3.3 70B, Qwen3-32B, GPT-OSS 120B, Kimi K2  (131K, 12K TPM free)
  NVIDIA:     Qwen3.5-397B, Kimi K2.5, DeepSeek V3.2           (128K, 1000 credits)
  CEREBRAS:   GPT-OSS 120B                                      (128K, 1M tok/día free)
  GEMINI:     2.5 Flash                                (1M context, 20 req/día free)
  SAMBANOVA:  DeepSeek V3.2                            (BACKUP — 24K limit)
  OPENROUTER: Hermes 405B free                         (variable)
  ZHIPU:      GLM-4.7-Flash                             (128K, gratis, 745B MoE)

Búsqueda web: Serper (Google) → Tavily → DuckDuckGo
"""

import os
import time
import logging
from dotenv import load_dotenv
from crewai import LLM

load_dotenv()

# LiteLLM busca NVIDIA_NIM_API_KEY para el prefijo nvidia_nim/
# Copiamos NVIDIA_API_KEY si existe
if os.getenv("NVIDIA_API_KEY") and not os.getenv("NVIDIA_NIM_API_KEY"):
    os.environ["NVIDIA_NIM_API_KEY"] = os.getenv("NVIDIA_API_KEY")

# Zhipu: NO copiar la key a OPENAI_API_KEY — LiteLLM la envia a api.openai.com
# En su lugar, usamos api_key directo en la instancia LLM con base_url.

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════
# PROVEEDORES
# ═══════════════════════════════════════════════════════

def get_groq_llm(model="llama-3.3-70b-versatile", temperature=0.3):
    """Groq — 131K context, ultrarrápido. 12K TPM free tier."""
    return LLM(
        model=f"groq/{model}",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=temperature,
        max_tokens=4096,
    )


def get_nvidia_llm(model="deepseek-ai/deepseek-v3.2", temperature=0.3):
    """NVIDIA NIM — 128K context. Qwen3.5-397B, Kimi K2.5, DeepSeek V3.2."""
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        return None
    return LLM(
        model=f"nvidia_nim/{model}",
        api_key=api_key,
        temperature=temperature,
        max_tokens=4096,
    )


def get_cerebras_llm(model="gpt-oss-120b", temperature=0.3):
    """Cerebras — 128K context, ultrarrápido (0.3s)."""
    api_key = os.getenv("CEREBRAS_API_KEY")
    if not api_key:
        return None
    return LLM(
        model=f"cerebras/{model}",
        api_key=api_key,
        temperature=temperature,
        max_tokens=4096,
    )


def get_sambanova_llm(model="DeepSeek-V3.2", temperature=0.3):
    """SambaNova — BACKUP ONLY (24K context limit)."""
    api_key = os.getenv("SAMBANOVA_API_KEY")
    if not api_key:
        return None
    return LLM(
        model=f"sambanova/{model}",
        api_key=api_key,
        temperature=temperature,
        max_tokens=4096,
    )


def get_openrouter_llm(model="nousresearch/hermes-3-llama-3.1-405b:free", temperature=0.3):
    """OpenRouter — modelos gratuitos (rate limited)."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return None
    return LLM(
        model=f"openrouter/{model}",
        api_key=api_key,
        temperature=temperature,
        max_tokens=4096,
    )


def get_gemini_llm(temperature=0.7):
    """Gemini 2.5 Flash — 1M context window. 20 req/día free."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    return LLM(
        model="gemini/gemini-2.5-flash",
        api_key=api_key,
        temperature=temperature,
    )


def get_zhipu_llm(model="glm-4.7-flash", temperature=0.3):
    """Zhipu AI — GLM-4.7-Flash gratis, 128K context, 745B MoE."""
    api_key = os.getenv("ZHIPU_API_KEY")
    if not api_key:
        return None
    return LLM(
        model=f"openai/{model}",
        api_key=api_key,
        base_url="https://api.z.ai/api/paas/v4/",
        temperature=temperature,
        max_tokens=4096,
        extra_body={"enable_thinking": False},
    )



# ═══════════════════════════════════════════════════════
# PROVIDER RESILIENCE — Auto-fallback cuando un provider cae
# ═══════════════════════════════════════════════════════

_exhausted_providers: set[str] = set()


def mark_provider_exhausted(provider: str):
    """Mark a provider as exhausted (rate limit). Skipped in all assignments."""
    provider = provider.lower()
    _exhausted_providers.add(provider)
    logger.warning(f"Provider '{provider}' marked as exhausted. Active: {_get_active_providers()}")


def reset_exhausted_providers():
    """Reset all providers to available."""
    _exhausted_providers.clear()
    logger.info("All providers reset to available.")


def _get_active_providers() -> list[str]:
    """List active (non-exhausted) providers."""
    all_providers = ["groq", "nvidia", "cerebras", "zhipu"]
    return [p for p in all_providers if p not in _exhausted_providers]


def _is_available(provider: str) -> bool:
    """Check if a provider is available (not exhausted)."""
    return provider.lower() not in _exhausted_providers


def _try_get(provider: str, getter, **kwargs):
    """Try to get an LLM from a provider if available."""
    if not _is_available(provider):
        return None
    return getter(**kwargs)


# ═══════════════════════════════════════════════════════
# ROLE ASSIGNMENT — With LiteLLM auto-fallback on rate limit
# ═══════════════════════════════════════════════════════
# Each role has a provider chain. First available becomes primary.
# Remaining providers attach as LiteLLM fallbacks so rate-limit
# errors auto-rotate to the next provider at the transport layer.

_ROLE_CHAINS = {
    "code_architect":    [("nvidia", "nvidia_nim/moonshotai/kimi-k2.5"),
                          ("groq", "groq/moonshotai/kimi-k2-instruct"),
                          ("cerebras", "cerebras/gpt-oss-120b"),
                          ("zhipu", "openai/glm-4.7-flash")],
    "research_analyst":  [("groq", "groq/llama-3.3-70b-versatile"),
                          ("nvidia", "nvidia_nim/deepseek-ai/deepseek-v3.2"),
                          ("cerebras", "cerebras/gpt-oss-120b"),
                          ("zhipu", "openai/glm-4.7-flash")],
    "mvp_strategist":    [("nvidia", "nvidia_nim/qwen/qwen3.5-397b-a17b"),
                          ("cerebras", "cerebras/gpt-oss-120b"),
                          ("zhipu", "openai/glm-4.7-flash"),
                          ("groq", "groq/llama-3.3-70b-versatile")],
    "qa_reviewer":       [("cerebras", "cerebras/gpt-oss-120b"),
                          ("groq", "groq/llama-3.3-70b-versatile"),
                          ("nvidia", "nvidia_nim/deepseek-ai/deepseek-v3.2"),
                          ("zhipu", "openai/glm-4.7-flash")],
    "data_engineer":     [("cerebras", "cerebras/gpt-oss-120b"),
                          ("nvidia", "nvidia_nim/deepseek-ai/deepseek-v3.2"),
                          ("groq", "groq/llama-3.3-70b-versatile"),
                          ("zhipu", "openai/glm-4.7-flash")],
    "project_organizer": [("groq", "groq/qwen/qwen3-32b"),
                          ("cerebras", "cerebras/gpt-oss-120b"),
                          ("zhipu", "openai/glm-4.7-flash"),
                          ("nvidia", "nvidia_nim/deepseek-ai/deepseek-v3.2")],
    "narrative_content": [("cerebras", "cerebras/gpt-oss-120b"),
                          ("zhipu", "openai/glm-4.7-flash"),
                          ("nvidia", "nvidia_nim/deepseek-ai/deepseek-v3.2"),
                          ("groq", "groq/llama-3.3-70b-versatile")],
    "verifier":          [("cerebras", "cerebras/gpt-oss-120b"),
                          ("groq", "groq/llama-3.3-70b-versatile"),
                          ("nvidia", "nvidia_nim/deepseek-ai/deepseek-v3.2"),
                          ("zhipu", "openai/glm-4.7-flash")],
}

_DEFAULT_CHAIN = [
    ("cerebras", "cerebras/gpt-oss-120b"),
    ("nvidia", "nvidia_nim/deepseek-ai/deepseek-v3.2"),
    ("groq", "groq/llama-3.3-70b-versatile"),
    ("zhipu", "openai/glm-4.7-flash"),
]

_ROLE_TEMPS = {
    "code_architect": 0.2, "research_analyst": 0.5, "mvp_strategist": 0.6,
    "qa_reviewer": 0.2, "data_engineer": 0.1, "project_organizer": 0.3,
    "narrative_content": 0.7, "verifier": 0.2,
}

_PROVIDER_KEY_ENV = {
    "groq": "GROQ_API_KEY",
    "nvidia": "NVIDIA_API_KEY",
    "cerebras": "CEREBRAS_API_KEY",
    "zhipu": "ZHIPU_API_KEY",
}

_ZHIPU_BASE_URL = "https://api.z.ai/api/paas/v4/"


def _build_fallback_entry(provider: str, model: str) -> dict | None:
    """Build a LiteLLM fallback dict for a provider. Returns None if no API key."""
    key_env = _PROVIDER_KEY_ENV.get(provider)
    if not key_env:
        return None
    api_key = os.getenv(key_env)
    if not api_key:
        return None
    entry = {"model": model, "api_key": api_key}
    if provider == "zhipu":
        entry["api_base"] = _ZHIPU_BASE_URL
    return entry


def get_llm_for_role(role: str) -> LLM:
    """
    Resilient assignment — first available provider becomes primary,
    remaining providers attach as LiteLLM fallbacks for automatic
    rotation on rate-limit errors.

    | Role              | Primary               | Fallback 1            | Fallback 2          | Fallback 3      |
    |-------------------|-----------------------|-----------------------|---------------------|-----------------|
    | Code Architect    | Kimi K2.5 (NVIDIA)    | Kimi K2 (Groq)        | GPT-OSS (Cerebras)  | GLM-4.7 (Zhipu) |
    | Research Analyst  | Llama 3.3 (Groq)      | DeepSeek V3.2 (NV)    | GPT-OSS (Cerebras)  | GLM-4.7 (Zhipu) |
    | MVP Strategist    | Qwen3.5-397B (NVIDIA) | GPT-OSS (Cerebras)    | GLM-4.7 (Zhipu)     | Llama 3.3 (Groq)|
    | QA Reviewer       | GPT-OSS (Cerebras)    | Llama 3.3 (Groq)      | DeepSeek V3.2 (NV)  | GLM-4.7 (Zhipu) |
    | Data Engineer     | GPT-OSS (Cerebras)    | DeepSeek V3.2 (NV)    | Llama 3.3 (Groq)    | GLM-4.7 (Zhipu) |
    | Project Organizer | Qwen3-32B (Groq)      | GPT-OSS (Cerebras)    | GLM-4.7 (Zhipu)     | DeepSeek (NV)   |
    | Narrative         | GPT-OSS (Cerebras)    | GLM-4.7 (Zhipu)       | DeepSeek V3.2 (NV)  | Llama 3.3 (Groq)|
    | Verifier          | GPT-OSS (Cerebras)    | Llama 3.3 (Groq)      | DeepSeek V3.2 (NV)  | GLM-4.7 (Zhipu) |
    """
    role = role.lower()
    chain = _ROLE_CHAINS.get(role, _DEFAULT_CHAIN)
    temp = _ROLE_TEMPS.get(role, 0.5)

    for i, (provider, model) in enumerate(chain):
        if not _is_available(provider):
            continue
        api_key = os.getenv(_PROVIDER_KEY_ENV.get(provider, ""))
        if not api_key:
            continue

        # Build fallbacks from remaining chain entries
        fallbacks = []
        for j, (fb_prov, fb_model) in enumerate(chain):
            if j == i:
                continue
            entry = _build_fallback_entry(fb_prov, fb_model)
            if entry:
                fallbacks.append(entry)

        # Build primary LLM with fallbacks
        kwargs = {
            "model": model,
            "api_key": api_key,
            "temperature": temp,
            "max_tokens": 4096,
        }
        if provider == "zhipu":
            kwargs["base_url"] = _ZHIPU_BASE_URL
            kwargs["extra_body"] = {"enable_thinking": False}
        if fallbacks:
            kwargs["fallbacks"] = fallbacks

        logger.info(f"LLM for '{role}': {model} + {len(fallbacks)} fallbacks")
        return LLM(**kwargs)

    raise ValueError(f"All providers exhausted. No LLM available for {role}.")


# ═══════════════════════════════════════════════════════
# SMART ROUTER — Elige modelo por contexto + rol
# ═══════════════════════════════════════════════════════

def estimate_tokens(text: str) -> int:
    """Estimación rápida de tokens (~4 chars = 1 token)."""
    return len(text) // 4


def get_llm_smart(role: str, task_text: str = "", context_size: int = 0):
    """
    Router inteligente (respeta providers agotados):
    - Si contexto > 200K tokens → Gemini (1M context)
    - Si tarea de código → Kimi K2.5 (NVIDIA)
    - Si tarea rápida/simple → Cerebras (0.3s)
    - Default → routing por rol con fallback completo
    """
    total_tokens = estimate_tokens(task_text) + context_size

    if total_tokens > 200_000:
        gemini = get_gemini_llm(temperature=0.5)
        if gemini:
            return gemini

    code_keywords = ["código", "code", "script", "debug", "función", "api", "endpoint",
                     "solidity", "rust", "python", "typescript", "smart contract"]
    is_code_task = any(kw in task_text.lower() for kw in code_keywords)
    if is_code_task and role != "code_architect":
        nvidia = _try_get("nvidia", get_nvidia_llm, model="moonshotai/kimi-k2.5", temperature=0.2)
        if nvidia:
            return nvidia

    reasoning_keywords = ["analiza", "razona", "estrategia", "plan", "diseña", "architecture",
                          "reasoning", "strategy", "evaluate", "compare"]
    is_reasoning_task = any(kw in task_text.lower() for kw in reasoning_keywords)
    if is_reasoning_task and role not in ("mvp_strategist", "code_architect"):
        nvidia_qwen = _try_get("nvidia", get_nvidia_llm, model="qwen/qwen3.5-397b-a17b", temperature=0.4)
        if nvidia_qwen:
            return nvidia_qwen

    if total_tokens < 5_000 and role not in ("research_analyst", "mvp_strategist"):
        cerebras = _try_get("cerebras", get_cerebras_llm, temperature=0.3)
        if cerebras:
            return cerebras

    # Fallback: routing por rol (ya tiene cadenas completas de 4 providers)
    return get_llm_for_role(role)


# ═══════════════════════════════════════════════════════
# VALIDACIÓN
# ═══════════════════════════════════════════════════════

def validate_keys() -> dict:
    status = {
        "groq": bool(os.getenv("GROQ_API_KEY")),
        "gemini": bool(os.getenv("GEMINI_API_KEY")),
        "nvidia": bool(os.getenv("NVIDIA_API_KEY")),
        "cerebras": bool(os.getenv("CEREBRAS_API_KEY")),
        "sambanova": bool(os.getenv("SAMBANOVA_API_KEY")),
        "openrouter": bool(os.getenv("OPENROUTER_API_KEY")),
        "zhipu": bool(os.getenv("ZHIPU_API_KEY")),
        "serper": bool(os.getenv("SERPER_API_KEY")),
        "tavily": bool(os.getenv("TAVILY_API_KEY")),
    }
    if not status["groq"]:
        raise ValueError("GROQ_API_KEY no configurada. https://console.groq.com")
    return status
