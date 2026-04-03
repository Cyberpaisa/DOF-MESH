"""
DOF-EvolveEngine — Multi-source data loader y evaluador enriquecido.

Carga y normaliza datos de 4 fuentes:
  1. adversarial.jsonl      — 4,902 registros (verdict PASS/FAIL, acr, score)
  2. security_hierarchy.jsonl — 7,046 registros (capas L0-L4 con scores + passed bool)
  3. enigma_bridge.jsonl    — 6,441 registros (overall_score, proxy_score, etc.)
  4. sentinel/validations.jsonl — 5 registros reales con TRACER dimensions

Ponderación del evaluador combinado:
  adversarial: 40%  |  enigma: 35%  |  sentinel: 25%

No modifica evolve_engine.py ni sentinel_lite.py.
"""

import json
import math
import logging
from pathlib import Path
from typing import Callable

logger = logging.getLogger("dof.evolve_data")

# ─── Rutas ────────────────────────────────────────────────────────────────────

BASE_DIR = Path("/Users/jquiceva")

ADVERSARIAL_LOG    = BASE_DIR / "equipo-de-agentes/logs/adversarial.jsonl"
SEC_HIERARCHY_LOG  = BASE_DIR / "equipo-de-agentes/logs/security_hierarchy.jsonl"
ENIGMA_BRIDGE_LOG  = BASE_DIR / "equipo-de-agentes/logs/enigma_bridge.jsonl"
SENTINEL_LOG       = BASE_DIR / "equipo-de-agentes/logs/sentinel/validations.jsonl"

# Pesos del evaluador combinado
DATASET_WEIGHTS = {
    "adversarial": 0.40,
    "enigma":      0.35,
    "sentinel":    0.25,
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _load_jsonl(path: Path) -> list[dict]:
    """Carga un archivo JSONL línea por línea, ignorando errores de parseo."""
    records = []
    if not path.exists():
        logger.warning(f"[EvolveData] Archivo no encontrado: {path}")
        return records
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                logger.debug(f"[EvolveData] Error JSON línea {lineno} en {path.name}: {e}")
    return records


def _spearman_correlation(x: list, y: list) -> float:
    """Correlación de Spearman sin scipy."""
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


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


# ─── Loaders por fuente ───────────────────────────────────────────────────────

def _load_adversarial() -> list[dict]:
    """
    Carga adversarial.jsonl.
    Extrae: acr (0-1), score (0-1), outcome (PASS→1.0, FAIL→0.0).
    Mapeo a TRACER dimensions:
      acr   → trust (calidad adversarial de identidad/confianza)
      score → capability (score general de capacidad)
    """
    raw = _load_jsonl(ADVERSARIAL_LOG)
    records = []
    for r in raw:
        try:
            verdict = r.get("verdict", "").upper()
            acr     = float(r.get("acr", 0.0))
            score   = float(r.get("score", 0.0))
            outcome = 1.0 if verdict == "PASS" else 0.0

            records.append({
                "_source": "adversarial",
                "tracer_dims": {
                    "trust":       _clamp(acr),
                    "reliability": _clamp(acr),          # acr indica confiabilidad del resultado
                    "autonomy":    _clamp(score * 0.8),  # proxy conservador
                    "capability":  _clamp(score),
                    "economics":   _clamp(score * 0.5),  # no hay dato directo
                    "reputation":  _clamp(acr * score),  # producto como reputación compuesta
                },
                "outcome": outcome,
            })
        except (TypeError, ValueError):
            continue
    return records


def _load_security_hierarchy() -> list[dict]:
    """
    Carga security_hierarchy.jsonl.
    Cada registro tiene layers L0-L4 con score (0-1) y passed (bool).
    Mapeo de capas a TRACER dimensions:
      L0 → trust        (capa base de identidad/autenticación)
      L1 → reliability  (validación de conectividad)
      L2 → autonomy     (capacidad de operación autónoma)
      L3 → capability   (score de capacidad operativa)
      L4 → reputation   (capa más exigente — reputación/compliance)
      passed → outcome (1.0 / 0.0)
    """
    raw = _load_jsonl(SEC_HIERARCHY_LOG)
    records = []
    for r in raw:
        try:
            passed  = bool(r.get("passed", False))
            outcome = 1.0 if passed else 0.0
            layers  = {lay["layer"]: lay for lay in r.get("layers", []) if "layer" in lay}

            def layer_score(name: str, default: float = 0.5) -> float:
                lay = layers.get(name, {})
                return _clamp(float(lay.get("score", default)))

            records.append({
                "_source": "security_hierarchy",
                "tracer_dims": {
                    "trust":       layer_score("L0"),
                    "reliability": layer_score("L1"),
                    "autonomy":    layer_score("L2"),
                    "capability":  layer_score("L3"),
                    "economics":   (layer_score("L3") + layer_score("L4")) / 2.0,
                    "reputation":  layer_score("L4"),
                },
                "outcome": outcome,
            })
        except (TypeError, ValueError, AttributeError):
            continue
    return records


def _load_enigma_bridge() -> list[dict]:
    """
    Carga enigma_bridge.jsonl.
    Scores ya en 0-1.
    Mapeo explícito según spec:
      proxy_score     → trust
      uptime_score    → reliability
      oz_match_score  → capability
      community_score → reputation
      overall_score   → outcome
    autonomy y economics se derivan de combinaciones.
    """
    raw = _load_jsonl(ENIGMA_BRIDGE_LOG)
    records = []
    for r in raw:
        try:
            proxy_score     = _clamp(float(r.get("proxy_score",     0.0)))
            uptime_score    = _clamp(float(r.get("uptime_score",    0.0)))
            oz_match_score  = _clamp(float(r.get("oz_match_score",  0.0)))
            community_score = _clamp(float(r.get("community_score", 0.0)))
            overall_score   = _clamp(float(r.get("overall_score",   0.0)))

            # autonomy: promedio de proxy (identidad independiente) + oz_match (estándar)
            autonomy = _clamp((proxy_score + oz_match_score) / 2.0)
            # economics: uptime como proxy de disponibilidad de servicio económico
            economics = _clamp((uptime_score + community_score) / 2.0)

            records.append({
                "_source": "enigma_bridge",
                "tracer_dims": {
                    "trust":       proxy_score,
                    "reliability": uptime_score,
                    "autonomy":    autonomy,
                    "capability":  oz_match_score,
                    "economics":   economics,
                    "reputation":  community_score,
                },
                "outcome": overall_score,
            })
        except (TypeError, ValueError):
            continue
    return records


def _load_sentinel() -> list[dict]:
    """
    Carga sentinel/validations.jsonl.
    Scores en 0-100 → normaliza a 0-1.
    result: PASS→1.0, PARTIAL→0.5, FAIL→0.0.
    """
    outcome_map = {"PASS": 1.0, "PARTIAL": 0.5, "FAIL": 0.0}
    raw = _load_jsonl(SENTINEL_LOG)
    records = []
    for r in raw:
        try:
            result = r.get("result", "").upper()
            outcome = outcome_map.get(result, 0.5)
            tracer = r.get("tracer", {})
            dims = tracer.get("dimensions", {})

            if not dims:
                continue

            # Sentinel usa scores 0-100 → normalizar a 0-1
            def norm(key: str) -> float:
                val = float(dims.get(key, 0.0))
                return _clamp(val / 100.0)

            records.append({
                "_source": "sentinel",
                "tracer_dims": {
                    "trust":       norm("trust"),
                    "reliability": norm("reliability"),
                    "autonomy":    norm("autonomy"),
                    "capability":  norm("capability"),
                    "economics":   norm("economics"),
                    "reputation":  norm("reputation"),
                },
                "outcome": outcome,
            })
        except (TypeError, ValueError, AttributeError):
            continue
    return records


# ─── API pública ──────────────────────────────────────────────────────────────

def load_all_sources() -> dict[str, list[dict]]:
    """
    Carga y normaliza todos los datasets.

    Retorna un dict con claves:
      "adversarial"        → list[dict]
      "security_hierarchy" → list[dict]
      "enigma"             → list[dict]
      "sentinel"           → list[dict]

    Cada elemento tiene:
      "_source"     : str
      "tracer_dims" : dict con 6 dimensiones en 0-1
      "outcome"     : float en 0-1
    """
    sources = {
        "adversarial":        _load_adversarial(),
        "security_hierarchy": _load_security_hierarchy(),
        "enigma":             _load_enigma_bridge(),
        "sentinel":           _load_sentinel(),
    }

    for name, records in sources.items():
        logger.info(f"[EvolveData] {name}: {len(records)} registros cargados")

    return sources


def build_rich_evaluator() -> Callable[[dict], float]:
    """
    Construye un evaluador multi-fuente que usa TODOS los datasets.

    Estrategia:
      - Calcula correlación Spearman por dataset entre
        score_ponderado(weights, dims) y outcome
      - Combina correlaciones con pesos: adversarial 40%, enigma 35%, sentinel 25%
      - security_hierarchy se usa internamente como fuente adicional del evaluador
        pero no tiene peso explícito en el promedio final (se mezcla en enigma)
      - Añade regularización DOF: trust+reliability+capability > 50%
      - Escala a [0, 1]

    Retorna:
      callable: weights_dict → float (0-1, mayor es mejor)
    """
    sources = load_all_sources()

    adv_records  = sources["adversarial"]
    sec_records  = sources["security_hierarchy"]
    enigma_recs  = sources["enigma"]
    sentinel_recs = sources["sentinel"]

    total_adv     = len(adv_records)
    total_sec     = len(sec_records)
    total_enigma  = len(enigma_recs)
    total_sent    = len(sentinel_recs)

    print(f"\n[EvolveData] Registros cargados:")
    print(f"  adversarial:        {total_adv:,}")
    print(f"  security_hierarchy: {total_sec:,}")
    print(f"  enigma_bridge:      {total_enigma:,}")
    print(f"  sentinel:           {total_sent}")
    print(f"  TOTAL:              {total_adv + total_sec + total_enigma + total_sent:,}\n")

    def _score_dataset(records: list[dict], weights: dict) -> float:
        """Correlación Spearman para un dataset dado los weights."""
        if not records:
            return 0.5  # neutral si no hay datos

        predicted = []
        actual    = []
        for r in records:
            dims = r["tracer_dims"]
            w_score = sum(
                weights.get(dim, 0.0) * dims.get(dim, 0.0)
                for dim in weights
            )
            predicted.append(w_score)
            actual.append(r["outcome"])

        corr = _spearman_correlation(predicted, actual)
        # Mapear de [-1,1] a [0,1]
        return (corr + 1.0) / 2.0

    def evaluate(weights: dict) -> float:
        # ── Correlaciones por fuente ──────────────────────────────────────────
        corr_adv     = _score_dataset(adv_records,   weights)
        corr_sec     = _score_dataset(sec_records,   weights)
        corr_enigma  = _score_dataset(enigma_recs,   weights)
        corr_sent    = _score_dataset(sentinel_recs, weights)

        # security_hierarchy refuerza enigma (misma familia de datos de capas)
        corr_enigma_combined = 0.7 * corr_enigma + 0.3 * corr_sec

        # ── Promedio ponderado según spec ─────────────────────────────────────
        combined = (
            DATASET_WEIGHTS["adversarial"] * corr_adv +
            DATASET_WEIGHTS["enigma"]      * corr_enigma_combined +
            DATASET_WEIGHTS["sentinel"]    * corr_sent
        )

        # ── Regularización DOF: trust + reliability + capability ≥ 50% ───────
        governance_core = (
            weights.get("trust", 0.0) +
            weights.get("reliability", 0.0) +
            weights.get("capability", 0.0)
        )
        prior_penalty = max(0.0, 0.50 - governance_core) * 0.5

        score = combined - prior_penalty
        return _clamp(score)

    return evaluate
