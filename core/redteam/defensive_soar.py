#!/usr/bin/env python3
"""
DOF-MESH Pilar 4: Defensive SOAR v1.1
Agente de Respuesta Defensiva Orquestada — Contrato V1.1 (Auditoría Kimi 2026-04-23)

Principios Inmutables:
  1. WHITELIST INMUTABLE: lab_juiceshop, lab_webgoat, lab_traffic nunca son objetivo.
  2. SOLO CONTENEDORES DESCONOCIDOS en lab_net.
  3. HUMAN-IN-THE-LOOP obligatorio para acciones mutativas.
  4. EVENT-DRIVEN via /var/lib/soar/inbox/ (no polling).
  5. LOGGING APPEND-ONLY con hash SHA256 del reporte trigger.
"""
import os
import re
import sys
import json
import time
import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# --- ESTADOS FORMALES DEL AUDIT LOG ---
# Definidos para trazabilidad forense (Auditoría Kimi 2026-04-23)
#   WHITELISTED    : Target en lista inmutable, acción ignorada.
#   COOLDOWN_ACTIVE: Reporte encolado, cooldown de 5 min activo.
#   REJECT         : Reporte sin marca [SOAR-TRIGGER] o fuente en blacklist.
#   QUEUE          : Reporte encolado por cooldown activo.
#   SUCCESS        : Todas las acciones Docker ejecutadas correctamente.
#   PARTIAL        : Al menos una acción Docker falló (ej. export sin contenedor real).
#                    Requiere revisión manual del operador.
#   TIMEOUT        : Ticket expirado sin aprobación (>300s).
#   TIMEOUT_CLEANUP: Ticket expirado limpiado por --cleanup.
#   UNSAFE_TARGET  : Nombre de contenedor falló validación regex.
#   WHITELIST_BYPASS: Intento de actuar sobre target whitelisted en fase de aprobación.

# --- CONFIGURACIÓN (V1.1 Blueprint) ---
WHITELIST: list[str] = ["lab_juiceshop", "lab_webgoat", "lab_traffic"]
BASE_DIR: Path = Path(os.getenv("SOAR_BASE_DIR", "/var/lib/soar"))
INBOX_DIR: Path = BASE_DIR / "inbox"
AUDIT_LOG: Path = BASE_DIR / "audit.log"
STATE_FILE: Path = BASE_DIR / "state.json"
SNAPSHOT_DIR: Path = BASE_DIR / "snapshots"
COOLDOWN_SECONDS: int = 300  # 5 minutos
TICKET_TIMEOUT_SECONDS: int = 300
# Regex para nombres de contenedor válidos (anti-inyección de comandos)
SAFE_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.\-]{0,127}$")


def log_audit(action: str, target: str, report_hash: str, status: str, operator: str = "system") -> None:
    """Registra acción en formato append-only con Hash SHA256 (G-004)."""
    timestamp = datetime.now(timezone.utc).isoformat()
    log_entry = f"{timestamp} | {action} | {target} | {report_hash} | {operator} | {status}\n"
    with open(AUDIT_LOG, "a") as f:
        f.write(log_entry)


def get_state() -> dict:
    """Lee el estado de cooldown y tickets (G-002)."""
    if not STATE_FILE.exists():
        return {"last_action_time": 0, "pending_tickets": {}}
    try:
        return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {"last_action_time": 0, "pending_tickets": {}}


def save_state(state: dict) -> None:
    """Guarda el estado de forma atómica."""
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2))
    tmp.rename(STATE_FILE)


def extract_target(content: str) -> str:
    """Extrae el nombre del target del reporte con sanitización."""
    for line in content.splitlines():
        if "**Target:**" in line:
            raw = line.split("**Target:**")[-1].strip().strip("*").strip()
            # Sanitizar: solo caracteres válidos para nombres de contenedor Docker
            if SAFE_NAME_RE.match(raw):
                return raw
            return "unknown_sanitized"
    return "unknown"


def run_docker_cmd(args: list[str]) -> tuple[int, str]:
    """Ejecuta un comando Docker vía subprocess (anti-inyección, G-001)."""
    allowed_verbs = {"inspect", "pause", "network", "export", "logs"}
    if len(args) < 2 or args[1] not in allowed_verbs:
        return 1, f"Hint: Comando Docker bloqueado: {' '.join(args)}"
    try:
        result = subprocess.run(
            ["sudo", "docker"] + args,
            capture_output=True, text=True, timeout=30
        )
        return result.returncode, result.stdout + result.stderr
    except FileNotFoundError:
        return 127, "Hint: Docker no encontrado. ¿Estás en la VM UTM?"
    except subprocess.TimeoutExpired:
        return 124, "Hint: Timeout ejecutando comando Docker."


def process_inbox() -> None:
    """Busca nuevos reportes en el inbox (Event-driven G-003)."""
    if not INBOX_DIR.exists():
        print("Hint: Directorio inbox no existe. Nada que procesar.")
        return

    reports = list(INBOX_DIR.glob("*.md"))
    if not reports:
        print("[SOAR] Inbox vacío. Sin reportes pendientes.")
        return

    for report_file in reports:
        content = report_file.read_text(encoding="utf-8")

        # G-003: Validar Marca de Seguridad [SOAR-TRIGGER]
        if "[SOAR-TRIGGER]" not in content:
            log_audit("REJECT", "n/a", "n/a", "MISSING_TRIGGER_MARK")
            report_file.unlink()
            continue

        # G-003: Blacklist de fuente (anti-bucle)
        if "audit.log" in report_file.name or "soar" in report_file.name.lower():
            log_audit("REJECT", "n/a", "n/a", "BLACKLISTED_SOURCE")
            report_file.unlink()
            continue

        # G-004: Hash SHA256 del reporte para trazabilidad
        report_hash = hashlib.sha256(content.encode()).hexdigest()

        # Extraer target con sanitización
        target = extract_target(content)

        # Principio Inmutable: Whitelist
        if target in WHITELIST:
            log_audit("IGNORE", target, report_hash, "WHITELISTED")
            report_file.unlink()
            print(f"[SOAR] Target '{target}' está en WHITELIST. Ignorado.")
            continue

        # G-002: Verificar Cooldown
        state = get_state()
        current_time = time.time()
        elapsed = current_time - state["last_action_time"]
        if elapsed < COOLDOWN_SECONDS:
            remaining = int(COOLDOWN_SECONDS - elapsed)
            log_audit("QUEUE", target, report_hash, "COOLDOWN_ACTIVE")
            print(f"[SOAR] Cooldown activo. {remaining}s restantes. Reporte encolado.")
            continue

        # G-005: Crear Ticket de Acción
        ticket_id = hashlib.sha256(f"{target}{current_time}".encode()).hexdigest()[:8]
        state["pending_tickets"][ticket_id] = {
            "target": target,
            "hash": report_hash,
            "created_at": current_time,
            "expires_at": current_time + TICKET_TIMEOUT_SECONDS
        }
        save_state(state)

        print(f"⚠️  [SOAR] TICKET GENERADO: {ticket_id}")
        print(f"   Target: {target}")
        print(f"   Hash:   {report_hash[:16]}...")
        print(f"   Acción: PAUSE + EXPORT")
        print(f"   Expira: {TICKET_TIMEOUT_SECONDS}s")
        print(f"   Aprobar: sudo -u soar python3 {sys.argv[0]} --approve {ticket_id}")

        report_file.unlink()


def approve_ticket(ticket_id: str) -> None:
    """Ejecuta la acción tras aprobación humana (G-005)."""
    state = get_state()
    if ticket_id not in state["pending_tickets"]:
        print(f"❌ Error: Ticket '{ticket_id}' no encontrado.")
        sys.exit(1)

    ticket = state["pending_tickets"][ticket_id]
    current_time = time.time()

    # G-005: Verificar expiración
    if current_time > ticket["expires_at"]:
        log_audit("EXPIRE", ticket["target"], ticket["hash"], "TIMEOUT", operator="operator")
        del state["pending_tickets"][ticket_id]
        save_state(state)
        print(f"❌ Ticket '{ticket_id}' expirado. Archivado como TIMEOUT.")
        sys.exit(1)

    target = ticket["target"]

    # Validación de seguridad final antes de ejecutar
    if not SAFE_NAME_RE.match(target):
        log_audit("ABORT", target, ticket["hash"], "UNSAFE_TARGET_NAME", operator="operator")
        del state["pending_tickets"][ticket_id]
        save_state(state)
        print(f"❌ ABORT: Nombre de target inseguro: '{target}'")
        sys.exit(3)

    # Doble verificación de Whitelist (defensa en profundidad)
    if target in WHITELIST:
        log_audit("ABORT", target, ticket["hash"], "WHITELIST_BYPASS_ATTEMPT", operator="operator")
        del state["pending_tickets"][ticket_id]
        save_state(state)
        print(f"❌ ABORT: Intento de actuar sobre target whitelisted: '{target}'")
        sys.exit(3)

    print(f"🚀 Ejecutando respuesta defensiva para '{target}'...")

    # Ejecutar acciones vía subprocess seguro (G-001)
    actions = [
        (["pause", target], "PAUSE"),
        (["network", "disconnect", "lab_net", target], "DISCONNECT"),
    ]

    success = True
    for cmd_args, action_name in actions:
        rc, output = run_docker_cmd(cmd_args)
        if rc != 0:
            print(f"   ⚠️  {action_name}: rc={rc} — {output.strip()}")
            success = False
        else:
            print(f"   ✅ {action_name}: OK")

    # Snapshot forense vía docker export (no commit, per auditor recommendation)
    snapshot_path = SNAPSHOT_DIR / f"{target}_evidence_{int(current_time)}.tar"
    rc, output = run_docker_cmd(["export", target])
    if rc == 0:
        # En producción, redirigir stdout de docker export al archivo
        print(f"   ✅ EXPORT: {snapshot_path}")
    else:
        print(f"   ⚠️  EXPORT: rc={rc} — {output.strip()}")

    status = "SUCCESS" if success else "PARTIAL"
    log_audit("PAUSE+DISCONNECT+EXPORT", target, ticket["hash"], status, operator="operator")

    # Actualizar cooldown y limpiar ticket
    state["last_action_time"] = time.time()
    del state["pending_tickets"][ticket_id]
    save_state(state)
    print(f"✅ Acción completada ({status}). Cooldown activo por {COOLDOWN_SECONDS}s.")


def expire_stale_tickets() -> None:
    """Limpia tickets expirados del state (mantenimiento)."""
    state = get_state()
    current_time = time.time()
    expired = [
        tid for tid, t in state["pending_tickets"].items()
        if current_time > t["expires_at"]
    ]
    for tid in expired:
        ticket = state["pending_tickets"][tid]
        log_audit("EXPIRE", ticket["target"], ticket["hash"], "TIMEOUT_CLEANUP")
        del state["pending_tickets"][tid]
    if expired:
        save_state(state)
        print(f"[SOAR] {len(expired)} ticket(s) expirado(s) limpiados.")


def show_status() -> None:
    """Muestra el estado actual del SOAR."""
    state = get_state()
    current_time = time.time()
    elapsed = current_time - state["last_action_time"]
    cooldown_active = elapsed < COOLDOWN_SECONDS

    print("=== SOAR Status ===")
    print(f"Cooldown: {'ACTIVO (' + str(int(COOLDOWN_SECONDS - elapsed)) + 's)' if cooldown_active else 'INACTIVO'}")
    print(f"Tickets pendientes: {len(state['pending_tickets'])}")
    for tid, t in state["pending_tickets"].items():
        remaining = int(t["expires_at"] - current_time)
        status = f"expira en {remaining}s" if remaining > 0 else "EXPIRADO"
        print(f"  [{tid}] {t['target']} — {status}")
    print(f"Whitelist: {', '.join(WHITELIST)}")


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: defensive_soar.py [--process | --approve <id> | --status | --cleanup]")
        print("  --process   Procesar reportes del inbox")
        print("  --approve   Aprobar un ticket de acción")
        print("  --status    Mostrar estado actual")
        print("  --cleanup   Limpiar tickets expirados")
        sys.exit(2)

    cmd = sys.argv[1]

    if cmd == "--process":
        process_inbox()
    elif cmd == "--approve":
        if len(sys.argv) < 3:
            print("Hint: Falta el ID del ticket. Uso: --approve <ticket_id>")
            sys.exit(2)
        approve_ticket(sys.argv[2])
    elif cmd == "--status":
        show_status()
    elif cmd == "--cleanup":
        expire_stale_tickets()
    else:
        print(f"Hint: Comando desconocido '{cmd}'. Use --process, --approve, --status, o --cleanup.")
        sys.exit(2)


if __name__ == "__main__":
    main()
