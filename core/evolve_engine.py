from __future__ import annotations
"""
DOF-EvolveEngine — AlphaEvolve-inspired self-improvement for DOF-MESH.

Optimizes TRACER weights and SOFT_RULE weights using historical validation
data as the fitness signal. Never touches HARD_RULES or Z3 theorems.

Architecture:
    EvolveController → CandidateGenerator (LLM) → DOFEvaluator → Z3Gate → ProgramDatabase

Usage:
    from core.evolve_engine import EvolveController, EvolveConfig, build_tracer_evaluator

    config = EvolveConfig(target="tracer_weights", max_iterations=30, budget_usd=0.50)
    evaluator = build_tracer_evaluator("logs/sentinel/validations.jsonl")
    engine = EvolveController(config, evaluator)
    best = engine.run()
    print(best)  # {"trust": 0.22, "reliability": 0.25, ...}

Safety constraints:
    - HARD_RULES are NOT a valid target — enforced at runtime
    - Z3 theorems are NOT a valid target — enforced at runtime
    - All adopted variants are saved to logs/evolve/adopted.json, NOT written to source files
    - Every candidate is validated against formal invariants before evaluation
    - Full audit trail in logs/evolve/runs.jsonl
"""

import json
import math
import random
import time
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger("dof.evolve")

# ─── Constants ────────────────────────────────────────────────────────────────

VALID_TARGETS = {"tracer_weights", "soft_rule_weights"}
FORBIDDEN_TARGETS = {"hard_rules", "z3_theorems", "constitution", "governance_hard"}

DEFAULT_TRACER_WEIGHTS = {
    "trust":       0.20,
    "reliability": 0.20,
    "autonomy":    0.15,
    "capability":  0.20,
    "economics":   0.10,
    "reputation":  0.15,
}

TRACER_WEIGHT_BOUNDS = {
    "trust":       (0.05, 0.40),
    "reliability": (0.05, 0.40),
    "autonomy":    (0.05, 0.35),
    "capability":  (0.05, 0.40),
    "economics":   (0.03, 0.30),
    "reputation":  (0.03, 0.30),
}

LOGS_DIR = Path("logs/evolve")


# ─── Data Classes ─────────────────────────────────────────────────────────────

@dataclass
class EvolveConfig:
    """Configuration for a single evolution run."""
    target: str                          # "tracer_weights" | "soft_rule_weights"
    max_iterations: int = 40
    population_size: int = 10
    budget_usd: float = 1.00             # max LLM spend per run
    min_improvement_pct: float = 0.5     # minimum delta to adopt a variant
    mutation_temperature: float = 0.25   # how aggressively to mutate (0.1-0.5)
    llm_model: str = "claude-haiku-4-5-20251001"  # cheap model for mutations
    random_seed: int = 42
    verbose: bool = True

    def __post_init__(self):
        if self.target in FORBIDDEN_TARGETS:
            raise ValueError(
                f"Target '{self.target}' is FORBIDDEN. "
                f"EvolveEngine never modifies HARD_RULES or Z3 theorems."
            )
        if self.target not in VALID_TARGETS:
            raise ValueError(
                f"Unknown target '{self.target}'. Valid: {VALID_TARGETS}"
            )


@dataclass
class Candidate:
    """A single parameter variant with its evaluation score."""
    params: dict
    score: float = 0.0
    iteration: int = 0
    generation_method: str = "random"   # "random" | "llm" | "crossover"
    cost_usd: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict:
        return {
            "params": self.params,
            "score": self.score,
            "iteration": self.iteration,
            "generation_method": self.generation_method,
            "cost_usd": self.cost_usd,
            "timestamp": self.timestamp,
        }


@dataclass
class EvolveResult:
    """Final result of an evolution run."""
    target: str
    best_params: dict
    best_score: float
    baseline_score: float
    improvement_pct: float
    total_iterations: int
    total_cost_usd: float
    adopted: bool
    run_duration_s: float
    run_id: str
    candidates_evaluated: int

    @property
    def summary(self) -> str:
        status = "✅ ADOPTED" if self.adopted else "⏭  SKIPPED (no improvement)"
        return (
            f"{status} | {self.target} | "
            f"baseline={self.baseline_score:.4f} → best={self.best_score:.4f} "
            f"(+{self.improvement_pct:.2f}%) | "
            f"{self.total_iterations} iterations | ${self.total_cost_usd:.4f}"
        )


# ─── Invariant Validators ──────────────────────────────────────────────────────

def validate_tracer_weights(weights: dict) -> tuple[bool, str]:
    """
    Formal invariants for TRACER weight candidates.
    Returns (is_valid, reason).
    """
    required_keys = set(DEFAULT_TRACER_WEIGHTS.keys())
    if set(weights.keys()) != required_keys:
        return False, f"Wrong keys: expected {required_keys}, got {set(weights.keys())}"

    total = sum(weights.values())
    if abs(total - 1.0) > 1e-4:
        return False, f"Weights sum to {total:.6f}, must be 1.0"

    for dim, val in weights.items():
        lo, hi = TRACER_WEIGHT_BOUNDS[dim]
        if val < lo or val > hi:
            return False, f"Weight '{dim}'={val:.3f} out of bounds [{lo}, {hi}]"

    return True, "OK"


def normalize_to_simplex(weights: dict) -> dict:
    """Project weights onto the probability simplex (sum=1.0)."""
    total = sum(weights.values())
    if total == 0:
        keys = list(weights.keys())
        return {k: 1.0 / len(keys) for k in keys}
    return {k: v / total for k, v in weights.items()}


def clip_to_bounds(weights: dict) -> dict:
    """Clip each weight to its allowed range, then renormalize."""
    clipped = {}
    for dim, val in weights.items():
        lo, hi = TRACER_WEIGHT_BOUNDS.get(dim, (0.01, 1.0))
        clipped[dim] = max(lo, min(hi, val))
    return normalize_to_simplex(clipped)


# ─── Evaluators ───────────────────────────────────────────────────────────────

def build_tracer_evaluator(
    validations_log: str = "logs/sentinel/validations.jsonl",
    min_records: int = 3,
) -> Callable[[dict], float]:
    """
    Build an evaluator that scores TRACER weight candidates against
    historical validation records.

    Metric: Spearman-like rank correlation between the recalculated
    TRACER score (with candidate weights) and the agent's actual outcome
    (PASS=1.0, PARTIAL=0.5, FAIL=0.0).

    With few records (<30), adds a regularization term that penalizes
    deviations from the DOF theoretical priors (trust+capability+reliability
    should have higher weight than economics+reputation for governance).

    Returns a callable: weights_dict → float (higher is better, range 0-1).
    """
    records = []
    log_path = Path(validations_log)

    if log_path.exists():
        with open(log_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                    if r.get("tracer") and r.get("result") in ("PASS", "PARTIAL", "FAIL"):
                        records.append(r)
                except json.JSONDecodeError:
                    continue

    if len(records) < min_records:
        logger.warning(
            f"[EvolveEngine] Only {len(records)} validation records found "
            f"(minimum {min_records}). Using simulation-augmented evaluator."
        )
        records = _augment_with_simulated_records(records)

    logger.info(f"[EvolveEngine] Evaluator built with {len(records)} records")

    def evaluate(weights: dict) -> float:
        # Map outcomes to numeric
        outcome_map = {"PASS": 1.0, "PARTIAL": 0.5, "FAIL": 0.0}

        predicted = []
        actual = []
        for r in records:
            dims = r["tracer"]["dimensions"]
            # Recalculate TRACER score with candidate weights
            new_score = sum(
                weights.get(dim, 0.0) * dims.get(dim, 0.0)
                for dim in weights
            )
            predicted.append(new_score)
            actual.append(outcome_map.get(r["result"], 0.5))

        # Spearman rank correlation (robust to outliers)
        corr = _spearman_correlation(predicted, actual)

        # Regularization: penalize extreme deviations from governance priors
        # Governance theory: trust + reliability + capability should dominate
        governance_core = weights.get("trust", 0) + weights.get("reliability", 0) + weights.get("capability", 0)
        prior_penalty = max(0.0, 0.50 - governance_core) * 0.5  # penalize if core < 50%

        score = corr - prior_penalty

        # Scale to [0, 1]
        return max(0.0, min(1.0, (score + 1.0) / 2.0))

    return evaluate


def _augment_with_simulated_records(real_records: list) -> list:
    """
    When insufficient real data exists, generate synthetic validation
    scenarios consistent with the DOF agent model.

    Synthetic records represent the theoretical extremes:
    - Perfect agent: all dimensions maxed → PASS
    - Failed agent: reliability=0, economics=0 → FAIL
    - Typical production agent: mixed scores → PARTIAL
    """
    augmented = list(real_records)

    # Theoretical PASS scenario
    augmented.append({
        "result": "PASS",
        "tracer": {"dimensions": {
            "trust": 95.0, "reliability": 95.0, "autonomy": 90.0,
            "capability": 90.0, "economics": 85.0, "reputation": 80.0,
        }},
        "_synthetic": True,
    })

    # Theoretical FAIL scenario (no connectivity)
    augmented.append({
        "result": "FAIL",
        "tracer": {"dimensions": {
            "trust": 40.0, "reliability": 0.0, "autonomy": 30.0,
            "capability": 30.0, "economics": 0.0, "reputation": 0.0,
        }},
        "_synthetic": True,
    })

    # Theoretical FAIL scenario (identity issues)
    augmented.append({
        "result": "FAIL",
        "tracer": {"dimensions": {
            "trust": 0.0, "reliability": 80.0, "autonomy": 60.0,
            "capability": 40.0, "economics": 50.0, "reputation": 0.0,
        }},
        "_synthetic": True,
    })

    # Good production agent
    augmented.append({
        "result": "PARTIAL",
        "tracer": {"dimensions": {
            "trust": 75.0, "reliability": 85.0, "autonomy": 75.0,
            "capability": 55.0, "economics": 90.0, "reputation": 20.0,
        }},
        "_synthetic": True,
    })

    # Weak production agent
    augmented.append({
        "result": "PARTIAL",
        "tracer": {"dimensions": {
            "trust": 60.0, "reliability": 50.0, "autonomy": 40.0,
            "capability": 45.0, "economics": 60.0, "reputation": 10.0,
        }},
        "_synthetic": True,
    })

    return augmented


def _spearman_correlation(x: list, y: list) -> float:
    """Compute Spearman rank correlation without scipy dependency."""
    n = len(x)
    if n < 2:
        return 0.0

    def rank(lst):
        sorted_idx = sorted(range(n), key=lambda i: lst[i])
        ranks = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j < n and lst[sorted_idx[j]] == lst[sorted_idx[i]]:
                j += 1
            avg_rank = (i + j - 1) / 2.0
            for k in range(i, j):
                ranks[sorted_idx[k]] = avg_rank
            i = j
        return ranks

    rx, ry = rank(x), rank(y)
    mean_rx = sum(rx) / n
    mean_ry = sum(ry) / n
    num = sum((rx[i] - mean_rx) * (ry[i] - mean_ry) for i in range(n))
    den_x = math.sqrt(sum((rx[i] - mean_rx) ** 2 for i in range(n)))
    den_y = math.sqrt(sum((ry[i] - mean_ry) ** 2 for i in range(n)))

    if den_x == 0 or den_y == 0:
        return 0.0
    return num / (den_x * den_y)


# ─── Candidate Generator ──────────────────────────────────────────────────────

class CandidateGenerator:
    """
    Generates TRACER weight variants using two strategies:
    1. LLM-guided mutation (uses the configured model)
    2. Random perturbation (fallback, zero cost)
    """

    def __init__(self, config: EvolveConfig):
        self.config = config
        self._llm = None
        self._cost_accumulated = 0.0

    def _get_llm(self):
        """Lazy-load Anthropic client."""
        if self._llm is None:
            try:
                import anthropic
                self._llm = anthropic.Anthropic()
            except ImportError:
                logger.warning("[EvolveEngine] anthropic not available — using random mutation only")
        return self._llm

    def generate(
        self,
        current_best: Candidate,
        history: list[Candidate],
        iteration: int,
    ) -> Candidate:
        """Generate a new candidate. Uses LLM if budget allows, else random."""
        # Use LLM for 60% of iterations when budget allows
        use_llm = (
            self._cost_accumulated < self.config.budget_usd * 0.8
            and random.random() < 0.6
            and self._get_llm() is not None
        )

        if use_llm:
            return self._llm_mutation(current_best, history, iteration)
        else:
            return self._random_mutation(current_best, iteration)

    def _random_mutation(self, base: Candidate, iteration: int) -> Candidate:
        """Gaussian perturbation on the weight simplex."""
        rng = random.Random(self.config.random_seed + iteration)
        new_params = {}
        for dim, val in base.params.items():
            noise = rng.gauss(0, self.config.mutation_temperature * 0.1)
            new_params[dim] = val + noise

        new_params = clip_to_bounds(new_params)
        valid, reason = validate_tracer_weights(new_params)
        if not valid:
            new_params = normalize_to_simplex(clip_to_bounds(new_params))

        return Candidate(
            params=new_params,
            iteration=iteration,
            generation_method="random",
            cost_usd=0.0,
        )

    def _llm_mutation(
        self,
        best: Candidate,
        history: list[Candidate],
        iteration: int,
    ) -> Candidate:
        """Ask the LLM to propose a parameter variant."""
        top_history = sorted(history, key=lambda c: c.score, reverse=True)[:5]
        history_str = json.dumps(
            [{"params": c.params, "score": round(c.score, 4)} for c in top_history],
            indent=2,
        )

        prompt = f"""You are optimizing TRACER weight parameters for the DOF-MESH agent governance system.

Current best parameters (score={best.score:.4f}):
{json.dumps(best.params, indent=2)}

Top-5 history:
{history_str}

TRACER dimensions:
- trust: TLS, identity, proxy detection (governance critical)
- reliability: health endpoint, latency (operational critical)
- autonomy: MCP tools, A2A protocol support
- capability: on-chain presence, tool count
- economics: x402 payment capability
- reputation: historical rating, on-chain record

Propose ONE improved parameter set. Rules:
1. All 6 keys must be present
2. Values must sum to exactly 1.0
3. Each value must be between its bounds: trust[0.05-0.40], reliability[0.05-0.40], autonomy[0.05-0.35], capability[0.05-0.40], economics[0.03-0.30], reputation[0.03-0.30]
4. Make SMALL changes (temperature={self.config.mutation_temperature})
5. Response must be ONLY valid JSON, no explanation

JSON response:"""

        client = self._get_llm()
        if client is None:
            return self._random_mutation(best, iteration)

        try:
            t0 = time.time()
            response = client.messages.create(
                model=self.config.llm_model,
                max_tokens=150,
                messages=[{"role": "user", "content": prompt}],
            )
            elapsed = time.time() - t0
            text = response.content[0].text.strip()

            # Extract JSON
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]

            new_params = json.loads(text)

            # Validate and fix
            new_params = {k: float(v) for k, v in new_params.items()}
            new_params = clip_to_bounds(new_params)
            valid, _ = validate_tracer_weights(new_params)
            if not valid:
                new_params = normalize_to_simplex(new_params)

            # Estimate cost (Haiku: ~$0.25/M input tokens, ~$1.25/M output)
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            cost = (input_tokens * 0.00000025) + (output_tokens * 0.00000125)
            self._cost_accumulated += cost

            return Candidate(
                params=new_params,
                iteration=iteration,
                generation_method="llm",
                cost_usd=cost,
            )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"[EvolveEngine] LLM mutation failed: {e} — falling back to random")
            return self._random_mutation(best, iteration)
        except Exception as e:
            logger.warning(f"[EvolveEngine] LLM call error: {e} — falling back to random")
            return self._random_mutation(best, iteration)


# ─── Program Database (MAP-Elites lite) ───────────────────────────────────────

class ProgramDatabase:
    """Stores all evaluated candidates with their scores."""

    def __init__(self, logs_dir: Path = LOGS_DIR):
        self.logs_dir = logs_dir
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self._candidates: list[Candidate] = []

    def add(self, candidate: Candidate):
        self._candidates.append(candidate)

    def top(self, n: int = 5) -> list[Candidate]:
        return sorted(self._candidates, key=lambda c: c.score, reverse=True)[:n]

    def best(self) -> Optional[Candidate]:
        if not self._candidates:
            return None
        return max(self._candidates, key=lambda c: c.score)

    def save_run(self, run_id: str, config: EvolveConfig):
        """Persist all candidates to JSONL."""
        run_file = self.logs_dir / "runs.jsonl"
        with open(run_file, "a") as f:
            for c in self._candidates:
                record = {"run_id": run_id, "target": config.target, **c.to_dict()}
                f.write(json.dumps(record) + "\n")

    def save_adopted(self, result: "EvolveResult"):
        """Save the adopted parameters to adopted.json (loaded at runtime by sentinel_lite)."""
        adopted_file = self.logs_dir / "adopted.json"
        data = {
            "target": result.target,
            "params": result.best_params,
            "score": result.best_score,
            "baseline_score": result.baseline_score,
            "score_delta": result.improvement_pct,
            "run_id": result.run_id,
            "adopted_at": datetime.utcnow().isoformat(),
            "candidates_evaluated": result.candidates_evaluated,
        }
        adopted_file.write_text(json.dumps(data, indent=2))
        logger.info(f"[EvolveEngine] Adopted params saved → {adopted_file}")


# ─── Main Controller ──────────────────────────────────────────────────────────

class EvolveController:
    """
    Orchestrates the full evolution loop.

    EvolveController → CandidateGenerator → DOFEvaluator → Z3Gate → ProgramDatabase

    Example:
        config = EvolveConfig(target="tracer_weights", max_iterations=40)
        evaluator = build_tracer_evaluator()
        engine = EvolveController(config, evaluator)
        result = engine.run()
        print(result.summary)
    """

    def __init__(
        self,
        config: EvolveConfig,
        evaluator: Callable[[dict], float],
        initial_params: Optional[dict] = None,
    ):
        self.config = config
        self.evaluator = evaluator
        self.initial_params = initial_params or dict(DEFAULT_TRACER_WEIGHTS)
        self._generator = CandidateGenerator(config)
        self._db = ProgramDatabase()
        random.seed(config.random_seed)

    def run(self) -> EvolveResult:
        """Execute the full evolution loop. Returns the best result found."""
        import uuid
        run_id = str(uuid.uuid4())[:8]
        t_start = time.time()

        if self.config.verbose:
            logger.info(f"[EvolveEngine] Starting run {run_id} | target={self.config.target} | "
                        f"iterations={self.config.max_iterations}")

        # Evaluate baseline
        baseline_score = self.evaluator(self.initial_params)
        baseline = Candidate(
            params=self.initial_params,
            score=baseline_score,
            iteration=0,
            generation_method="baseline",
        )
        self._db.add(baseline)
        best = baseline

        if self.config.verbose:
            logger.info(f"[EvolveEngine] Baseline score: {baseline_score:.4f}")

        total_cost = 0.0

        for i in range(1, self.config.max_iterations + 1):
            # Budget check — only applies to LLM cost, random mutations are always free
            if self.config.budget_usd > 0 and total_cost >= self.config.budget_usd:
                logger.info(f"[EvolveEngine] LLM budget exhausted at iteration {i}")
                break

            # Generate candidate
            candidate = self._generator.generate(
                current_best=best,
                history=self._db.top(10),
                iteration=i,
            )

            # Validate invariants before evaluating
            valid, reason = validate_tracer_weights(candidate.params)
            if not valid:
                if self.config.verbose:
                    logger.debug(f"[EvolveEngine] Iter {i}: invalid candidate ({reason}), skipping")
                continue

            # Evaluate
            score = self.evaluator(candidate.params)
            candidate.score = score
            total_cost += candidate.cost_usd
            self._db.add(candidate)

            # Update best
            if score > best.score:
                improvement = (score - best.score) / max(best.score, 1e-9) * 100
                best = candidate
                if self.config.verbose:
                    logger.info(
                        f"[EvolveEngine] Iter {i}: NEW BEST {score:.4f} "
                        f"(+{improvement:.2f}%) via {candidate.generation_method}"
                    )

        # Build result
        improvement_pct = (
            (best.score - baseline_score) / max(baseline_score, 1e-9) * 100
        )
        adopted = improvement_pct >= self.config.min_improvement_pct

        result = EvolveResult(
            target=self.config.target,
            best_params=best.params,
            best_score=best.score,
            baseline_score=baseline_score,
            improvement_pct=improvement_pct,
            total_iterations=len(self._db._candidates) - 1,
            total_cost_usd=total_cost,
            adopted=adopted,
            run_duration_s=time.time() - t_start,
            run_id=run_id,
            candidates_evaluated=len(self._db._candidates),
        )

        # Persist
        self._db.save_run(run_id, self.config)
        if adopted:
            self._db.save_adopted(result)

        # On-chain attestation of weight evolution
        if adopted:
            self._attest_evolution_onchain(result)

        if self.config.verbose:
            logger.info(f"[EvolveEngine] {result.summary}")

        return result

    def _attest_evolution_onchain(self, result: "EvolveResult") -> dict:
        """
        Write immutable on-chain record when TRACER weights evolve.

        Attestation payload: legacy SHA3-256/FIPS digest of {run_id, target,
        old_weights, new_weights, score_delta, corpus_size, timestamp}.

        This legacy digest is not equivalent to Solidity/EVM keccak256.

        Uses dry_run mode if DOF_PRIVATE_KEY not set — logs but doesn't tx.
        """
        import hashlib
        import json as _json

        # Build attestation payload
        payload = {
            "run_id": result.run_id,
            "target": result.target,
            "baseline_score": round(result.baseline_score, 6),
            "new_score": round(result.best_score, 6),
            "score_delta_pct": round(result.improvement_pct, 4),
            "new_weights": result.best_params,
            "candidates_evaluated": result.candidates_evaluated,
            "timestamp": datetime.utcnow().isoformat(),
            "event": "WEIGHTS_EVOLVED"
        }

        # Legacy SHA3-256/FIPS digest. This is not equivalent to EVM keccak256.
        payload_bytes = _json.dumps(payload, sort_keys=True).encode()
        proof_hash = "0x" + hashlib.sha3_256(payload_bytes).hexdigest()

        # Try on-chain attestation
        dry_run = not bool(os.environ.get("DOF_PRIVATE_KEY"))

        try:
            from core.chain_adapter import DOFChainAdapter
            adapter = DOFChainAdapter.from_chain_name("avalanche", dry_run=dry_run)

            metadata = _json.dumps({
                "type": "evolve_attestation",
                "run_id": result.run_id,
                "improvement_pct": round(result.improvement_pct, 4)
            })

            attest_result = adapter.publish_attestation(
                proof_hash=proof_hash,
                agent_id=0,  # 0 = system-level attestation (not agent-specific)
                metadata=metadata
            )

            # Save attestation record locally
            attest_log = LOGS_DIR / "evolution_attestations.jsonl"
            with open(attest_log, "a") as f:
                record = {**payload, "proof_hash": proof_hash, "chain_result": attest_result}
                f.write(_json.dumps(record) + "\n")

            logger.info(
                f"[EvolveEngine] Evolution attested on-chain: {proof_hash[:16]}... "
                f"({'dry_run' if dry_run else 'LIVE tx: ' + str(attest_result.get('tx_hash', '?'))[:16]})"
            )
            return attest_result

        except Exception as e:
            logger.warning(f"[EvolveEngine] On-chain attestation failed (non-fatal): {e}")
            return {"status": "error", "error": str(e), "proof_hash": proof_hash}


# ─── Convenience function ─────────────────────────────────────────────────────

def evolve_tracer_weights(
    validations_log: str = "logs/sentinel/validations.jsonl",
    max_iterations: int = 40,
    budget_usd: float = 0.50,
    verbose: bool = True,
) -> EvolveResult:
    """
    One-call interface to optimize TRACER weights.

    Example:
        from core.evolve_engine import evolve_tracer_weights
        result = evolve_tracer_weights()
        if result.adopted:
            print("New weights adopted:", result.best_params)
    """
    logging.basicConfig(level=logging.INFO if verbose else logging.WARNING)
    config = EvolveConfig(
        target="tracer_weights",
        max_iterations=max_iterations,
        budget_usd=budget_usd,
        verbose=verbose,
    )
    evaluator = build_tracer_evaluator(validations_log)
    engine = EvolveController(config, evaluator)
    return engine.run()
