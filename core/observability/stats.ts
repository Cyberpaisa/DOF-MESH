/** Compute arithmetic mean. Returns 0 for empty arrays. */
export function computeMean(values: number[]): number {
  if (values.length === 0) return 0;
  let sum = 0;
  for (const v of values) sum += v;
  return sum / values.length;
}

/** Compute sample standard deviation with Bessel's correction (n-1). Returns 0 for n <= 1. */
export function computeStd(values: number[]): number {
  if (values.length <= 1) return 0;
  const mean = computeMean(values);
  let sumSq = 0;
  for (const v of values) {
    const diff = v - mean;
    sumSq += diff * diff;
  }
  return Math.sqrt(sumSq / (values.length - 1));
}
