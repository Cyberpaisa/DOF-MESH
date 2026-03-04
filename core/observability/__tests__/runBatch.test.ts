import { runBatch } from "../index";
import type { BatchConfig, BatchResult } from "../types";

const BASE_CONFIG: BatchConfig = {
  providers: ["groq", "cerebras", "nvidia"],
  failureProbability: 0.3,
  seed: 42,
  runs: 20,
  maxRetries: 3,
};

function assert(condition: boolean, message: string): void {
  if (!condition) throw new Error(`FAIL: ${message}`);
}

function assertEq(a: number, b: number, message: string): void {
  if (a !== b) throw new Error(`FAIL: ${message} — got ${a}, expected ${b}`);
}

// 1) Reproducibility: same config → identical results
function testReproducibility(): void {
  const r1 = runBatch(BASE_CONFIG);
  const r2 = runBatch(BASE_CONFIG);

  assertEq(r1.SS, r2.SS, "SS not reproducible");
  assertEq(r1.PFI, r2.PFI, "PFI not reproducible");
  assertEq(r1.RP, r2.RP, "RP not reproducible");
  assertEq(r1.GCR, r2.GCR, "GCR not reproducible");
  assertEq(r1.SSR, r2.SSR, "SSR not reproducible");
  assertEq(r1.SS_std, r2.SS_std, "SS_std not reproducible");
  assertEq(r1.PFI_std, r2.PFI_std, "PFI_std not reproducible");
  assertEq(r1.RP_std, r2.RP_std, "RP_std not reproducible");
  assertEq(r1.GCR_std, r2.GCR_std, "GCR_std not reproducible");
  assertEq(r1.SSR_std, r2.SSR_std, "SSR_std not reproducible");
  assertEq(r1.totalRuns, r2.totalRuns, "totalRuns not reproducible");
  assertEq(r1.results.length, r2.results.length, "results length not reproducible");

  for (let i = 0; i < r1.results.length; i++) {
    const a = r1.results[i].metrics;
    const b = r2.results[i].metrics;
    assertEq(a.success ? 1 : 0, b.success ? 1 : 0, `run ${i} success mismatch`);
    assertEq(a.providerFailures, b.providerFailures, `run ${i} providerFailures mismatch`);
    assertEq(a.retriesUsed, b.retriesUsed, `run ${i} retriesUsed mismatch`);
  }

  console.log("PASS: reproducibility");
}

// 2) Seed variation: different seed → at least one metric differs
function testSeedVariation(): void {
  const r1 = runBatch(BASE_CONFIG);
  const r2 = runBatch({ ...BASE_CONFIG, seed: 9999 });

  const different =
    r1.SS !== r2.SS ||
    r1.PFI !== r2.PFI ||
    r1.RP !== r2.RP ||
    r1.GCR !== r2.GCR ||
    r1.SSR !== r2.SSR;

  assert(different, "changing seed should produce at least one different metric");
  console.log("PASS: seed variation");
}

// 3) failureProbability = 0 → perfect execution
function testZeroFailure(): void {
  const r = runBatch({ ...BASE_CONFIG, failureProbability: 0 });

  assertEq(r.SS, 1, "SS should be 1 with no failures");
  assertEq(r.PFI, 0, "PFI should be 0 with no failures");
  assertEq(r.RP, 0, "RP should be 0 with no failures");

  console.log("PASS: zero failure");
}

// 4) failureProbability = 1, maxRetries = 0 → total failure
function testTotalFailure(): void {
  const r = runBatch({ ...BASE_CONFIG, failureProbability: 1, maxRetries: 0 });

  assertEq(r.SS, 0, "SS should be 0 with 100% failure and no retries");

  console.log("PASS: total failure");
}

// 5) RP never exceeds maxRetries for any run
function testRetryBound(): void {
  const configs: BatchConfig[] = [
    { ...BASE_CONFIG, maxRetries: 1 },
    { ...BASE_CONFIG, maxRetries: 3 },
    { ...BASE_CONFIG, maxRetries: 5, failureProbability: 0.8 },
  ];

  for (const config of configs) {
    const r = runBatch(config);
    for (const run of r.results) {
      assert(
        run.metrics.retriesUsed <= config.maxRetries,
        `run ${run.runIndex} retriesUsed (${run.metrics.retriesUsed}) exceeds maxRetries (${config.maxRetries})`,
      );
    }
  }

  console.log("PASS: retry bound");
}

// Run all tests
function main(): void {
  console.log("Running deterministic observability tests...\n");

  testReproducibility();
  testSeedVariation();
  testZeroFailure();
  testTotalFailure();
  testRetryBound();

  console.log("\nAll tests passed.");
}

main();
