# Deterministic Degradation Curves for Multi-Agent Systems

*Cyber Paisa / Enigma Group — March 2026*

---

## 1. The Hidden Problem

Multi-agent LLM systems fail in ways that are invisible to their operators. A pipeline of four agents using three providers can produce a correct-looking output while internally experiencing two rate limits, one retry cascade, and a governance near-miss. The output arrives. The latency was acceptable. Everything looks fine. But the system was one provider exhaustion away from total failure.

This is not a theoretical concern. When you operate multi-agent crews across free-tier LLM providers — Groq, NVIDIA NIM, Cerebras, Zhipu AI — each with different rate limits, model capabilities, and failure characteristics, the failure surface is combinatorial. A rate limit on Groq triggers rotation to Cerebras. Cerebras rejects the output format. The retry goes to NVIDIA NIM, which is also rate-limited. Three providers down in under two seconds, and the only log entry says "crew completed successfully" because the fourth provider eventually responded.

The fundamental problem is attribution. When a multi-agent system degrades, which component caused the degradation? Was it a provider failure? A governance check that inflated retry count? A supervisor that was too strict? Without formal metrics and controlled experiments, these questions have no answer. You are debugging by reading logs and guessing.

We built a framework to replace guessing with measurement.

## 2. Why Chaos Engineering Is Not Enough

The standard approach to resilience testing is chaos engineering: inject random failures and observe what happens. Netflix's Chaos Monkey, Gremlin, LitmusChaos — all follow this pattern. Inject failure at random, measure recovery.

For multi-agent LLM systems, random injection is insufficient for a specific reason: it does not support attribution. If you inject failures randomly across 20 runs and observe that Stability Score dropped from 1.0 to 0.85, you cannot determine whether the degradation is linear, exponential, or step-function. You cannot distinguish between a system that degrades gracefully (SS proportional to failure rate) and one that collapses catastrophically (SS drops to zero above a threshold). Random injection tells you that the system is affected by failures. It does not tell you how.

There is a second problem specific to multi-provider architectures. Provider failures are correlated, not independent. When Groq rate-limits, the retry goes to another provider, which may also be approaching its rate limit. The failure of provider A increases the probability of provider B failing. Random injection does not model this correlation because it treats each injection point independently.

What we need is deterministic failure injection with parametric control: a `failure_rate` parameter that specifies exactly what fraction of runs fail, using index-based selection so that the same rate always produces the same set of failing runs. This is not chaos engineering. It is controlled experimentation.

## 3. Deterministic Failure Injection

The framework introduces a `failure_rate` parameter in the range [0.0, 1.0] that controls the fraction of experimental runs that experience injected provider failures. The injection is deterministic: for `n` runs at rate `f`, the first `floor(n × f)` runs fail. No randomness. No sampling. The same parameters always produce the same partition of failed and successful runs.

This design choice has a specific consequence: the "failing" runs are always the first ones in the sequence. This eliminates ordering effects — you cannot accidentally create a pattern where failures cluster at the end (when providers might be warm) or in the middle (when caches might be populated). The partition is fixed by arithmetic.

For each run designated as "failing," the framework injects a simulated provider exhaustion at a configurable step index. The failure triggers the existing resilience infrastructure: provider rotation, TTL-based cooldown, exponential backoff, and retry logic. The run either recovers (if backup providers are available and the retry succeeds) or fails (if all providers are exhausted). The resulting metrics — Stability Score, Provider Fragility Index, Retry Pressure — reflect the system's actual resilience behavior, not the injection mechanism.

The deterministic mode also controls infrastructure-level randomness beyond failure injection. Provider ordering is fixed via `get_deterministic_providers()`. Session IDs are reset between experiments via `reset_session()`. The `ProviderManager` singleton is reset via `reset_all()` to prevent state leakage between experiments. These three resets — discovered and fixed during a code audit — are essential. Without them, experiment 5 in a sweep inherits exhaustion state from experiment 4, corrupting the independence assumption.

## 4. Parametric Sensitivity: SS(f) = 1 - f/2

We ran 120 experiments across six failure rates: 0%, 10%, 20%, 30%, 50%, 70%. Each rate was tested with 20 independent runs in deterministic mode. The results:

| Failure Rate (f) | SS (mean ± std) | PFI (mean ± std) | RP (mean ± std) | GCR |
|:-:|:-:|:-:|:-:|:-:|
| 0.0 | 1.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 1.0 |
| 0.1 | 0.95 ± 0.15 | 0.10 ± 0.31 | 0.10 ± 0.31 | 1.0 |
| 0.2 | 0.90 ± 0.21 | 0.20 ± 0.41 | 0.20 ± 0.41 | 1.0 |
| 0.3 | 0.85 ± 0.24 | 0.30 ± 0.47 | 0.30 ± 0.47 | 1.0 |
| 0.5 | 0.75 ± 0.26 | 0.50 ± 0.51 | 0.50 ± 0.51 | 1.0 |
| 0.7 | 0.65 ± 0.24 | 0.70 ± 0.47 | 0.70 ± 0.47 | 1.0 |

The Stability Score follows a linear degradation: **SS(f) = 1 - f/2**. This is not a fit — it is an exact analytical result. Each failing run produces SS = 0.5 (half the steps succeed), and each successful run produces SS = 1.0. The population mean is:

```
SS(f) = f × 0.5 + (1 - f) × 1.0 = 1 - f/2
```

This linearity is the first empirical result. It means that, under the framework's two-step crew structure, Stability Score degrades proportionally to failure rate with a coefficient of 0.5. There is no threshold effect, no cliff, no phase transition. Every percentage point of failure rate costs exactly half a percentage point of stability. A system operating at 10% failure rate loses 5% stability. At 50%, it loses 25%.

The standard deviation follows a different pattern. Since each run's SS is a Bernoulli trial (1.0 or 0.5), the variance is:

```
σ²(f) = f(1-f) × (1.0 - 0.5)² = f(1-f)/4
```

Maximum variance occurs at f = 0.5, where σ = 0.25. This is the point of maximum uncertainty — you cannot predict whether the next run will succeed or fail. At the extremes (f near 0 or f near 1), variance approaches zero because the outcome is nearly certain.

The practical implication: if you need to characterize a system's resilience with minimal experimental runs, test at f = 0.3 and f = 0.5. These two points give you the slope of the degradation curve and the maximum variance, from which you can extrapolate the full parametric response.

## 5. Governance Invariance

The most striking result in the sweep is not the degradation curve but the invariance. Governance Compliance Rate (GCR) = 1.0 at every failure rate, from 0% to 70%.

This matters because governance and provider resilience are implemented by different modules (`ConstitutionEnforcer` and `ProviderManager`) that interact through the same execution pipeline. A provider failure triggers a retry, which produces new output, which goes through governance checks. If governance were sensitive to retried output (different wording, different structure, edge-case formatting), GCR would degrade with failure rate. It does not.

The invariance confirms structural decoupling: governance evaluates output content independently of the infrastructure path that produced it. A response that passed governance on the first attempt will also pass governance after two retries and a provider rotation. The constitutional rules (hard rules: no prompt leaks, no harmful content; soft rules: minimum length, required structure) are agnostic to provider identity and retry history.

This is not obvious. In many production systems, retry logic changes the output characteristics — shorter responses under time pressure, different formatting from different models, truncated content when fallback providers have smaller context windows. The framework's simulated crews produce uniform output regardless of provider path, which is what enables the invariance. With real LLM providers, GCR invariance would need to be empirically verified rather than assumed.

Supervisor Strictness Ratio (SSR) = 0.0 across all rates is the complementary result. The meta-supervisor never rejected a completed run. Combined with GCR = 1.0, this means that quality gates are consistently satisfied even as the system experiences increasing failure pressure. The quality pipeline is robust to infrastructure degradation.

## 6. What This Means for AI Infrastructure

Three implications for teams operating multi-agent LLM systems:

**Formal metrics replace log analysis.** The five metrics defined in this framework — SS, PFI, RP, GCR, SSR — provide a quantitative vocabulary for discussing system health. Instead of "the system seems slower lately," you can say "PFI increased from 0.1 to 0.3, indicating provider fragility has tripled." Instead of "quality seems fine," you can verify that GCR and SSR are unchanged. Metrics make degradation visible before it becomes failure.

**Deterministic replay replaces probabilistic retries.** The standard pattern for handling multi-agent failures is to add more retries with longer backoffs. This approach increases latency and masks the underlying failure pattern. Deterministic failure injection provides an alternative: characterize the degradation curve first, then design the retry policy to match. If SS(f) = 1 - f/2, you know that three retries at 30% failure rate will bring effective SS back above 0.95. You can calculate the retry budget instead of guessing.

**Parametric sweeps before deployment.** The 120-experiment sweep took minutes to execute with simulated crews and would take hours with real LLM providers. Either way, the result is a complete degradation profile: how does every metric respond to every failure rate? This profile should be generated before deployment, not discovered in production. When a new provider is added or a rate limit changes, re-run the sweep. The degradation curve is your system's resilience specification.

The framework is 2,252 lines of Python with no external observability dependencies. It wraps any crew that implements `.kickoff()` and produces JSONL traces, CSV exports, and markdown summaries. The metrics are computed from traces, not sampled from logs. The experiment runner handles statistical aggregation with Bessel's correction. The deterministic mode makes every result reproducible.

The degradation curve is not a dashboard. It is a measurement.

---

*Framework: [github.com/Enigma-Team-org/equipo-de-agentes](https://github.com/Enigma-Team-org/equipo-de-agentes)*
*Paper: `paper/PAPER_OBSERVABILITY_LAB.md` (8,700+ words, 13 sections)*
*Data: `experiments/parametric_sweep.csv` (120 runs, 6 failure rates)*
