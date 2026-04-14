#!/usr/bin/env python3
"""
run_second_brain.py — Entrypoint del DOF-MESH Second Brain v2.0.

Uso:
  python3 scripts/run_second_brain.py                # modo interactivo
  python3 scripts/run_second_brain.py --index        # indexar vault y salir
  python3 scripts/run_second_brain.py --fix-meta     # fix metadata (dry-run)
  python3 scripts/run_second_brain.py --fix-meta --live  # fix metadata (real)
  python3 scripts/run_second_brain.py --cpr-test     # test CPR compresión
  python3 scripts/run_second_brain.py --status       # estado del sistema
"""

import os
import sys
import logging
import argparse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%H:%M:%S",
    )


def cmd_index() -> None:
    """Construye el índice inicial del vault y sale."""
    from agents.hunter.daemon import HunterDaemon
    hunter = HunterDaemon()
    count = hunter.build_initial_index()
    print(f"[Hunter] ✅ Índice construido: {count} archivos")
    print(f"[Hunter] Guardado en: {hunter.index_file}")


def cmd_fix_meta(live: bool = False) -> None:
    """Ejecuta metadata_fixer sobre el vault."""
    sys.path.insert(0, os.path.join(BASE_DIR, "tools"))
    from tools.metadata_fixer import fix_vault
    stats = fix_vault(dry_run=not live)
    mode = "LIVE" if live else "DRY_RUN"
    print(f"\n[MetaFixer] {mode} completado: {stats}")


def cmd_cpr_test() -> None:
    """Test del sistema CPR."""
    from agents.memory.cpr import compress, save_session, resume, should_compress

    test_log = """
    Decidí usar polling con os.stat() — más soberano que watchdog.
    ✅ Creé _agent/ separado del vault personal.
    Error detectado: .icloud files causan falsos positivos → fix implementado.
    Resultado: Hunter indexa 40 archivos en el vault.
    Próximo: conectar Ollama como Weaver para síntesis real.
    """

    print("=== CPR Test ===")
    print(f"should_compress(test_log): {should_compress(test_log)}")
    compressed = compress(test_log, "test-cpr")
    print(f"\nComprimido ({len(test_log)} → {len(compressed)} chars):\n{compressed}")
    path = save_session(test_log, "test-cpr")
    print(f"\n✅ Sesión guardada: {path}")

    ctx = resume(1)
    print(f"\n✅ Resume cargado: {len(ctx)} chars")


def cmd_status() -> None:
    """Muestra estado completo del sistema."""
    import json
    import importlib.util

    def load(path, name):
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    print("=" * 50)
    print("DOF-MESH Second Brain v2.0 — Estado del Sistema")
    print("=" * 50)

    # Hunter
    hunter_mod = load(os.path.join(BASE_DIR, "agents/hunter/daemon.py"), "daemon")
    hunter = hunter_mod.HunterDaemon()
    h_stats = hunter.get_stats()
    print(f"\n🔍 Hunter Daemon")
    print(f"  Vault: {h_stats['vault']}")
    print(f"  Archivos indexados: {len(hunter._load_index())}")
    print(f"  Carpetas de escaneo: {h_stats['scan_folders']}")

    # StateManager
    sm_mod = load(os.path.join(BASE_DIR, "core/state_manager.py"), "state_manager")
    state = sm_mod.StateManager()
    s = state.get_stats()
    print(f"\n📊 State Manager")
    print(f"  Session ID: {s['session_id']}")
    print(f"  Tarea actual: {s['current_task'] or 'None'}")
    print(f"  Historial: {s['history_count']} entradas")
    print(f"  Tareas pendientes: {s['pending_tasks']}")

    # EventBus
    eb_mod = load(os.path.join(BASE_DIR, "core/event_bus.py"), "event_bus")
    bus = eb_mod.EventBus()
    print(f"\n🔌 Event Bus: ready")

    # Vault check
    vault_path = os.getenv(
        "OBSIDIAN_VAULT_PATH",
        "/Users/jquiceva/Library/Mobile Documents/com~apple~CloudDocs/cerebro-cyber/cerebro cyber"
    )
    agent_path = os.path.join(vault_path, "_agent")
    print(f"\n🧠 Vault de Obsidian")
    print(f"  Path: {vault_path}")
    print(f"  _agent/ existe: {'✅' if os.path.exists(agent_path) else '❌'}")
    print(f"  AGENTS.md: {'✅' if os.path.exists(os.path.join(vault_path, 'AGENTS.md')) else '❌'}")
    print(f"  CONTEXT.md: {'✅' if os.path.exists(os.path.join(vault_path, '_agent/memory/CONTEXT.md')) else '❌'}")
    print(f"  index.json: {'✅' if os.path.exists(os.path.join(vault_path, '_agent/memory/index.json')) else '❌'}")

    print("\n" + "=" * 50)
    print("🟢 Sistema operativo")
    print("=" * 50)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="DOF-MESH Second Brain v2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--index", action="store_true", help="Construir índice del vault y salir")
    parser.add_argument("--fix-meta", action="store_true", help="Ejecutar metadata_fixer (dry-run por defecto)")
    parser.add_argument("--live", action="store_true", help="Aplicar cambios reales (usar con --fix-meta)")
    parser.add_argument("--cpr-test", action="store_true", help="Test del sistema CPR")
    parser.add_argument("--status", action="store_true", help="Estado del sistema")
    parser.add_argument("--verbose", action="store_true", help="Logging detallado")
    parser.add_argument("--json", action="store_true", help="Salida en JSON (modo agente)")
    args = parser.parse_args()

    setup_logging(args.verbose)

    if args.index:
        cmd_index()
    elif args.fix_meta:
        cmd_fix_meta(live=args.live)
    elif args.cpr_test:
        cmd_cpr_test()
    elif args.status:
        cmd_status()
    else:
        # Modo interactivo — lanzar Orchestrator
        from core.orchestrator_v2 import OrchestratorV2
        orch = OrchestratorV2()
        orch.run()


if __name__ == "__main__":
    main()
