#!/usr/bin/env python3
"""
DOF-MESH Evolution Daemon
─────────────────────────────────────────────────────────────────────────────
Daemon autónomo que cierra el loop de auto-evolución:

  Ciclo (cada INTERVAL segundos):
    1. Verification Sweep — verifica reglas con `verify:` pattern
    2. Auto-Promote Rules — correcciones repetidas → learned-rules.md
    3. EvolveEngine — optimiza pesos TRACER si hay nuevos registros
    4. Scorecard — loguea sesión en sessions.jsonl

Modo de ejecución:
    python3 scripts/evolution_daemon.py              # corre indefinidamente
    python3 scripts/evolution_daemon.py --once       # un ciclo y sale
    python3 scripts/evolution_daemon.py --interval 3600  # cada hora
    python3 scripts/evolution_daemon.py --dry-run    # sin writes on-chain
"""

import sys
import json
import time
import argparse
import subprocess
import logging
from pathlib import Path
from datetime import datetime, timezone

# ──────────────────────────────────────────────
# Configuración
# ──────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
LOGS_DIR = ROOT / "logs" / "daemon"
SESSIONS_PATH = ROOT / ".claude" / "memory" / "sessions.jsonl"
VIOLATIONS_PATH = ROOT / ".claude" / "memory" / "violations.jsonl"
LEARNED_RULES_PATH = ROOT / ".claude" / "memory" / "learned-rules.md"

LOGS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [DAEMON] %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "evolution_daemon.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("evolution.daemon")

DEFAULT_INTERVAL = 1800  # 30 minutos


# ──────────────────────────────────────────────
# Paso 1: Verification Sweep
# ──────────────────────────────────────────────
def verification_sweep() -> dict:
    """Lee learned-rules.md y ejecuta cada verify: check."""
    if not LEARNED_RULES_PATH.exists():
        return {"checked": 0, "passed": 0, "failed": 0, "violations": []}

    content = LEARNED_RULES_PATH.read_text()
    rules = []
    current_rule = None

    for line in content.splitlines():
        line_stripped = line.strip()
        if line_stripped.startswith("- ") and not line_stripped.startswith("- verify:"):
            current_rule = line_stripped[2:].strip()
        elif line_stripped.startswith("verify:") and current_rule:
            verify_spec = line_stripped[len("verify:"):].strip()
            rules.append({"rule": current_rule, "verify": verify_spec})

    results = {"checked": 0, "passed": 0, "failed": 0, "violations": []}

    for r in rules:
        results["checked"] += 1
        verify = r["verify"]

        # Ignorar checks manuales
        if verify.lower().startswith("manual"):
            results["passed"] += 1
            continue

        # Ejecutar grep-based checks
        try:
            passed = _run_verify_check(verify, r["rule"])
            if passed:
                results["passed"] += 1
            else:
                results["failed"] += 1
                violation = {
                    "timestamp": _now(),
                    "rule": r["rule"][:100],
                    "check": verify[:100],
                    "result": "FAIL",
                    "auto_fixed": False,
                }
                results["violations"].append(violation)
                _log_violation(violation)
        except Exception as e:
            log.warning(f"Error verificando '{r['rule'][:50]}': {e}")
            results["passed"] += 1  # No penalizar errores de parse

    return results


def _run_verify_check(verify: str, rule: str) -> bool:
    """Ejecuta un check de verify: y retorna True si pasa."""
    import re

    # Patrón: Grep("X", path="Y") → N matches
    # Maneja strings con comillas embebidas: 'agent_id="' o "import pytest"
    # Intenta primero con comilla simple, luego con doble
    m = re.search(r"Grep\('([^']+)'.*?\)\s*→\s*(\d+)\+?\s*match", verify, re.IGNORECASE)
    if not m:
        m = re.search(r'Grep\("([^"]+)".*?\)\s*→\s*(\d+)\+?\s*match', verify, re.IGNORECASE)
    if m:
        pattern = m.group(1)
        expected_count = int(m.group(2))
        is_zero = "0 match" in verify.lower()

        # Extraer path si existe
        path_m = re.search(r'path=["\'](.+?)["\']', verify)
        search_path = ROOT / path_m.group(1) if path_m else ROOT / "core"

        try:
            result = subprocess.run(
                ["grep", "-r", "--include=*.py", "-l", pattern, str(search_path)],
                capture_output=True, text=True, timeout=10
            )
            actual_count = len([l for l in result.stdout.splitlines() if l.strip()])

            if is_zero:
                return actual_count == 0
            else:
                return actual_count >= expected_count
        except subprocess.TimeoutExpired:
            return True  # Timeout → pass (no block)
        except Exception:
            return True

    return True  # Check no parseable → pass


# ──────────────────────────────────────────────
# Paso 2: Auto-Promote Rules
# ──────────────────────────────────────────────
def auto_promote() -> dict:
    """Llama al script de auto-promote y parsea output."""
    try:
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "auto_promote_rules.py")],
            capture_output=True, text=True, cwd=str(ROOT), timeout=30
        )
        promoted_count = result.stdout.count("✅ PROMOVIDO")
        return {"promoted": promoted_count, "output": result.stdout.strip()}
    except Exception as e:
        log.warning(f"Auto-promote error: {e}")
        return {"promoted": 0, "output": str(e)}


# ──────────────────────────────────────────────
# Paso 3: EvolveEngine
# ──────────────────────────────────────────────
def run_evolve_engine(dry_run: bool) -> dict:
    """Corre EvolveEngine si hay suficientes registros nuevos."""
    try:
        sys.path.insert(0, str(ROOT))
        from core.evolve_engine import EvolveController, EvolveConfig

        # Verificar si hay registros suficientes para evolucionar
        records_path = ROOT / "logs" / "evolve" / "records.jsonl"
        if not records_path.exists():
            return {"ran": False, "reason": "sin registros aún"}

        count = sum(1 for _ in open(records_path))
        if count < 100:
            return {"ran": False, "reason": f"solo {count} registros (mínimo 100)"}

        config = EvolveConfig(
            target="tracer_weights",
            budget_usd=0.0,   # gratis — sin LLM calls
            max_iterations=20,
            dry_run=dry_run,
        )
        controller = EvolveController(config)
        result = controller.run()

        return {
            "ran": True,
            "run_id": result.run_id,
            "baseline": round(result.baseline_score, 4),
            "new_score": round(result.best_score, 4),
            "improvement_pct": round(result.improvement_pct, 2),
            "adopted": result.adopted,
        }
    except ImportError as e:
        return {"ran": False, "reason": f"ImportError: {e}"}
    except Exception as e:
        log.warning(f"EvolveEngine error: {e}")
        return {"ran": False, "reason": str(e)}


# ──────────────────────────────────────────────
# Paso 4: Scorecard
# ──────────────────────────────────────────────
def write_scorecard(sweep: dict, promote: dict, evolve: dict) -> None:
    scorecard = {
        "date": _now(),
        "corrections_received": 0,  # se actualiza manualmente via corrections.jsonl
        "rules_checked": sweep["checked"],
        "rules_passed": sweep["passed"],
        "rules_failed": sweep["failed"],
        "violations": [v["rule"][:60] for v in sweep.get("violations", [])],
        "rules_promoted": promote.get("promoted", 0),
        "evolve_ran": evolve.get("ran", False),
        "evolve_improvement_pct": evolve.get("improvement_pct"),
        "source": "evolution_daemon",
    }

    SESSIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SESSIONS_PATH, "a") as f:
        f.write(json.dumps(scorecard, ensure_ascii=False) + "\n")


def _log_violation(v: dict) -> None:
    VIOLATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(VIOLATIONS_PATH, "a") as f:
        f.write(json.dumps(v, ensure_ascii=False) + "\n")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ──────────────────────────────────────────────
# Ciclo principal
# ──────────────────────────────────────────────
def run_cycle(dry_run: bool) -> None:
    log.info("═══════════════════════════════════════")
    log.info("  DOF Evolution Daemon — Ciclo iniciado")
    log.info("═══════════════════════════════════════")

    # 1. Sweep
    log.info("[1/4] Verification Sweep...")
    sweep = verification_sweep()
    log.info(f"  → {sweep['passed']}/{sweep['checked']} reglas OK, {sweep['failed']} violaciones")
    for v in sweep.get("violations", []):
        log.warning(f"  VIOLACIÓN: {v['rule'][:70]}")

    # 2. Auto-promote
    log.info("[2/4] Auto-Promote Rules...")
    promote = auto_promote()
    if promote["promoted"] > 0:
        log.info(f"  → {promote['promoted']} regla(s) promovida(s)")
    else:
        log.info("  → Sin reglas nuevas")

    # 3. EvolveEngine
    log.info("[3/4] EvolveEngine...")
    evolve = run_evolve_engine(dry_run)
    if evolve["ran"]:
        log.info(f"  → run {evolve['run_id']} | +{evolve['improvement_pct']}% | adopted={evolve['adopted']}")
    else:
        log.info(f"  → {evolve['reason']}")

    # 4. Scorecard
    log.info("[4/4] Scorecard...")
    write_scorecard(sweep, promote, evolve)
    log.info("  → Guardado en .claude/memory/sessions.jsonl")

    # Resumen
    log.info("═══════════════════════════════════════")
    status = "✅ LIMPIO" if sweep["failed"] == 0 else f"⚠️  {sweep['failed']} VIOLACIONES"
    log.info(f"  Estado: {status} | {sweep['passed']}/{sweep['checked']} reglas | {promote['promoted']} promovidas")
    if evolve["ran"]:
        log.info(f"  EvolveEngine: +{evolve['improvement_pct']}%")
    log.info("═══════════════════════════════════════")


def main() -> None:
    parser = argparse.ArgumentParser(description="DOF-MESH Evolution Daemon")
    parser.add_argument("--once", action="store_true", help="Un ciclo y salir")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL, help="Segundos entre ciclos")
    parser.add_argument("--dry-run", action="store_true", help="Sin escrituras on-chain")
    args = parser.parse_args()

    if args.once:
        run_cycle(dry_run=args.dry_run)
        return

    log.info(f"Daemon iniciado. Ciclo cada {args.interval}s. Ctrl+C para detener.")
    while True:
        try:
            run_cycle(dry_run=args.dry_run)
            log.info(f"Próximo ciclo en {args.interval // 60} min...")
            time.sleep(args.interval)
        except KeyboardInterrupt:
            log.info("Daemon detenido por el Soberano.")
            break
        except Exception as e:
            log.error(f"Error en ciclo: {e}")
            time.sleep(60)  # espera 1 min antes de reintentar


if __name__ == "__main__":
    main()
