"""
Configuración de LLMs — 8 proveedores gratuitos + Smart Router + Retry.

Distribución de carga (Research Crew):
  Researcher:  Groq Llama 3.3         (tool-calling)
  Strategist:  NVIDIA Qwen3.5-397B    (razonamiento)
  QA Reviewer: Cerebras GPT-OSS 120B  (tool-calling)
  Verifier:    Cerebras GPT-OSS 120B  (libera Groq TPM)

Proveedores activos (8):
  GROQ:       Llama 3.3 70B, Qwen3-32B, GPT-OSS 120B, Kimi K2  (131K, 12K TPM free)
  NVIDIA:     Qwen3.5-397B, Kimi K2.5, DeepSeek V3.2           (128K, 1000 credits)
  CEREBRAS:   GPT-OSS 120B                                      (128K, 1M tok/día free)
  MINIMAX:    MiniMax-M2.1                                      (128K, free tier)
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


def get_minimax_llm(model="MiniMax-M2.1", temperature=0.3):
    """MiniMax — M2.1, 128K context, free tier."""
    api_key = os.getenv("MINIMAX_API_KEY")
    if not api_key:
        return None
    return LLM(
        model=f"minimax/{model}",
        api_key=api_key,
        temperature=temperature,
        max_tokens=4096,
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
    all_providers = ["groq", "nvidia", "cerebras", "minimax", "zhipu"]
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
# ROLE ASSIGNMENT — Provider chain with crew-level rotation
# ═══════════════════════════════════════════════════════
# Each role has a provider chain. First available becomes primary.
# On rate-limit, crew_runner marks the provider exhausted and
# rebuilds the crew via crew_factory → next provider is selected.

_ROLE_CHAINS = {
    "code_architect":    [("zo", "vercel:minimax/minimax-m2.5"),
    ("minimax", "minimax/MiniMax-M2.1"),
                          ("groq", "groq/moonshotai/kimi-k2-instruct"),
                          ("cerebras", "cerebras/gpt-oss-120b"),
                          ("zhipu", "openai/glm-4.7-flash"),
                          ("nvidia", "nvidia_nim/moonshotai/kimi-k2.5")],
    "research_analyst":  [("zo", "vercel:minimax/minimax-m2.5"),
    ("minimax", "minimax/MiniMax-M2.1"),
                          ("groq", "groq/llama-3.3-70b-versatile"),
                          ("cerebras", "cerebras/gpt-oss-120b"),
                          ("zhipu", "openai/glm-4.7-flash"),
                          ("nvidia", "nvidia_nim/deepseek-ai/deepseek-v3.2")],
    "mvp_strategist":    [("zo", "vercel:minimax/minimax-m2.5"),
    ("minimax", "minimax/MiniMax-M2.1"),
                          ("cerebras", "cerebras/gpt-oss-120b"),
                          ("groq", "groq/llama-3.3-70b-versatile"),
                          ("zhipu", "openai/glm-4.7-flash"),
                          ("nvidia", "nvidia_nim/qwen/qwen3.5-397b-a17b")],
    "qa_reviewer":       [("zo", "vercel:minimax/minimax-m2.5"),
    ("minimax", "minimax/MiniMax-M2.1"),
                          ("cerebras", "cerebras/gpt-oss-120b"),
                          ("groq", "groq/llama-3.3-70b-versatile"),
                          ("zhipu", "openai/glm-4.7-flash"),
                          ("nvidia", "nvidia_nim/deepseek-ai/deepseek-v3.2")],
    "data_engineer":     [("zo", "vercel:minimax/minimax-m2.5"),
    ("minimax", "minimax/MiniMax-M2.1"),
                          ("cerebras", "cerebras/gpt-oss-120b"),
                          ("groq", "groq/llama-3.3-70b-versatile"),
                          ("zhipu", "openai/glm-4.7-flash"),
                          ("nvidia", "nvidia_nim/deepseek-ai/deepseek-v3.2")],
    "project_organizer": [("zo", "vercel:minimax/minimax-m2.5"),
    ("minimax", "minimax/MiniMax-M2.1"),
                          ("groq", "groq/qwen/qwen3-32b"),
                          ("cerebras", "cerebras/gpt-oss-120b"),
                          ("zhipu", "openai/glm-4.7-flash"),
                          ("nvidia", "nvidia_nim/deepseek-ai/deepseek-v3.2")],
    "narrative_content": [("zo", "vercel:minimax/minimax-m2.5"),
    ("minimax", "minimax/MiniMax-M2.1"),
                          ("cerebras", "cerebras/gpt-oss-120b"),
                          ("groq", "groq/llama-3.3-70b-versatile"),
                          ("zhipu", "openai/glm-4.7-flash"),
                          ("nvidia", "nvidia_nim/deepseek-ai/deepseek-v3.2")],
    "verifier":          [("zo", "vercel:minimax/minimax-m2.5"),
    ("minimax", "minimax/MiniMax-M2.1"),
                          ("cerebras", "cerebras/gpt-oss-120b"),
                          ("groq", "groq/llama-3.3-70b-versatile"),
                          ("zhipu", "openai/glm-4.7-flash"),
                          ("nvidia", "nvidia_nim/deepseek-ai/deepseek-v3.2")],
}

_DEFAULT_CHAIN = [
    ("zo", "vercel:minimax/minimax-m2.5"),
    ("minimax", "minimax/MiniMax-M2.1"),
    ("cerebras", "cerebras/gpt-oss-120b"),
    ("groq", "groq/llama-3.3-70b-versatile"),
    ("zhipu", "openai/glm-4.7-flash"),
    ("nvidia", "nvidia_nim/deepseek-ai/deepseek-v3.2"),
]

_ROLE_TEMPS = {
    "code_architect": 0.2, "research_analyst": 0.5, "mvp_strategist": 0.6,
    "qa_reviewer": 0.2, "data_engineer": 0.1, "project_organizer": 0.3,
    "narrative_content": 0.7, "verifier": 0.2,
}

_PROVIDER_KEY_ENV = {
    "zo": "ZO_API_KEY",
    "minimax": "MINIMAX_API_KEY",
    "groq": "GROQ_API_KEY",
    "nvidia": "NVIDIA_API_KEY",
    "cerebras": "CEREBRAS_API_KEY",
    "zhipu": "ZHIPU_API_KEY",
}

_ZHIPU_BASE_URL = "https://api.z.ai/api/paas/v4/"


def get_llm_for_role(role: str) -> LLM:
    """
    Resilient assignment — first available (non-exhausted) provider becomes primary.
    On rate-limit failure, crew_runner rebuilds the crew via crew_factory, which
    calls this function again with the exhausted provider already marked — so the
    next provider in the chain is automatically selected.

    | Role              | Chain order (first available wins)                                                       |
    |-------------------|------------------------------------------------------------------------------------------|
    | Code Architect    | M2.1 (MiniMax) → Kimi K2 (Groq) → GPT-OSS (Cerebras) → GLM (Zhipu) → Kimi K2.5 (NV)   |
    | Research Analyst  | M2.1 (MiniMax) → Llama 3.3 (Groq) → GPT-OSS (Cerebras) → GLM (Zhipu) → DeepSeek (NV)   |
    | MVP Strategist    | M2.1 (MiniMax) → GPT-OSS (Cerebras) → Llama 3.3 (Groq) → GLM (Zhipu) → Qwen3.5 (NV)   |
    | QA Reviewer       | M2.1 (MiniMax) → GPT-OSS (Cerebras) → Llama 3.3 (Groq) → GLM (Zhipu) → DeepSeek (NV)   |
    | Data Engineer     | M2.1 (MiniMax) → GPT-OSS (Cerebras) → Llama 3.3 (Groq) → GLM (Zhipu) → DeepSeek (NV)   |
    | Project Organizer | M2.1 (MiniMax) → Qwen3-32B (Groq) → GPT-OSS (Cerebras) → GLM (Zhipu) → DeepSeek (NV)   |
    | Narrative         | M2.1 (MiniMax) → GPT-OSS (Cerebras) → Llama 3.3 (Groq) → GLM (Zhipu) → DeepSeek (NV)  |
    | Verifier          | M2.1 (MiniMax) → GPT-OSS (Cerebras) → Llama 3.3 (Groq) → GLM (Zhipu) → DeepSeek (NV)  |
    """
    role = role.lower()
    chain = _ROLE_CHAINS.get(role, _DEFAULT_CHAIN)
    temp = _ROLE_TEMPS.get(role, 0.5)

    for provider, model in chain:
        if not _is_available(provider):
            continue
        api_key = os.getenv(_PROVIDER_KEY_ENV.get(provider, ""))
        if not api_key:
            continue

        kwargs = {
            "model": model,
            "api_key": api_key,
            "temperature": temp,
            "max_tokens": 4096,
        }
        if provider == "zhipu":
            kwargs["base_url"] = _ZHIPU_BASE_URL
            kwargs["extra_body"] = {"enable_thinking": False}

        logger.info(f"LLM for '{role}': {model} (provider: {provider})")
        return LLM(**kwargs)

    raise ValueError(f"All providers exhausted. No LLM available for {role}.")


# ═══════════════════════════════════════════════════════
# SMART ROUTER — Elige modelo por contexto + task_type + rol
# ═══════════════════════════════════════════════════════

def estimate_tokens(text: str) -> int:
    """Estimación rápida de tokens (~4 chars = 1 token)."""
    return len(text) // 4


# ── Circuit Breaker ──────────────────────────────────────────────────
# Tracks failures per provider. 3+ failures within 5 minutes → degraded.
# Structure: {provider: [(timestamp, ...), ...]}
_circuit_breaker: dict[str, list[float]] = {}
_CIRCUIT_BREAKER_THRESHOLD = 3
_CIRCUIT_BREAKER_WINDOW_S = 300  # 5 minutes

# ── Routing Decision Log ─────────────────────────────────────────────
# Each entry: {timestamp, role, task_type, chosen_provider, chosen_model, reason}
_routing_log: list[dict] = []


def record_provider_failure(provider: str):
    """Record a provider failure for circuit breaker tracking."""
    provider = provider.lower()
    now = time.time()
    if provider not in _circuit_breaker:
        _circuit_breaker[provider] = []
    _circuit_breaker[provider].append(now)
    # Prune old entries
    _circuit_breaker[provider] = [
        t for t in _circuit_breaker[provider]
        if now - t < _CIRCUIT_BREAKER_WINDOW_S
    ]
    if len(_circuit_breaker[provider]) >= _CIRCUIT_BREAKER_THRESHOLD:
        mark_provider_exhausted(provider)
        logger.warning(
            f"Circuit breaker OPEN for '{provider}': "
            f"{len(_circuit_breaker[provider])} failures in {_CIRCUIT_BREAKER_WINDOW_S}s"
        )


def is_provider_degraded(provider: str) -> bool:
    """Check if a provider is degraded (circuit breaker open)."""
    provider = provider.lower()
    if not _is_available(provider):
        return True
    now = time.time()
    recent = [t for t in _circuit_breaker.get(provider, [])
              if now - t < _CIRCUIT_BREAKER_WINDOW_S]
    return len(recent) >= _CIRCUIT_BREAKER_THRESHOLD


def get_routing_log(last_n: int = 100) -> list[dict]:
    """Return last N routing decisions for analytics."""
    return _routing_log[-last_n:]


def get_routing_stats() -> dict:
    """Return routing distribution and failure rates for monitoring."""
    log = get_routing_log(100)
    if not log:
        return {
            "total_decisions": 0,
            "provider_distribution": {},
            "provider_failure_rate": {},
            "avg_latency_ms": {},
        }

    # Distribution
    dist: dict[str, int] = {}
    for entry in log:
        p = entry.get("chosen_provider", "unknown")
        dist[p] = dist.get(p, 0) + 1
    total = len(log)
    pct_dist = {k: round(v / total * 100, 1) for k, v in dist.items()}

    # Failure rates from circuit breaker
    now = time.time()
    failure_rates: dict[str, float] = {}
    for provider, timestamps in _circuit_breaker.items():
        recent = [t for t in timestamps if now - t < _CIRCUIT_BREAKER_WINDOW_S]
        provider_calls = dist.get(provider, 1)
        failure_rates[provider] = round(len(recent) / max(provider_calls, 1) * 100, 1)

    return {
        "total_decisions": total,
        "provider_distribution": pct_dist,
        "provider_failure_rate": failure_rates,
        "avg_latency_ms": {},  # Populated by caller with actual latency data
    }


def _log_routing_decision(role: str, task_type: str, provider: str, model: str, reason: str):
    """Log a routing decision for analytics."""
    entry = {
        "timestamp": time.time(),
        "role": role,
        "task_type": task_type or "default",
        "chosen_provider": provider,
        "chosen_model": model,
        "reason": reason,
    }
    _routing_log.append(entry)
    # Cap log size at 1000 entries
    if len(_routing_log) > 1000:
        _routing_log[:] = _routing_log[-500:]
    logger.info(f"Routing: {role}/{task_type} → {provider}/{model} ({reason})")


# TODO paper — "Learning When to Act or Refuse" (KARL):
# get_llm_smart implements neurosymbolic routing where the deterministic
# router (task_type rules + circuit breaker) decides which LLM is invoked.
# This is analogous to the Z3 gate: the router proposes → rules approve/reject.

def get_llm_smart(role: str, task_text: str = "", context_size: int = 0,
                  task_type: str = None):
    """
    Smart LLM router with task-type routing, circuit breaker, and analytics.

    Routing priority:
    1. Context size > 50K tokens → Gemini (1M context window)
    2. Explicit task_type:
       - "architecture" → Kimi K2.5 (NVIDIA NIM)
       - "research"     → DeepSeek V3.2 (NVIDIA NIM)
       - "verification" → MiniMax M2.1 (primary, 1000 req/day)
       - "fast"         → Zhipu GLM-4.7 (17x faster)
       - "fallback"     → Groq Llama 3.3
    3. Keyword-based heuristics (code, reasoning)
    4. Small context optimization (< 5K → Cerebras)
    5. Default → role-based routing with full fallback chain

    Circuit breaker: 3 failures in 5 minutes → provider degraded.
    OpenAI: REMOVED (caused 33% of failures).
    NVIDIA NIM: only at end of chains (no structured output).

    Args:
        role: Agent role name (e.g. "code_architect").
        task_text: Optional task description for keyword-based routing.
        context_size: Pre-computed token count of context already loaded.
        task_type: Explicit routing hint. One of: architecture, research,
                   verification, fast, fallback. If None, uses heuristics.

    Returns:
        LLM instance configured for the selected provider.
    """
    total_tokens = estimate_tokens(task_text) + context_size

    # ── 1. Large context → Gemini ────────────────────────────────────
    if total_tokens > 50_000:
        gemini = get_gemini_llm(temperature=0.5)
        if gemini:
            _log_routing_decision(role, task_type, "gemini", "gemini-2.5-flash",
                                  f"large context ({total_tokens} tokens)")
            return gemini

    # ── 2. Explicit task_type routing ────────────────────────────────
    if task_type == "architecture":
        nvidia = _try_get("nvidia", get_nvidia_llm,
                          model="moonshotai/kimi-k2.5", temperature=0.2)
        if nvidia and not is_provider_degraded("nvidia"):
            _log_routing_decision(role, task_type, "nvidia", "kimi-k2.5",
                                  "task_type=architecture")
            return nvidia

    elif task_type == "research":
        nvidia = _try_get("nvidia", get_nvidia_llm,
                          model="deepseek-ai/deepseek-v3.2", temperature=0.3)
        if nvidia and not is_provider_degraded("nvidia"):
            _log_routing_decision(role, task_type, "nvidia", "deepseek-v3.2",
                                  "task_type=research")
            return nvidia

    elif task_type == "verification":
        minimax = _try_get("minimax", get_minimax_llm, temperature=0.2)
        if minimax and not is_provider_degraded("minimax"):
            _log_routing_decision(role, task_type, "minimax", "MiniMax-M2.1",
                                  "task_type=verification")
            return minimax

    elif task_type == "fast":
        zhipu = _try_get("zhipu", get_zhipu_llm, temperature=0.3)
        if zhipu and not is_provider_degraded("zhipu"):
            _log_routing_decision(role, task_type, "zhipu", "glm-4.7-flash",
                                  "task_type=fast")
            return zhipu

    elif task_type == "fallback":
        groq = _try_get("groq", get_groq_llm, temperature=0.3)
        if groq and not is_provider_degraded("groq"):
            _log_routing_decision(role, task_type, "groq", "llama-3.3-70b",
                                  "task_type=fallback")
            return groq

    # ── 3. Keyword heuristics (preserved from v0.3.2) ───────────────
    if not task_type:
        code_keywords = ["código", "code", "script", "debug", "función", "api",
                         "endpoint", "solidity", "rust", "python", "typescript",
                         "smart contract"]
        is_code_task = any(kw in task_text.lower() for kw in code_keywords)
        if is_code_task and role != "code_architect":
            nvidia = _try_get("nvidia", get_nvidia_llm,
                              model="moonshotai/kimi-k2.5", temperature=0.2)
            if nvidia:
                _log_routing_decision(role, task_type, "nvidia", "kimi-k2.5",
                                      "code keywords detected")
                return nvidia

        reasoning_keywords = ["analiza", "razona", "estrategia", "plan", "diseña",
                              "architecture", "reasoning", "strategy", "evaluate",
                              "compare"]
        is_reasoning_task = any(kw in task_text.lower() for kw in reasoning_keywords)
        if is_reasoning_task and role not in ("mvp_strategist", "code_architect"):
            nvidia_qwen = _try_get("nvidia", get_nvidia_llm,
                                   model="qwen/qwen3.5-397b-a17b", temperature=0.4)
            if nvidia_qwen:
                _log_routing_decision(role, task_type, "nvidia", "qwen3.5-397b",
                                      "reasoning keywords detected")
                return nvidia_qwen

    # ── 4. Small context → Cerebras ──────────────────────────────────
    if total_tokens < 5_000 and role not in ("research_analyst", "mvp_strategist"):
        cerebras = _try_get("cerebras", get_cerebras_llm, temperature=0.3)
        if cerebras:
            _log_routing_decision(role, task_type, "cerebras", "gpt-oss-120b",
                                  f"small context ({total_tokens} tokens)")
            return cerebras

    # ── 5. Fallback: role-based routing ──────────────────────────────
    _log_routing_decision(role, task_type, "role_chain", "get_llm_for_role",
                          "default fallback")
    return get_llm_for_role(role)


# ═══════════════════════════════════════════════════════
# VALIDACIÓN
# ═══════════════════════════════════════════════════════

def validate_keys() -> dict:
    status = {
        "minimax": bool(os.getenv("MINIMAX_API_KEY")),
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
