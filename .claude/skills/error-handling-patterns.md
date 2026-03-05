---
name: error-handling-patterns
description: Error handling patterns for DOF SDK — resilient multi-agent LLM systems with graceful degradation, retry logic, and deterministic error classification. Use when implementing error handling, improving reliability, or debugging production issues.
---

# Error Handling Patterns — DOF Adapted

Build resilient multi-agent LLM systems with robust error handling that gracefully degrades under infrastructure failures.

## When to Use This Skill

- Implementing error handling in new DOF modules
- Adding retry logic for provider failures
- Designing error-resilient governance pipelines
- Improving observability of error paths
- Implementing circuit breaker patterns for LLM providers
- Handling async/concurrent errors in crew execution

## DOF Error Classification

DOF uses deterministic error classification (no LLM) via `core/observability.py`:

```python
from dof import classify_error, ErrorClass

# Error classes
ErrorClass.INFRA_FAILURE     # Provider down, network error, rate limit
ErrorClass.GOVERNANCE_BLOCK  # Hard rule violation
ErrorClass.TIMEOUT           # Request timeout
ErrorClass.INVALID_OUTPUT    # Unparseable or malformed output
ErrorClass.UNKNOWN           # Unclassified error
```

## DOF Exception Hierarchy

```python
class DOFError(Exception):
    """Base exception for all DOF errors."""
    pass

class GovernanceViolation(DOFError):
    """Raised when a hard governance rule is violated."""
    def __init__(self, violations: list, score: float):
        self.violations = violations
        self.score = score
        super().__init__(f"Governance failed: {violations}")

class ProviderExhausted(DOFError):
    """Raised when all providers in a chain are exhausted."""
    def __init__(self, provider_chain: list):
        self.provider_chain = provider_chain
        super().__init__(f"All providers exhausted: {provider_chain}")

class ASTViolation(DOFError):
    """Raised when generated code fails AST verification."""
    def __init__(self, violations: list, score: float):
        self.violations = violations
        self.score = score
        super().__init__(f"AST verification failed: {violations}")
```

## Retry with Provider Fallback (DOF Pattern)

DOF uses TTL backoff (5→10→20 min) for provider failures:

```python
def retry_with_fallback(func, providers: list, max_retries: int = 3):
    """DOF retry pattern: try each provider in chain before failing."""
    last_error = None
    for attempt in range(max_retries):
        for provider in providers:
            if provider.is_exhausted():
                continue  # Skip providers in TTL backoff
            try:
                return func(provider=provider)
            except Exception as e:
                last_error = e
                provider.mark_failed()  # Start TTL backoff
                logger.warning(f"Provider {provider.name} failed: {e}")
                continue
    raise ProviderExhausted([p.name for p in providers])
```

## Graceful Degradation Pattern

```python
def with_fallback(primary, fallback, log_error=True):
    """Try primary function, fall back on error."""
    try:
        return primary()
    except Exception as e:
        if log_error:
            logger.error(f"Primary failed: {e}")
        return fallback()

# DOF usage: cache → database → default
def get_metrics():
    return with_fallback(
        primary=lambda: cache.get_metrics(),
        fallback=lambda: compute_metrics_from_traces()
    )
```

## Circuit Breaker for LLM Providers

```python
from enum import Enum
from datetime import datetime, timedelta

class CircuitState(Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failing, reject requests
    HALF_OPEN = "half_open" # Testing if recovered

class ProviderCircuitBreaker:
    def __init__(self, failure_threshold=5, timeout_minutes=5):
        self.failure_threshold = failure_threshold
        self.timeout = timedelta(minutes=timeout_minutes)
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.last_failure_time = None

    def call(self, func):
        if self.state == CircuitState.OPEN:
            if datetime.now() - self.last_failure_time > self.timeout:
                self.state = CircuitState.HALF_OPEN
            else:
                raise ProviderExhausted(["circuit_open"])
        try:
            result = func()
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED

    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
```

## Context Managers for DOF Resources

```python
from contextlib import contextmanager

@contextmanager
def governed_execution(enforcer):
    """Ensure governance is checked even on error."""
    try:
        yield enforcer
    except GovernanceViolation as e:
        logger.error(f"Governance violation: {e.violations}")
        raise
    except Exception as e:
        logger.exception(f"Unexpected error during governed execution")
        raise DOFError("Execution failed") from e
```

## Best Practices for DOF

1. **Classify errors deterministically**: use `classify_error()`, never LLM
2. **Log to JSONL**: every error goes to the audit trail
3. **Preserve context**: include provider name, agent, step_index in error metadata
4. **Fail fast on governance**: hard rule violations should block immediately
5. **Retry on infra**: provider failures get retry with TTL backoff
6. **Don't swallow errors**: log or re-raise, never silently ignore
7. **Clean up resources**: use context managers for crew execution
8. **Record in StepTrace**: every error updates the observability trace

## Common Pitfalls in DOF

- Catching `Exception` broadly and losing the error class
- Not marking provider as failed (skipping TTL backoff)
- Retrying governance violations (they're deterministic — same input = same result)
- Missing JSONL audit log for error events
- Not updating `RunTrace.steps` with error information
- Using `time.sleep()` in retry loops without backoff factor
