import random
import time
from dataclasses import dataclass


@dataclass
class BetaParams:
    alpha: float = 1.0
    beta: float = 1.0
    last_decay: float | None = None

    def __post_init__(self):
        if self.last_decay is None:
            self.last_decay = time.time()

    def mean(self):
        return self.alpha / (self.alpha + self.beta)

    def variance(self):
        a = self.alpha
        b = self.beta
        return (a * b) / (((a + b) ** 2) * (a + b + 1))

    def sample(self):
        return random.betavariate(self.alpha, self.beta)


class BayesianProviderSelector:

    def __init__(self, providers=None, decay_interval=3600, decay_factor=0.9):
        self.providers = providers or []
        self.decay_interval = decay_interval
        self.decay_factor = decay_factor
        self.reset()

    def reset(self):
        self._providers = {p: BetaParams() for p in self.providers}

    def _ensure(self, provider):
        if provider not in self._providers:
            self._providers[provider] = BetaParams()

    def record_success(self, provider):
        self._ensure(provider)
        self._providers[provider].alpha += 1

    def record_failure(self, provider):
        self._ensure(provider)
        self._providers[provider].beta += 1

    def _apply_decay(self, p: BetaParams):
        now = time.time()
        if now - p.last_decay > self.decay_interval:
            p.alpha = max(1.0, p.alpha * self.decay_factor)
            p.beta = max(1.0, p.beta * self.decay_factor)
            p.last_decay = now

    def get_confidence(self, provider):
        if provider not in self._providers:
            return 0.5
        p = self._providers[provider]
        self._apply_decay(p)
        return p.mean()

    def get_all_confidences(self):
        return {k: self.get_confidence(k) for k in self._providers}

    def get_status(self):
        total = sum((p.alpha + p.beta - 2) for p in self._providers.values())
        return {
            "providers": len(self._providers),
            "total_observations": int(total),
        }

    def select(self, providers=None):
        candidates = providers or self.providers
        if not candidates:
            raise ValueError("No providers available")

        scores = {}

        for p in candidates:
            self._ensure(p)
            params = self._providers[p]
            self._apply_decay(params)
            scores[p] = params.sample()

        return max(scores, key=scores.get)
