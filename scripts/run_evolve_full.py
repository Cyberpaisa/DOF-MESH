"""
DOF-EvolveEngine — Full run con evaluador multi-fuente.

Usa build_rich_evaluator() de evolve_data.py que combina:
  - adversarial.jsonl      (40%)
  - enigma_bridge.jsonl    (35%, reforzado con security_hierarchy)
  - sentinel/validations.jsonl (25%)

budget_usd=0.0 → solo random mutations (sin LLM, sin costo).
max_iterations=60

Guarda resultados en: logs/evolve/full_run_20260329.json
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# ─── Path setup ──────────────────────────────────────────────────────────────
sys.path.insert(0, "/Users/jquiceva/DOF-MESH")

from core.evolve_engine import EvolveController, EvolveConfig
from core.evolve_data import build_rich_evaluator

# ─── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("dof.run_evolve_full")

# ─── Constantes ───────────────────────────────────────────────────────────────
OUTPUT_DIR  = Path("/Users/jquiceva/DOF-MESH/logs/evolve")
OUTPUT_FILE = OUTPUT_DIR / "full_run_20260329.json"


def main():
    print("=" * 65)
    print("  DOF-EvolveEngine — Full Multi-Source Run")
    print(f"  {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 65)

    # ── 1. Construir evaluador enriquecido ────────────────────────────────────
    print("\n[1/3] Construyendo evaluador multi-fuente...")
    evaluator = build_rich_evaluator()

    # ── 2. Configurar y lanzar EvolveController ───────────────────────────────
    print("[2/3] Iniciando EvolveController (60 iteraciones, sin LLM)...")
    config = EvolveConfig(
        target="tracer_weights",
        max_iterations=60,
        budget_usd=0.0,       # solo random mutations — sin costo LLM
        min_improvement_pct=0.5,
        mutation_temperature=0.25,
        random_seed=42,
        verbose=True,
    )

    engine = EvolveController(config, evaluator)
    result = engine.run()

    # ── 3. Mostrar resultados ─────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("  RESULTADOS")
    print("=" * 65)
    print(f"  Run ID          : {result.run_id}")
    print(f"  Target          : {result.target}")
    print(f"  Baseline score  : {result.baseline_score:.6f}")
    print(f"  Mejor score     : {result.best_score:.6f}")
    improvement = result.improvement_pct
    sign = "+" if improvement >= 0 else ""
    print(f"  Mejora          : {sign}{improvement:.4f}%")
    print(f"  Iteraciones     : {result.total_iterations}")
    print(f"  Candidatos eval : {result.candidates_evaluated}")
    print(f"  Costo LLM       : ${result.total_cost_usd:.6f}")
    print(f"  Duración        : {result.run_duration_s:.2f}s")
    print(f"  Adoptado        : {'SÍ ✅' if result.adopted else 'NO (mejora insuficiente)'}")

    print("\n  Weights óptimos encontrados:")
    for dim, val in sorted(result.best_params.items(), key=lambda x: -x[1]):
        bar = "█" * int(val * 30)
        print(f"    {dim:<12} {val:.6f}  {bar}")

    print("\n  Comparación baseline vs óptimo:")
    from core.evolve_engine import DEFAULT_TRACER_WEIGHTS
    print(f"    {'Dimensión':<12} {'Baseline':>10}  {'Óptimo':>10}  {'Delta':>10}")
    print(f"    {'-'*12}  {'-'*10}  {'-'*10}  {'-'*10}")
    for dim in DEFAULT_TRACER_WEIGHTS:
        base_val = DEFAULT_TRACER_WEIGHTS[dim]
        opt_val  = result.best_params.get(dim, base_val)
        delta    = opt_val - base_val
        sign_d   = "+" if delta >= 0 else ""
        print(f"    {dim:<12} {base_val:>10.6f}  {opt_val:>10.6f}  {sign_d}{delta:>9.6f}")

    print("=" * 65)

    # ── 4. Guardar resultados en JSON ─────────────────────────────────────────
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_data = {
        "run_id":               result.run_id,
        "run_timestamp":        datetime.utcnow().isoformat(),
        "target":               result.target,
        "baseline_score":       result.baseline_score,
        "best_score":           result.best_score,
        "improvement_pct":      result.improvement_pct,
        "total_iterations":     result.total_iterations,
        "candidates_evaluated": result.candidates_evaluated,
        "total_cost_usd":       result.total_cost_usd,
        "run_duration_s":       result.run_duration_s,
        "adopted":              result.adopted,
        "best_params":          result.best_params,
        "baseline_params":      DEFAULT_TRACER_WEIGHTS,
        "dataset_sources": {
            "adversarial":        str(Path("/Users/jquiceva/equipo-de-agentes/logs/adversarial.jsonl")),
            "security_hierarchy": str(Path("/Users/jquiceva/equipo-de-agentes/logs/security_hierarchy.jsonl")),
            "enigma_bridge":      str(Path("/Users/jquiceva/equipo-de-agentes/logs/enigma_bridge.jsonl")),
            "sentinel":           str(Path("/Users/jquiceva/DOF-MESH/logs/sentinel/validations.jsonl")),
        },
        "dataset_weights": {
            "adversarial": 0.40,
            "enigma":      0.35,
            "sentinel":    0.25,
        },
        "config": {
            "max_iterations":       config.max_iterations,
            "budget_usd":           config.budget_usd,
            "mutation_temperature": config.mutation_temperature,
            "random_seed":          config.random_seed,
            "population_size":      config.population_size,
        },
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\n[3/3] Resultados guardados en: {OUTPUT_FILE}")
    print()

    return result


if __name__ == "__main__":
    main()
