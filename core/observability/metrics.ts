import type { ExecutionMetrics } from "./types";

/** Create a successful execution metrics object. */
export function successMetrics(retriesUsed: number, providerFailures: number): ExecutionMetrics {
  return {
    success: true,
    providerFailures,
    retriesUsed,
    governancePassed: true,   // simulated — always passes
    supervisorRejected: false, // simulated — never rejects
  };
}

/** Create a failed execution metrics object. */
export function failedMetrics(providerFailures: number): ExecutionMetrics {
  return {
    success: false,
    providerFailures,
    retriesUsed: providerFailures, // each failure consumed a retry
    governancePassed: true,        // governance is evaluated independently
    supervisorRejected: false,
  };
}
