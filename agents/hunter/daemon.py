"""
HunterDaemon — Indexador vivo del vault de Obsidian para DOF-MESH Second Brain v2.0.

Características:
  - Polling eficiente con os.stat() (soberano, sin watchdog)
  - Fix anti-iCloud: ignora archivos .icloud y archivos ocultos temporales
  - Delta updates: solo procesa archivos modificados desde último scan
  - Extrae frontmatter YAML sin dependencias externas
  - Publica eventos en EventBus cuando detecta cambios
  - Corre en hilo daemon (no bloquea el main loop)

Sin dependencias externas. Python stdlib pura.
"""

import os
import re
import json
import time
import hashlib
import logging
import threading
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.event_bus import EventBus

logger = logging.getLogger("agents.hunter.daemon")

# Configuración desde variables de entorno
VAULT_PATH = Path(
    os.getenv(
        "OBSIDIAN_VAULT_PATH",
        "/Users/jquiceva/Library/Mobile Documents/com~apple~CloudDocs/cerebro-cyber/cerebro cyber"
    )
)
INDEX_FILE = VAULT_PATH / "_agent" / "memory" / "index.json"
POLL_INTERVAL_SECS = int(os.getenv("HUNTER_POLL_SECS", "8"))

# Solo escanear estas carpetas (READ targets según AGENTS.md)
SCAN_FOLDERS = ["wiki", "raw", "_agent/tasks"]

# Patrones a ignorar (iCloud + backups)
IGNORE_SUFFIXES = {".icloud", ".bak", ".tmp"}
IGNORE_PREFIXES = {".", "~"}


class HunterDaemon:
    """
    Daemon de indexación viva del vault de Obsidian.

    Ciclo: scan_delta() → publicar vault_modified/task_created → esperar N segundos → repetir.

    Uso:
        bus = EventBus()
        hunter = HunterDaemon()
        hunter.start(bus)   # hilo daemon, no bloquea
    """

    def __init__(self, vault_path: Path = VAULT_PATH) -> None:
        self.vault_path = vault_path
        self.index_file = vault_path / "_agent" / "memory" / "index.json"
        self._index: dict[str, str] = self._load_index()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._scans_done = 0
        self._files_indexed = 0

    # ── Index I/O ────────────────────────────────────────────────────

    def _load_index(self) -> dict:
        """Carga índice de mtimes desde disco."""
        if self.index_file.exists():
            try:
                return json.loads(self.index_file.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.warning("No se pudo cargar index.json: %s", exc)
        return {}

    def _save_index(self) -> None:
        """Persiste índice actualizado."""
        try:
            self.index_file.parent.mkdir(parents=True, exist_ok=True)
            self.index_file.write_text(
                json.dumps(self._index, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception as exc:
            logger.error("Error al guardar index.json: %s", exc)

    # ── File Filtering (Anti-iCloud Bug) ─────────────────────────────

    def _should_index(self, path: Path) -> bool:
        """
        Determina si un archivo debe ser indexado.

        Ignorar:
          - Archivos con sufijos de iCloud/backups (.icloud, .bak, .tmp)
          - Archivos ocultos (empiezan con . o ~)
          - Archivos que no son .md
        """
        name = path.name
        suffix = path.suffix

        # Anti-iCloud: archivos pending de sincronización
        if suffix in IGNORE_SUFFIXES:
            return False

        # Archivos ocultos o temporales
        if any(name.startswith(p) for p in IGNORE_PREFIXES):
            return False

        # Solo markdown
        if suffix != ".md":
            return False

        # Solo carpetas controladas
        path_str = str(path)
        if not any(folder in path_str for folder in SCAN_FOLDERS):
            return False

        return True

    # ── Frontmatter Parser (Soberano) ─────────────────────────────────

    def extract_frontmatter(self, path: Path) -> dict:
        """
        Extrae frontmatter YAML de una nota Markdown.
        Implementación soberana sin PyYAML.
        """
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            logger.debug("No se pudo leer %s: %s", path, exc)
            return {}

        if not content.strip().startswith("---"):
            return {}

        try:
            end_idx = content.index("---", 3)
            fm_raw = content[3:end_idx].strip()
        except ValueError:
            return {}

        meta = {}
        for line in fm_raw.splitlines():
            if ":" in line and not line.startswith(" "):
                key, _, value = line.partition(":")
                k = key.strip()
                v = value.strip().strip('"').strip("'")
                # Parsear listas simples: [a, b, c]
                if v.startswith("[") and v.endswith("]"):
                    v = [i.strip().strip('"') for i in v[1:-1].split(",")]
                meta[k] = v

        return meta

    # ── Delta Scanner ──────────────────────────────────────────────────

    def scan_delta(self) -> list[dict]:
        """
        Escanea carpetas controladas y retorna solo archivos modificados.
        Retorna lista de {path, meta, is_new} para cada archivo cambiado.
        """
        changed = []

        for folder in SCAN_FOLDERS:
            target = self.vault_path / folder
            if not target.exists():
                continue

            for md_file in target.rglob("*"):
                if not self._should_index(md_file):
                    continue

                try:
                    mtime = str(md_file.stat().st_mtime)
                except Exception:
                    continue  # Archivo iCloud no descargado aún

                key = str(md_file)
                is_new = key not in self._index

                if self._index.get(key) != mtime:
                    self._index[key] = mtime
                    self._files_indexed += 1
                    meta = self.extract_frontmatter(md_file)
                    changed.append({
                        "path": key,
                        "meta": meta,
                        "is_new": is_new,
                    })

        if changed:
            self._save_index()
            logger.info("Hunter: %d archivos modificados detectados", len(changed))

        return changed

    def build_initial_index(self) -> int:
        """
        Construye el índice inicial completo.
        Retorna número de archivos indexados.
        """
        logger.info("Hunter: construyendo índice inicial del vault...")
        changed = self.scan_delta()
        logger.info("Hunter: %d archivos en índice inicial", len(self._index))
        return len(self._index)

    # ── Daemon Loop ────────────────────────────────────────────────────

    def _run_loop(self, event_bus: Optional["EventBus"]) -> None:
        """Loop principal del daemon."""
        logger.info(
            "HunterDaemon activo | vault=%s | poll=%ds | carpetas=%s",
            self.vault_path.name, POLL_INTERVAL_SECS, SCAN_FOLDERS
        )

        # Índice inicial
        count = self.build_initial_index()
        logger.info("Hunter: %d archivos en índice base", count)

        while self._running:
            try:
                changed = self.scan_delta()
                self._scans_done += 1

                if event_bus and changed:
                    for file_info in changed:
                        # Evento genérico de cambio
                        event_bus.publish("vault_modified", file_info)

                        # Evento específico si es una tarea pendiente
                        meta = file_info.get("meta", {})
                        if (
                            meta.get("type") == "task"
                            and meta.get("status") == "pending"
                        ):
                            event_bus.publish("task_created", file_info)
                            logger.info(
                                "Hunter: nueva tarea detectada → %s",
                                file_info["path"]
                            )

            except Exception as exc:
                logger.error("Hunter scan error: %s", exc)

            time.sleep(POLL_INTERVAL_SECS)

    def start(self, event_bus: Optional["EventBus"] = None) -> None:
        """Inicia el daemon en un hilo background (no bloquea)."""
        if self._running:
            logger.warning("HunterDaemon ya está corriendo")
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop,
            args=(event_bus,),
            daemon=True,  # muere con el proceso principal
            name="hunter-daemon",
        )
        self._thread.start()
        logger.info("HunterDaemon lanzado en background")

    def stop(self) -> None:
        """Detiene el daemon."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("HunterDaemon detenido")

    def get_stats(self) -> dict:
        """Estadísticas del daemon."""
        return {
            "running": self._running,
            "vault": str(self.vault_path),
            "indexed_files": len(self._index),
            "scans_done": self._scans_done,
            "files_processed": self._files_indexed,
            "poll_interval_secs": POLL_INTERVAL_SECS,
            "scan_folders": SCAN_FOLDERS,
        }


# ── Entrypoint standalone ──────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

    hunter = HunterDaemon()

    # Modo --index: solo construir índice y salir
    if "--index" in sys.argv:
        count = hunter.build_initial_index()
        print(f"[Hunter] Índice construido: {count} archivos")
        print(f"[Hunter] Index guardado en: {hunter.index_file}")
        sys.exit(0)

    # Modo --stats: mostrar estadísticas
    if "--stats" in sys.argv:
        hunter.build_initial_index()
        import json as _json
        print(_json.dumps(hunter.get_stats(), indent=2))
        sys.exit(0)

    # Modo daemon: correr indefinidamente
    hunter.start()
    print("[Hunter] Daemon activo. Ctrl+C para detener.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        hunter.stop()
        print("\n[Hunter] Detenido.")
