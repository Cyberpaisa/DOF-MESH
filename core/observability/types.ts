/** Configuration for a deterministic execution batch. */
export interface ExecutionConfig {
  providerList: string[];
  failureProbability: number; // [0, 1]
  seed: number;
  maxRetries: number;
}

/** Configuration for a full batch run. */
export interface BatchConfig {
  providers: string[];
  failureProbability: number; // [0, 1]
  seed: number;
  runs: number;
  maxRetries: number;
}

/** Metrics collected from a single execution run. */
export interface ExecutionMetrics {
  success: boolean;
  providerFailures: number;
  retriesUsed: number;
  governancePassed: boolean;
  supervisorRejected: boolean;
}

/** Result of a single deterministic run. */
export interface RunResult {
  runIndex: number;
  providers: string[];
  metrics: ExecutionMetrics;
}

/** Aggregated metrics from a batch of runs. */
export interface BatchResult {
  SS: number;  // Stability Score
  PFI: number; // Provider Fragility Index
  RP: number;  // Retry Pressure
  GCR: number; // Governance Compliance Rate
  SSR: number; // Supervisor Strictness Ratio
  SS_std: number;
  PFI_std: number;
  RP_std: number;
  GCR_std: number;
  SSR_std: number;
  totalRuns: number;
  results: RunResult[];
}

/** Deterministic PRNG function type. */
export type RngFn = () => number;
