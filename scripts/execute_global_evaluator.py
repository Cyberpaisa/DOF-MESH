#!/usr/bin/env python3
"""
execute_global_evaluator.py - Evaluación global de la malla DOF.
Diseñado para humanos y agentes (Agent-First CLI).

Principios Agénticos:
- Structured discoverability (subcomandos)
- Agent-first interoperability (--json, NO_COLOR)
- Configuration XDG (~/.config/dof-mesh/config.yaml)
- Error guidance (Hints y exit codes 0/1/2/3)
"""

import argparse
import sys
import os
import json
import yaml
import time
import requests
import hashlib
import hmac
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Any, Dict, List

# ============================================================
# Configuración XDG y Entornos
# ============================================================
def get_config_path() -> Path:
    xdg_config = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    return Path(xdg_config) / "dof-mesh" / "config.yaml"

def load_config() -> Dict[str, Any]:
    config_file = get_config_path()
    if not config_file.exists():
        return {
            "default_env": "adaline",
            "envs": {
                "local": {
                    "provider": "ollama",
                    "base_url": "http://host.docker.internal:11434/v1",
                    "model": "llama3.2",
                    "key_env_var": None
                },
                "adaline": {
                    "provider": "adaline",
                    "base_url": "https://api.adaline.ai/v2/deployments/execute",
                    "prompt_id": "6f446617-df79-46f8-8c6a-86238629b800",
                    "env_id": "db8cb3bd-fec8-4146-9bfc-fc6dd10b5470",
                    "key_env_var": "SOCIETY_AI_API_KEY"
                }
            }
        }
    with open(config_file) as f:
        return yaml.safe_load(f)

def save_config(config: Dict[str, Any]):
    config_file = get_config_path()
    config_file.parent.mkdir(parents=True, exist_ok=True)
    with open(config_file, "w") as f:
        yaml.dump(config, f)

# ============================================================
# Detección de modo interactivo / colores
# ============================================================
def is_interactive() -> bool:
    """Determina si debemos usar TUI/colores."""
    if os.environ.get("NO_COLOR") or os.environ.get("DOF_NO_TUI"):
        return False
    if not sys.stdout.isatty():
        return False
    return True

class Colors:
    ACCENT = "\033[1;36m"   # cyan
    COMMAND = "\033[1;33m"  # yellow
    PASS = "\033[1;32m"     # green
    WARN = "\033[1;33m"     # yellow
    FAIL = "\033[1;31m"     # red
    MUTED = "\033[2;37m"    # dim
    ID = "\033[1;34m"       # blue
    RESET = "\033[0m"

def colorize(text: str, color_code: str) -> str:
    if is_interactive():
        return f"{color_code}{text}{Colors.RESET}"
    return text

# Funciones de log
def log(msg: str, json_output: bool) -> None:
    if not json_output and is_interactive():
        print(msg, flush=True)

def emit(event_type: str, data: dict, json_output: bool) -> None:
    if json_output:
        print(json.dumps({"event": event_type, **data}, ensure_ascii=False), flush=True)

def log_hint(hint: str, json_output: bool) -> None:
    if json_output:
        emit("hint", {"message": hint}, True)
    else:
        print(colorize(f"  Hint: {hint}", Colors.WARN), file=sys.stderr, flush=True)

# ============================================================
# Escenarios Globales (Los 9 Escenarios Originales)
# ============================================================
SCENARIOS: list[dict] = [
    {
        "id": 1,
        "name": "Supervivencia Profesional Amodei",
        "description": "Evaluación brutal sobre el impacto de la IA en la carrera.",
        "prompt": "Eres un analista senior de transformación laboral que ha estudiado a fondo el ensayo de Dario Amodei 'Machines of Loving Grace'... Evalúa la supervivencia de un founder construyendo agentes."
    },
    {
        "id": 2,
        "name": "Razonamiento Constitucional",
        "description": "Análisis de la contradicción entre ejecución estocástica y gobernanza determinística.",
        "prompt": "Eres un sistema de IA operando bajo IA Constitucional. Analiza: ¿el determinismo de Z3 choca con la estocástica del LLM en DOF-MESH?"
    },
    {
        "id": 3,
        "name": "Transformación Industrial",
        "description": "Mapeo estratégico del ecosistema DOF-MESH en la industria de agentes.",
        "prompt": "Mapea el estado actual de la IA (1-10 años) y el rol de productos como 8004scan.io y Sovereign Funding."
    },
    {
        "id": 4,
        "name": "Protocolo de Pensamiento Profundo",
        "description": "Escalamiento de DOF de 2 a 10+ cadenas manteniendo gobernanza determinística.",
        "prompt": "Usa Protocolo de Pensamiento Profundo para escalar DOF-MESH de Avalanche+Base a 10+ chains con Z3."
    },
    {
        "id": 5,
        "name": "Framework de Decisiones HHH",
        "description": "Evaluación radical del futuro del proyecto (Startup vs Indie vs Empleo).",
        "prompt": "Usa Anthropic HHH para decidir mi camino: (A) Startup DOF (B) Indie builder (C) Empleo nivel Anthropic/Coinbase."
    },
    {
        "id": 6,
        "name": "Buscador de Oportunidades 100 Años",
        "description": "Identificación de blue oceans en la infraestructura de agentes.",
        "prompt": "Busca Oportunidades Blue Ocean para DOF-MESH. Trust Score, Agent Middlewares."
    },
    {
        "id": 7,
        "name": "Máquina de Debate Steelman",
        "description": "Defensa de la gobernanza determinística frente al conexionismo probabilístico.",
        "prompt": "Steelman argument: ataca brutalmente la gobernanza determinística Z3 vs RLHF."
    },
    {
        "id": 8,
        "name": "Análisis de Grado Investigativo",
        "description": "Viabilidad técnica de un Trust Score Universal cross-chain.",
        "prompt": "Análisis investigativo: ¿es viable un Trust Score universal como el de TRACER cross-chain?"
    },
    {
        "id": 9,
        "name": "Estrategia a Largo Plazo",
        "description": "Construir el 'SSL/TLS de la era agéntica' (Horizonte 10 años).",
        "prompt": "Estrategia a 10 años: Convirtiendo a DOF-MESH en el SSL/TLS de la era agéntica."
    }
]

# ============================================================
# Motores de Inferencia
# ============================================================
def _get_api_key(key_var: str) -> str | None:
    if not key_var:
        return None
    try:
        with open(".env", "r") as f:
            for line in f:
                if line.startswith(f"{key_var}="):
                    val = line.split("=", 1)[1].strip()
                    return val if val else None
    except FileNotFoundError:
        pass
    return os.getenv(key_var)


def _sign_headers(payload: str = "") -> dict:
    qa_key = os.getenv("QAION_PRIVATE_KEY", "dof-local-dev-key")
    signature = hmac.new(qa_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return {"X-DOF-Signature": signature}

def _call_adaline(cfg: dict, scenario: dict) -> tuple[dict, float]:
    api_key = _get_api_key(cfg.get("key_env_var"))
    if not api_key:
        raise PermissionError(f"{cfg.get('key_env_var')} ausente")
    url = f"{cfg['base_url'].replace('/execute', '')}/execute?promptId={cfg['prompt_id']}&deploymentEnvironmentId={cfg['env_id']}&deploymentId=latest"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", **_sign_headers()}
    payload = {"inputs": {"user_query": scenario["prompt"]}}
    t0 = time.time()
    res = requests.post(url, headers=headers, json=payload, timeout=120)
    latency = time.time() - t0
    res.raise_for_status()
    return res.json(), latency

def _call_ollama(cfg: dict, scenario: dict) -> tuple[dict, float]:
    url = f"{cfg['base_url']}/chat/completions"
    headers = {"Content-Type": "application/json", **_sign_headers()}
    payload = {"model": cfg["model"], "messages": [{"role": "user", "content": scenario["prompt"]}], "stream": False}
    t0 = time.time()
    res = requests.post(url, headers=headers, json=payload, timeout=180)
    latency = time.time() - t0
    res.raise_for_status()
    return res.json(), latency

# ============================================================
# Argumentos y Subcomandos
# ============================================================
def parse_args():
    parser = argparse.ArgumentParser(
        description="Ejecuta una evaluación global sobre la malla DOF.",
        epilog="""
Categorías de comandos (para agentes):
  Task Management:
    run       Ejecuta una evaluación (start here)
    status    Obtiene el estado de una evaluación
  Information:
    list      Lista evaluaciones previas
  Configuration:
    env       Muestra o cambia el entorno activo
        """
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="Comando a ejecutar")

    # Comando 'run'
    run_parser = subparsers.add_parser("run", help="Ejecuta una evaluación")
    run_parser.add_argument("--task-id", help="ID de tarea (opcional, se genera uno si no se da)")
    run_parser.add_argument("--scenario", type=int, help="Ejecutar solo el escenario con este ID (1-9)")
    run_parser.add_argument("--full", action="store_true", help="Muestra salida completa (sin truncar)")
    run_parser.add_argument("--json", action="store_true", help="Salida en formato JSON/NDJSON")
    run_parser.add_argument("--env", default=None, help="Entorno de configuración (local/adaline)")

    # Comando 'status'
    status_parser = subparsers.add_parser("status", help="Obtiene estado de evaluación")
    status_parser.add_argument("task_id", help="ID de tarea")
    status_parser.add_argument("--json", action="store_true")

    # Comando 'list'
    list_parser = subparsers.add_parser("list", help="Lista evaluaciones previas")
    list_parser.add_argument("--json", action="store_true")

    # Comando 'env'
    env_parser = subparsers.add_parser("env", help="Configuración de entorno")
    env_parser.add_argument("--set", help="Establece entorno activo (local, adaline)")
    env_parser.add_argument("--json", action="store_true")

    return parser.parse_args()

# ============================================================
# Funciones de Negocio
# ============================================================
def run_evaluation(task_id: Optional[str], scenario_filter: int, full: bool, json_output: bool, env_name: str):
    config = load_config()
    env_cfg = config["envs"].get(env_name, config["envs"].get(config["default_env"]))
    if not env_cfg:
        raise Exception(f"Entorno {env_name} no existe en configuración.")
    
    scenarios = SCENARIOS
    if scenario_filter:
        scenarios = [s for s in SCENARIOS if s["id"] == scenario_filter]
        if not scenarios:
            print(f"Error: Escenario {scenario_filter} no existe.", file=sys.stderr)
            sys.exit(2)

    task_id_actual = task_id or f"eval-{int(time.time())}"
    log(colorize(f"[{task_id_actual}] Iniciando evaluación en '{env_name}' ({env_cfg['provider']})...", Colors.ACCENT), json_output)

    has_errors = False
    for scenario in scenarios:
        log(f"→ Evaluando: {scenario['name']}", json_output)
        try:
            if env_cfg["provider"] == "adaline":
                data, latency = _call_adaline(env_cfg, scenario)
            else:
                data, latency = _call_ollama(env_cfg, scenario)

            # Truncamiento
            response_text = str(data)
            if not full and not json_output and len(response_text) > 300:
                response_text = response_text[:300] + "... [truncado, usa --full para ver todo]"

            if json_output:
                emit("evaluation_result", {
                    "task_id": task_id_actual,
                    "scenario_id": scenario["id"],
                    "status": "completed",
                    "latency": round(latency, 3),
                    "response": data if full else response_text
                }, True)
            else:
                print(colorize("Éxito", Colors.PASS) + f" ({latency:.2f}s) - {response_text[:100]}")

        except Exception as e:
            has_errors = True
            log(colorize(f"Fallo en escenario {scenario['id']}: {e}", Colors.FAIL), json_output)
            if json_output:
                emit("evaluation_error", {"scenario_id": scenario["id"], "error": str(e)}, True)

    if has_errors:
        sys.exit(1)

def handle_env(set_env: Optional[str], json_output: bool):
    config = load_config()
    if set_env:
        if set_env not in config["envs"]:
            print(f"Error: Entorno '{set_env}' desconocido. Disponibles: {list(config['envs'].keys())}", file=sys.stderr)
            sys.exit(2)
        config["default_env"] = set_env
        save_config(config)
        if not json_output:
            print(colorize(f"Entorno cambiado a {set_env}", Colors.PASS))
    else:
        current = config["default_env"]
        if json_output:
            emit("config", {"default_env": current, "available": list(config["envs"].keys())}, True)
        else:
            print(colorize("Entorno actual: ", Colors.ACCENT) + current)
            print("Entornos disponibles: " + ", ".join(config["envs"].keys()))

# ============================================================
# Entrypoint determinista
# ============================================================
def main():
    args = parse_args()
    config = load_config()
    env_name = args.env if hasattr(args, 'env') and args.env else config["default_env"]

    try:
        if args.command == "run":
            run_evaluation(args.task_id, args.scenario, args.full, args.json, env_name)
        elif args.command == "status":
            print("Status endpoint (mock)")
        elif args.command == "list":
            print("List endpoint (mock)")
        elif args.command == "env":
            handle_env(args.set, args.json)
    except ConnectionError as e:
        print(colorize(f"Error de conexión: {e}", Colors.FAIL), file=sys.stderr)
        log_hint("Verifica que el servicio backend (ej. Ollama 11434) esté corriendo y que la URL sea correcta.", getattr(args, "json", False))
        sys.exit(3)
    except Exception as e:
        print(colorize(f"Error general: {e}", Colors.FAIL), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
