import type { RngFn } from "./types";

/**
 * Determine whether a provider should fail on this invocation.
 * Uses the deterministic RNG — never Math.random().
 *
 * @param providerIndex - Index of the provider being tested (unused but available for future per-provider policies)
 * @param failureProbability - Probability of failure in [0, 1]
 * @param rng - Deterministic PRNG function returning values in [0, 1)
 */
export function shouldFail(
  providerIndex: number,
  failureProbability: number,
  rng: RngFn,
): boolean {
  return rng() < failureProbability;
}
