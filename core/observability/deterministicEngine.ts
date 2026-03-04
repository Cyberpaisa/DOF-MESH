import type { ExecutionConfig, ExecutionMetrics, RngFn } from "./types";
import { shouldFail } from "./failureInjector";
import { successMetrics, failedMetrics } from "./metrics";

/**
 * Mulberry32 — deterministic 32-bit PRNG.
 * Returns a function that produces values in [0, 1) from a given seed.
 * No Math.random() usage.
 */
export function mulberry32(seed: number): RngFn {
  let state = seed | 0;
  return (): number => {
    state = (state + 0x6d2b79f5) | 0;
    let t = Math.imul(state ^ (state >>> 15), 1 | state);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * Execute a single deterministic run across providers with bounded retry.
 *
 * Providers are tried in fixed order (no shuffling).
 * Failure is decided by the deterministic PRNG via failureInjector.
 * Retries rotate through providers up to maxRetries.
 */
export function runDeterministic(config: ExecutionConfig, rng: RngFn): ExecutionMetrics {
  const { providerList, failureProbability, maxRetries } = config;
  let providerFailures = 0;
  let retriesUsed = 0;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    const providerIndex = attempt % providerList.length;
    const failed = shouldFail(providerIndex, failureProbability, rng);

    if (!failed) {
      // Provider succeeded
      return successMetrics(retriesUsed, providerFailures);
    }

    // Provider failed
    providerFailures++;
    if (attempt < maxRetries) {
      retriesUsed++;
    }
  }

  // All retries exhausted
  return failedMetrics(providerFailures);
}
