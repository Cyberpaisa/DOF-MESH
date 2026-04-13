#!/usr/bin/env python3
"""
knowledge_health_check.py — Extrae aprendizajes de cycles.jsonl y los persiste en el vault Obsidian.

DOF Mesh Legion · Cyber Paisa

Uso:
    python3 scripts/knowledge_health_check.py          # procesa entradas nuevas
    python3 scripts/knowledge_health_check.py --dry-run  # muestra sin escribir
    python3 scripts/knowledge_health_check.py --all    # reprocesa todo (ignora processed)

Criterio de aprendizaje:
    - result_status == "error"              → siempre es aprendizaje
    - mode == "improve" y status success    → mejora exitosa, documentar
    - mode == "build" y status success      → orden ejecutada, documentar
    - budget_exceeded                       → límite de costo, documentar
    - Acción nueva nunca vista antes        → patrón emergente

Salida:
    - Appends a ~/cerebro cyber/cerebro cyber/dof-mesh/main/aprendizajes.md
    - Actualiza logs/daemon/knowledge_processed.jsonl con timestamps procesados
"""

import json
import os
import sys
import argparse
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Generator

BASE_DIR = Path(__file__).parent.parent
CYCLES_LOG   = BASE_DIR / "logs" / "daemon" / "cycles.jsonl"
PROCESSED_LOG = BASE_DIR / "logs" / "daemon" / "knowledge_processed.jsonl"
VAULT_NOTE   = Path.home() / "cerebro cyber" / "cerebro cyber" / "dof-mesh" / "main" / "aprendizajes.md"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _entry_id(entry: dict) -> str:
    """ID estable para un ciclo: hash de timestamp + cycle."""
    key = f"{entry.get('timestamp', 0):.3f}:{entry.get('cycle', 0)}"
    return hashlib.md5(key.encode()).hexdigest()[:12]


def _stream_cycles(path: Path) -> Generator[dict, None, None]:
    """Lee cycles.jsonl línea por línea (streaming — nunca carga todo en RAM)."""
    if not path.exists():
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def _load_processed_ids(path: Path) -> set[str]:
    """Carga IDs de entradas ya procesadas."""
    ids: set[str] = set()
    if not path.exists():
        return ids
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if "entry_id" in rec:
                    ids.add(rec["entry_id"])
            except json.JSONDecodeError:
                continue
    return ids


def _mark_processed(path: Path, entry_id: str, summary: str) -> None:
    """Registra un entry_id como procesado."""
    rec = {
        "entry_id": entry_id,
        "ts": datetime.now().isoformat(timespec="seconds"),
        "summary": summary[:120],
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


# ─── Criterio de relevancia ────────────────────────────────────────────────────

def _is_learnable(entry: dict, seen_actions: set[str]) -> tuple[bool, str]:
    """
    Determina si una entrada del ciclo genera un aprendizaje.

    Returns:
        (es_relevante, tipo_aprendizaje)
    """
    status = entry.get("result_status", "")
    mode   = entry.get("mode", "")
    action = entry.get("action", "")

    if status == "error":
        return True, "error"

    if status == "budget_exceeded":
        return True, "budget_exceeded"

    if status == "success" and mode in ("improve", "build"):
        return True, f"success_{mode}"

    # Acción nueva: primer vez que el daemon la toma
    action_key = action[:80].lower().strip()
    if action_key and action_key not in seen_actions:
        seen_actions.add(action_key)
        return True, "nuevo_patron"

    return False, ""


# ─── Formateo de aprendizaje ───────────────────────────────────────────────────

def _format_learning(entry: dict, tipo: str) -> str:
    """Formatea un ciclo como bloque Markdown para el vault."""
    ts   = entry.get("iso", entry.get("timestamp", "?"))
    mode = entry.get("mode", "?").upper()
    action = entry.get("action", "?")
    status = entry.get("result_status", "?")
    output = entry.get("output_summary", "")[:300]
    elapsed = entry.get("elapsed_ms", 0)

    tipo_labels = {
        "error":          "🔴 Error detectado",
        "budget_exceeded": "🟡 Budget excedido",
        "success_improve": "🟢 Mejora exitosa",
        "success_build":   "🟢 Orden ejecutada",
        "nuevo_patron":    "🔵 Patrón nuevo",
    }
    label = tipo_labels.get(tipo, "⚪ Ciclo notable")

    lines = [
        f"### {label} — {ts}",
        f"- **Modo:** {mode} | **Estado:** {status} | **Duración:** {elapsed:.0f}ms",
        f"- **Acción:** {action}",
    ]
    if output and tipo in ("error", "budget_exceeded"):
        lines.append(f"- **Output:** {output}")

    return "\n".join(lines) + "\n"


# ─── Patch al vault ────────────────────────────────────────────────────────────

def _patch_vault_note(note_path: Path, new_blocks: list[str], dry_run: bool) -> bool:
    """
    Appends nuevos bloques de aprendizaje a la nota del vault.

    Inserta bajo el heading '## Aprendizajes del Daemon (auto-generados)'
    si existe; si no, lo crea al final del archivo.
    """
    if not note_path.exists():
        print(f"[WARN] Nota no encontrada: {note_path}", file=sys.stderr)
        return False

    content = note_path.read_text(encoding="utf-8")
    section_header = "## Aprendizajes del Daemon (auto-generados)\n"

    new_content_block = "\n" + "\n".join(new_blocks) + "\n"

    if section_header in content:
        # Insertar justo después del heading
        insert_at = content.index(section_header) + len(section_header)
        updated = content[:insert_at] + new_content_block + content[insert_at:]
    else:
        # Crear sección al final
        updated = content.rstrip("\n") + "\n\n" + section_header + new_content_block

    if dry_run:
        print(f"[DRY RUN] Se escribirían {len(new_blocks)} bloques en {note_path}")
        for block in new_blocks:
            print("  " + block.split("\n")[0])
        return True

    note_path.write_text(updated, encoding="utf-8")
    return True


# ─── Función principal (callable desde daemon) ────────────────────────────────

def run_check(dry_run: bool = False, reprocess_all: bool = False,
              max_per_run: int = 30) -> list[str]:
    """
    Extrae aprendizajes nuevos de cycles.jsonl y los escribe en el vault.

    Args:
        dry_run: Solo reporta, no escribe.
        reprocess_all: Ignora el historial de procesados.
        max_per_run: Máximo de bloques a escribir por ejecución (evita flooding).
                     El daemon usa 5; el CLI manual puede usar más.

    Returns:
        Lista de sumarios de aprendizajes encontrados.
    """
    processed_ids = set() if reprocess_all else _load_processed_ids(PROCESSED_LOG)
    seen_actions: set[str] = set()
    new_blocks: list[str] = []
    new_entry_ids: list[tuple[str, str]] = []  # (entry_id, summary)
    skip_ids: list[str] = []  # no-learnable → marcar processed sin escribir

    # Primera pasada: cargar acciones ya vistas (para dedup "nuevo_patron")
    for entry in _stream_cycles(CYCLES_LOG):
        eid = _entry_id(entry)
        if eid in processed_ids:
            action_key = entry.get("action", "")[:80].lower().strip()
            if action_key:
                seen_actions.add(action_key)

    for entry in _stream_cycles(CYCLES_LOG):
        if len(new_blocks) >= max_per_run:
            break

        eid = _entry_id(entry)
        if eid in processed_ids:
            continue

        is_learnable, tipo = _is_learnable(entry, seen_actions)
        if not is_learnable:
            skip_ids.append(eid)
            processed_ids.add(eid)
            continue

        block = _format_learning(entry, tipo)
        new_blocks.append(block)
        summary = f"{tipo}:{entry.get('action', '')[:60]}"
        new_entry_ids.append((eid, summary))
        processed_ids.add(eid)

    if not new_blocks:
        print("[OK] No hay aprendizajes nuevos.")
        return []

    # Escribir en vault
    success = _patch_vault_note(VAULT_NOTE, new_blocks, dry_run)

    # Marcar como procesados (learnable + skipped)
    if not dry_run:
        if success:
            for eid, summary in new_entry_ids:
                _mark_processed(PROCESSED_LOG, eid, summary)
        for eid in skip_ids:
            _mark_processed(PROCESSED_LOG, eid, "skip")

    summaries = [eid_sum[1] for eid_sum in new_entry_ids]
    print(f"[OK] {len(new_blocks)} aprendizaje(s) escritos en vault.")
    return summaries


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Extrae aprendizajes del daemon DOF y los persiste en el vault Obsidian."
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Muestra qué se escribiría sin modificar archivos.")
    parser.add_argument("--all", action="store_true", dest="reprocess_all",
                        help="Reprocesa todas las entradas (ignora historial).")
    parser.add_argument("--limit", type=int, default=30,
                        help="Máximo de bloques a escribir por ejecución (default: 30).")
    args = parser.parse_args()

    summaries = run_check(dry_run=args.dry_run, reprocess_all=args.reprocess_all,
                          max_per_run=args.limit)
    if summaries:
        for s in summaries:
            print(f"  · {s}")


if __name__ == "__main__":
    main()
