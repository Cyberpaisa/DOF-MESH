"""
metadata_fixer.py — Inyector de frontmatter para el vault de Obsidian.

Reglas:
  - Solo opera en carpetas autorizadas (AGENTS.md)
  - Modo DRY_RUN por defecto (no modifica nada)
  - Backup .bak antes de cualquier escritura
  - Genera reporte en _agent/logs/metadata_fix_report.md

Uso:
  python3 tools/metadata_fixer.py                    # dry-run
  python3 tools/metadata_fixer.py --live             # aplicar cambios
  python3 tools/metadata_fixer.py --live --folder wiki  # solo wiki/
"""

import os
import re
import sys
from typing import Optional
import shutil
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("tools.metadata_fixer")

VAULT = Path(
    os.getenv(
        "OBSIDIAN_VAULT_PATH",
        "/Users/jquiceva/Library/Mobile Documents/com~apple~CloudDocs/cerebro-cyber/cerebro cyber"
    )
)

# Solo estas carpetas — protección de vault personal
TARGET_FOLDERS = ["wiki", "raw", "_agent/tasks"]

REPORT_PATH = VAULT / "_agent" / "logs" / "metadata_fix_report.md"

# Inferencia de dominio por carpeta
_DOMAIN_MAP = {
    "DOF-MESH": "dof-mesh",
    "Claude-Code": "claude-code",
    "Blockchain": "blockchain",
    "Proyectos": "projects",
    "tasks": "meta",
}


def _infer_domain(path: Path) -> str:
    """Infiere el dominio de la nota según su carpeta padre."""
    for part in path.parts:
        if part in _DOMAIN_MAP:
            return _DOMAIN_MAP[part]
    return "general"


def _infer_type(path: Path) -> str:
    """Infiere el tipo de nota según su carpeta."""
    path_str = str(path)
    if "_agent/tasks" in path_str:
        return "task"
    if "raw" in path_str:
        return "knowledge"
    return "knowledge"


def build_frontmatter(file_path: Path) -> str:
    """Construye el frontmatter YAML para una nota."""
    now = datetime.now(timezone.utc)
    slug = re.sub(r"[^a-zA-Z0-9\-]", "-", file_path.stem.lower())[:40]
    note_id = f"{now.strftime('%Y%m%d')}-{slug}"
    domain = _infer_domain(file_path)
    note_type = _infer_type(file_path)

    return f"""---
id: {note_id}
type: {note_type}
domain: {domain}
priority: medium
status: active
created: {now.strftime('%Y-%m-%d')}
---

"""


def has_frontmatter(content: str) -> bool:
    """True si la nota ya tiene frontmatter YAML."""
    return content.strip().startswith("---")


def is_icloud_file(path: Path) -> bool:
    """Detecta archivos iCloud no descargados."""
    return (
        path.suffix == ".icloud"
        or path.name.startswith(".")
        or ".icloud" in str(path)
    )


def fix_vault(
    dry_run: bool = True,
    target_folder: Optional[str] = None
) -> dict:
    """
    Analiza y corrige frontmatter en el vault.

    Args:
        dry_run: Si True, solo reporta sin modificar.
        target_folder: Si se especifica, solo procesa esa carpeta.

    Returns:
        dict con estadísticas: fixed, skipped, errors, icloud_skipped
    """
    folders = [target_folder] if target_folder else TARGET_FOLDERS
    stats = {"fixed": 0, "skipped": 0, "errors": 0, "icloud_skipped": 0}
    report_lines = [
        f"# Metadata Fix Report",
        f"**Fecha**: {datetime.now().strftime('%Y-%m-%d %H:%M COT')}",
        f"**Modo**: {'DRY RUN 🔍' if dry_run else 'LIVE ✅'}",
        f"**Carpetas**: {', '.join(folders)}",
        "",
    ]

    for folder in folders:
        target = VAULT / folder
        if not target.exists():
            report_lines.append(f"\n⚠️ Carpeta no encontrada: `{folder}`")
            continue

        report_lines.append(f"\n## `{folder}/`\n")

        for md_file in sorted(target.rglob("*.md")):
            try:
                # Ignorar archivos iCloud
                if is_icloud_file(md_file):
                    stats["icloud_skipped"] += 1
                    continue

                # Ignorar backups
                if md_file.suffix in {".bak", ".tmp"}:
                    continue

                content = md_file.read_text(encoding="utf-8", errors="replace")

                # Ya tiene frontmatter
                if has_frontmatter(content):
                    stats["skipped"] += 1
                    report_lines.append(f"- ⏭️ `{md_file.name}` (ya tiene frontmatter)")
                    continue

                # Construir nuevo frontmatter
                new_frontmatter = build_frontmatter(md_file)
                new_content = new_frontmatter + content

                if dry_run:
                    report_lines.append(f"- 🔍 `{md_file.name}` (necesita frontmatter)")
                else:
                    # Backup antes de modificar
                    backup = md_file.with_suffix(".md.bak")
                    shutil.copy(md_file, backup)
                    md_file.write_text(new_content, encoding="utf-8")
                    report_lines.append(f"- ✅ `{md_file.name}` (frontmatter inyectado)")

                stats["fixed"] += 1

            except PermissionError:
                stats["errors"] += 1
                report_lines.append(f"- ❌ `{md_file.name}` (sin permisos)")
            except Exception as exc:
                stats["errors"] += 1
                report_lines.append(f"- ❌ `{md_file.name}` (error: {exc})")

    # Resumen
    mode_label = "necesitan" if dry_run else "modificados"
    report_lines += [
        "",
        "---",
        f"## Resumen",
        f"- Archivos que {mode_label} frontmatter: **{stats['fixed']}**",
        f"- Ya correctos (skipped): **{stats['skipped']}**",
        f"- Errores: **{stats['errors']}**",
        f"- iCloud no descargados (ignorados): **{stats['icloud_skipped']}**",
    ]

    # Guardar reporte
    report_text = "\n".join(report_lines)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report_text, encoding="utf-8")

    # Imprimir resumen
    print(report_text)
    print(f"\nReporte guardado → {REPORT_PATH}")
    return stats


# ── CLI ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    dry_run = "--live" not in sys.argv
    folder = None
    if "--folder" in sys.argv:
        idx = sys.argv.index("--folder")
        if idx + 1 < len(sys.argv):
            folder = sys.argv[idx + 1]

    if dry_run:
        print("=" * 50)
        print("MODO DRY RUN — no se modificará ningún archivo")
        print("Usa --live para aplicar cambios reales")
        print("=" * 50 + "\n")

    stats = fix_vault(dry_run=dry_run, target_folder=folder)
