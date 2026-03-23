import os
import random
import time
from typing import Dict, List, Optional

try:
    from crewai import LLM
except ImportError:
    LLM = None

# Zo se usa via ask_zo() directamente, NO via LiteLLM
# LiteLLM usa groq como primario


# ═══════════════════════════════════════════════════════
# BetaParams — Beta distribution for Thompson Sampling
# ═══════════════════════════════════════════════════════

class BetaParams:
    """Beta distribution parameters for a single provider."""

    def __init__(self, alpha: float = 1.0, beta: float = 1.0,
                 last_decay: Optional[float] = None):
        self.alpha = alpha
        self.beta = beta
        self.last_decay = last_decay or time.time()

    def mean(self) -> float:
        """Expected success rate: E[Beta] = α / (α + β)."""
        return self.alpha / (self.alpha + self.beta)

    def variance(self) -> float:
        """Var[Beta] = αβ / ((α+β)²(α+β+1))."""
        ab = self.alpha + self.beta
        return (self.alpha * self.beta) / (ab * ab * (ab + 1.0))

    def sample(self) -> float:
        """Draw a sample from the Beta distribution."""
        return random.betavariate(self.alpha, self.beta)


# ═══════════════════════════════════════════════════════
# ProviderManager — LLM instantiation
# ═══════════════════════════════════════════════════════

class ProviderManager:
    @staticmethod
    def get_llm_for_role(role: str):
        if LLM is None:
            raise RuntimeError("crewai not installed")
        key = os.getenv("GROQ_API_KEY")
        if key:
            return LLM(model="groq/llama-3.3-70b-versatile", api_key=key, temperature=0.3, max_tokens=4096)
        key = os.getenv("CEREBRAS_API_KEY")
        if key:
            return LLM(model="cerebras/llama-3.3-70b", api_key=key, temperature=0.3, max_tokens=4096)
        raise RuntimeError("No hay provider disponible (GROQ_API_KEY o CEREBRAS_API_KEY requerida)")


# ═══════════════════════════════════════════════════════
# BayesianProviderSelector — Thompson Sampling with decay
# ═══════════════════════════════════════════════════════

class BayesianProviderSelector:
    """Select providers using Thompson Sampling with temporal decay.

    Each provider maintains Beta(α, β) parameters. Selection samples from
    each Beta distribution and picks the provider with the highest sample.
    Observations decay exponentially (λ=0.95 per hour) so recent results
    matter more than old ones.
    """

    DECAY_LAMBDA = 0.95       # decay factor per hour
    DECAY_INTERVAL = 3600.0   # apply decay every hour

    def __init__(self, providers: Optional[List[str]] = None):
        self._providers: Dict[str, BetaParams] = {}
        if providers:
            for name in providers:
                self._providers[name] = BetaParams()

    def reset(self) -> None:
        """Reset all providers to uniform prior Beta(1, 1)."""
        now = time.time()
        for name in list(self._providers.keys()):
            self._providers[name] = BetaParams(last_decay=now)

    def _ensure_provider(self, name: str) -> None:
        """Initialize a provider if not yet tracked."""
        if name not in self._providers:
            self._providers[name] = BetaParams()

    def select_provider(self, available: List[str]) -> str:
        """Pick the best provider via Thompson Sampling.

        Args:
            available: List of provider names to choose from.

        Returns:
            Name of the selected provider.

        Raises:
            ValueError: If available list is empty.
        """
        if not available:
            raise ValueError("No providers available for selection")

        self._apply_decay()

        best_name = None
        best_sample = -1.0
        for name in available:
            self._ensure_provider(name)
            sample = self._providers[name].sample()
            if sample > best_sample:
                best_sample = sample
                best_name = name

        return best_name

    def record_success(self, provider: str) -> None:
        """Record a successful call — increments α."""
        self._ensure_provider(provider)
        self._providers[provider].alpha += 1.0

    def record_failure(self, provider: str) -> None:
        """Record a failed call — increments β."""
        self._ensure_provider(provider)
        self._providers[provider].beta += 1.0

    def get_confidence(self, provider: str) -> float:
        """Return the Beta mean (expected success rate) for a provider."""
        self._ensure_provider(provider)
        return self._providers[provider].mean()

    def get_all_confidences(self) -> Dict[str, float]:
        """Return confidence scores for all tracked providers."""
        return {name: params.mean() for name, params in self._providers.items()}

    def _apply_decay(self) -> None:
        """Apply temporal decay: α and β shrink toward 1.0 over time."""
        now = time.time()
        for params in self._providers.values():
            elapsed = now - params.last_decay
            hours = elapsed / self.DECAY_INTERVAL
            if hours < 1.0:
                continue
            factor = self.DECAY_LAMBDA ** hours
            params.alpha = max(1.0, params.alpha * factor)
            params.beta = max(1.0, params.beta * factor)
            params.last_decay = now

    def get_status(self) -> Dict[str, dict]:
        """Return full Bayesian state for all providers."""
        result = {}
        for name, params in self._providers.items():
            result[name] = {
                "alpha": params.alpha,
                "beta": params.beta,
                "confidence": params.mean(),
                "variance": params.variance(),
                "total_observations": (params.alpha + params.beta) - 2.0,
            }
        return result

def get_llm_for_role(role: str):
    return ProviderManager.get_llm_for_role(role)

pm = ProviderManager()

# ═══════════════════════════════════════════════════════
# ZO API - Llamada directa (sin litellm)
# ═══════════════════════════════════════════════════════

def ask_zo(prompt: str, model: str = "vercel:minimax/minimax-m2.5") -> str:
    """Llamada directa a la API de Zo (funciona siempre)."""
    import requests
    api_key = os.getenv("ZO_API_KEY")
    if not api_key:
        return "ERROR: ZO_API_KEY no configurada"
    
    try:
        resp = requests.post(
            "https://api.zo.computer/zo/ask",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={"input": prompt, "model_name": model},
            timeout=60
        )
        if resp.status_code == 200:
            return resp.json().get("output", resp.text)
        return f"ERROR: {resp.status_code} - {resp.text}"
    except Exception as e:
        return f"ERROR: {str(e)[:100]}"
