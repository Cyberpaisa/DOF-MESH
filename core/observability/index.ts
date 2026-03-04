import type { BatchConfig, BatchResult, RunResult } from "./types";
import { mulberry32, runDeterministic } from "./deterministicEngine";
import { computeMean, computeStd } from "./stats";

// Re-export public API
export { mulberry32, runDeterministic } from "./deterministicEngine";
export { shouldFail } from "./failureInjector";
export { successMetrics, failedMetrics } from "./metrics";
export { computeMean, computeStd } from "./stats";
export type {
  ExecutionConfig, BatchConfig, ExecutionMetrics,
  RunResult, BatchResult, RngFn,
} from "./types";

/**
 * Run a deterministic batch of N executions and compute aggregate metrics.
 *
 * Each run uses seed + runIndex as its PRNG seed for controlled variation.
 * Metrics: SS, PFI, RP, GCR, SSR (with std dev via Bessel correction).
 */
export function runBatch(config: BatchConfig): BatchResult {
  const { providers, failureProbability, seed, runs, maxRetries } = config;
  const results: RunResult[] = [];

  for (let i = 0; i < runs; i++) {
    const rng = mulberry32(seed + i);
    const metrics = runDeterministic(
      { providerList: providers, failureProbability, seed: seed + i, maxRetries },
      rng,
    );
    results.push({
      runIndex: i,
      providers: [...providers],
      metrics,
    });
  }

  // Per-run binary indicators for metric computation
  const ssValues = results.map((r) => (r.metrics.success ? 1 : 0));
  const pfiValues = results.map((r) => r.metrics.providerFailures);
  const rpValues = results.map((r) => r.metrics.retriesUsed);
  const gcrValues = results.map((r) => (r.metrics.governancePassed ? 1 : 0));

  const successfulRuns = results.filter((r) => r.metrics.success);
  const ssrValues = successfulRuns.length > 0
    ? successfulRuns.map((r) => (r.metrics.supervisorRejected ? 1 : 0))
    : [0];

  return {
    SS: computeMean(ssValues),
    PFI: computeMean(pfiValues),
    RP: computeMean(rpValues),
    GCR: computeMean(gcrValues),
    SSR: computeMean(ssrValues),
    SS_std: computeStd(ssValues),
    PFI_std: computeStd(pfiValues),
    RP_std: computeStd(rpValues),
    GCR_std: computeStd(gcrValues),
    SSR_std: computeStd(ssrValues),
    totalRuns: runs,
    results,
  };
}
