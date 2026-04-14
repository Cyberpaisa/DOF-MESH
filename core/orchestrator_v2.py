from __future__ import annotations
"""
OrchestratorV2 — Cerebro Central del DOF-MESH Second Brain v2.0.

Flujo principal:
  1. Recibe tarea (CLI o evento del vault)
  2. Recupera contexto de sesiones previas (CPR)
  3. Hunter provee contexto del vault
  4. Router MoE selecciona modelo
  5. AutonomousExecutor ejecuta la tarea
  6. Memory guarda resultado (CPR automático si aplica)
  7. EventBus notifica completación

Comandos especiales:
  /resume  → Cargar contexto de últimas 3 sesiones
  /compress → Guardar sesión actual en _agent/memory/
  /status  → Estado del sistema
  /hunter  → Estadísticas del daemon de indexación
  /exit    → Guardar sesión y salir

Sin dependencias externas para la orquestación base.
"""

import os
import sys
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core.event_bus import EventBus
from core.state_manager import StateManager
from core.rag_engine import get_rag_engine
from agents.hunter.daemon import HunterDaemon
from agents.memory.cpr import resume, save_session, should_compress, update_context
from routing.moe_router import route, get_model_config

logger = logging.getLogger("core.orchestrator_v2")


class OrchestratorV2:
    """
    Orquestador central del DOF-MESH Second Brain v2.0.

    Uso:
        orch = OrchestratorV2()
        orch.run()           # CLI interactivo
        orch.handle_task(t)  # una tarea programática
    """

    def __init__(self) -> None:
        self.bus = EventBus()
        self.state = StateManager()
        self.hunter = HunterDaemon()
        self.rag = get_rag_engine()
        self.vault_path = Path(os.getenv("OBSIDIAN_VAULT_PATH", "/Users/jquiceva/Library/Mobile Documents/com~apple~CloudDocs/cerebro-cyber/cerebro cyber"))
        self._session_log: list[str] = []
        
        # Sincronización RAG inicial (Blocking Boot)
        if self.rag:
            logger.info("Orchestrator: Cargando e indexando vault...")
            self.rag.index_directory(self.vault_path)
            self.rag.save_index()
            
        self._setup_handlers()

    # ── Handlers de Eventos ────────────────────────────────────────────

    def _setup_handlers(self) -> None:
        """Registra handlers en el EventBus."""
        self.bus.subscribe("vault_modified", self._on_vault_change)
        self.bus.subscribe("task_created", self._on_task_created)
        self.bus.subscribe("task_completed", self._on_task_completed)
        self.bus.subscribe("compress_needed", self._on_compress)

    def _on_vault_change(self, data: dict) -> None:
        """Reacciona a cambios en el vault detectados por Hunter."""
        path = data.get("path", "")
        meta = data.get("meta", {})
        logger.debug("Vault change: %s (type=%s)", Path(path).name, meta.get("type", "unknown"))

        # FASE 2.1: Re-indexar en el motor RAG
        if path and Path(path).suffix == ".md":
            logger.info("RAG: Re-indexando %s", Path(path).name)
            self.rag.index_file(path)
            self.rag.save_index()

    def _on_task_created(self, data: dict) -> None:
        """Añade tarea detectada en el vault a la cola pendiente."""
        path = data.get("path", "")
        logger.info("Nueva tarea en vault: %s", Path(path).name)
        self.state.append("pending_tasks", path)

    def _on_task_completed(self, data: dict) -> None:
        """Guarda resultado y dispara CPR si el contexto está lleno."""
        result = data.get("result", "")
        task = data.get("task", "unknown")
        self.state.append("history", {"task": task, "result": result[:500]})
        self.state.add_tokens(len(result))
        self._session_log.append(f"[{task}]: {result[:200]}")

        if self.state.needs_compression():
            self.bus.publish("compress_needed", {
                "log": "\n".join(self._session_log),
                "task": task,
            })

    def _on_compress(self, data: dict) -> None:
        """Ejecuta CPR y guarda sesión."""
        log = data.get("log", "\n".join(self._session_log))
        task = data.get("task", "auto")
        session_id = self.state.get("session_id")

        path = save_session(log, task, session_id or "")
        logger.info("CPR: sesión comprimida → %s", path.name)

        # Actualizar CONTEXT.md
        key_points = [l for l in log.splitlines() if l.strip()][:10]
        update_context(key_points, task)

        # Reset token counter
        self.state.update("token_count", 0)
        self._session_log.clear()

    # ── Core: handle_task ──────────────────────────────────────────────

    def handle_task(self, task: str) -> dict:
        """
        Procesa una tarea completa.
        Retorna dict con model, context, result.
        """
        self.state.update("current_task", task)

        # 1. Recuperar contexto de memoria previa
        memory_context = resume(n_sessions=2)

        # 2. Recuperar contexto del Vault (RAG)
        vault_context = self.rag.get_context(task, max_chars=4000)

        # 3. Routing inteligente
        model = route(task, f"{memory_context}\n\n{vault_context}", self.state)
        model_conf = get_model_config(model)

        # 4. Ejecutar tarea via Weaver o fallback
        result = self._execute(task, model_conf, memory_context, vault_context)

        # 4. Notificar completación (dispara CPR si necesario)
        self.bus.publish("task_completed", {"task": task, "result": result})

        return {
            "model": model,
            "model_description": model_conf["description"],
            "context_loaded": bool(memory_context and memory_context != "Sin memoria previa."),
            "result": result,
        }

    def _execute(self, task: str, model_conf: dict,
                 memory_context: str = "", vault_context: str = "") -> str:
        """
        Ejecuta la tarea usando el Weaver (Ollama) como backend principal.

        Estrategia de ejecución:
          - Tareas conversacionales / análisis → Weaver directo (Ollama)
          - Tareas de código con herramientas → AutonomousExecutor (loop agentic)
          - Sin Ollama → AutonomousExecutor como fallback
        """
        model_name = model_conf.get("ollama_model", "phi4:latest")
        logical_model = model_conf.get("model_name", "general")

        # ── Weaver directo para tareas conversacionales ────────────────
        # Evita el loop agentic pesado para queries simples
        if logical_model not in ("coder",):
            try:
                from agents.weaver.weaver import synthesize_context, check_connection

                # Solo usar Weaver si Ollama está disponible
                conn_status = check_connection()
                if conn_status["available"]:
                    logger.info(
                        "Weaver: usando %s para tarea '%s'",
                        model_name, task[:40]
                    )
                    result = synthesize_context(
                        task=task,
                        vault_context=vault_context,
                        memory_context=memory_context,
                        model=logical_model,
                    )
                    return result
                else:
                    logger.warning("Weaver: Ollama no disponible — cayendo a AutonomousExecutor")

            except Exception as exc:
                logger.warning("Weaver error, usando AutonomousExecutor: %s", exc)

        # ── AutonomousExecutor para código / fallback ──────────────────
        try:
            from core.autonomous_executor import AutonomousExecutor
            import uuid

            task_with_context = task
            full_ctx = f"## Memoria previa\n{memory_context}\n\n## Conocimiento Vault\n{vault_context}"
            if full_ctx.strip():
                task_with_context = (
                    f"## Contexto DOF-MESH\n"
                    f"{full_ctx[:2000]}\n\n"
                    f"## Tarea\n{task}"
                )

            executor = AutonomousExecutor(model=model_name)
            task_id = str(uuid.uuid4())[:8]
            exec_result = executor.execute(task_id, task_with_context)
            return exec_result.result

        except Exception as exc:
            logger.error("AutonomousExecutor error: %s", exc)
            return f"[ERROR] {exc}\nHint: Verifica que Ollama esté corriendo en {os.getenv('OLLAMA_URL', 'http://localhost:11434')}"

    # ── Comandos Especiales ────────────────────────────────────────────

    def _cmd_resume(self) -> str:
        ctx = resume(n_sessions=3)
        return ctx if ctx else "Sin sesiones previas."

    def _cmd_compress(self) -> str:
        log = "\n".join(self._session_log) if self._session_log else "Sesión vacía"
        path = save_session(log, "manual-compress", self.state.get("session_id") or "")
        self._session_log.clear()
        self.state.update("token_count", 0)
        return f"Sesión guardada → {path.name}"

    def _cmd_status(self) -> str:
        import json
        state_stats = self.state.get_stats()
        hunter_stats = self.hunter.get_stats()
        bus_stats = self.bus.get_stats()
        combined = {
            "state": state_stats,
            "hunter": hunter_stats,
            "event_bus": bus_stats,
        }
        return json.dumps(combined, indent=2, default=str)

    def _cmd_hunter(self) -> str:
        import json
        return json.dumps(self.hunter.get_stats(), indent=2)

    # ── Main Loop ──────────────────────────────────────────────────────

    def start_hunter(self) -> None:
        """Inicia el HunterDaemon en background."""
        self.hunter.start(self.bus)

    def run(self) -> None:
        """Loop interactivo principal."""
        # Iniciar Hunter en background
        self.start_hunter()

        # Publicar inicio de sesión
        self.bus.publish("session_start", {
            "session_id": self.state.get("session_id"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # Cargar contexto previo
        ctx = resume(n_sessions=2)
        if ctx and ctx != "Sin memoria previa.":
            logger.info("Contexto previo cargado (%d chars)", len(ctx))

        print("\n╔══════════════════════════════════════════╗")
        print("║  DOF-MESH Second Brain v2.0              ║")
        print("║  Hunter activo | CPR automático          ║")
        print("╠══════════════════════════════════════════╣")
        print("║  /resume    → cargar contexto previo     ║")
        print("║  /compress  → guardar sesión actual      ║")
        print("║  /status    → estado del sistema         ║")
        print("║  /hunter    → estadísticas del Hunter    ║")
        print("║  /exit      → guardar y salir            ║")
        print("╚══════════════════════════════════════════╝\n")

        session_id = self.state.get("session_id")
        print(f"Sesión: {session_id}")
        if ctx and ctx != "Sin memoria previa.":
            print(f"Contexto: {len(ctx)} chars de sesiones previas cargado\n")

        while True:
            try:
                raw = input(">> ").strip()
                if not raw:
                    continue

                # Comandos especiales
                if raw == "/exit":
                    print("\nGuardando sesión...")
                    self._on_compress({"log": "\n".join(self._session_log), "task": "shutdown"})
                    self.bus.publish("session_end", {"session_id": session_id})
                    print("Hasta luego. Sesión guardada en _agent/memory/")
                    break
                elif raw == "/resume":
                    print(self._cmd_resume())
                elif raw == "/compress":
                    print(self._cmd_compress())
                elif raw == "/status":
                    print(self._cmd_status())
                elif raw == "/hunter":
                    print(self._cmd_hunter())
                else:
                    # Tarea normal
                    result = self.handle_task(raw)
                    print(f"\n[{result['model']}] {result['result']}\n")

            except KeyboardInterrupt:
                print("\n\nInterrumpido. Guardando sesión...")
                self._on_compress({
                    "log": "\n".join(self._session_log),
                    "task": "keyboard-interrupt"
                })
                break
            except EOFError:
                break


# ── Entrypoint ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%H:%M:%S",
    )
    orch = OrchestratorV2()
    orch.run()
