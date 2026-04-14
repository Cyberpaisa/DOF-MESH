#!/usr/bin/env python3
"""
second_brain.py — Sistema de Segundo Cerebro para Obsidian
DOF Mesh Legion · Cyber Paisa

Uso:
    python3 scripts/second_brain.py add "título" --content "texto" --tags tag1,tag2
    python3 scripts/second_brain.py process            # procesa todos los archivos en raw/
    python3 scripts/second_brain.py watch              # vigila raw/ en tiempo real
    python3 scripts/second_brain.py search "query"    # busca en el vault
    python3 scripts/second_brain.py health            # verifica el vault
    python3 scripts/second_brain.py sync              # sincroniza docs/ DOF → vault
"""

import sys
import os
import re
import json
import time
import hashlib
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Optional

# import frontmatter (Eliminado - usamos yaml directamente)
import yaml
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

# markitdown — Microsoft — convierte PDF, DOCX, PPTX, imágenes → Markdown
try:
    from markitdown import MarkItDown
    _MARKITDOWN = MarkItDown()
    MARKITDOWN_OK = True
except ImportError:
    MARKITDOWN_OK = False

console = Console()

# ─── Configuración ────────────────────────────────────────────────────────────
VAULT_PATH = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/cerebro-cyber/cerebro cyber"
DOF_DOCS   = Path("/Users/jquiceva/equipo-de-agentes/docs")
RAW_DIR    = VAULT_PATH / "raw"
WIKI_DIR   = VAULT_PATH / "wiki"
OUTPUTS    = VAULT_PATH / "outputs"

SECTION_MAP = {
    "dof": WIKI_DIR / "DOF-MESH",
    "dof-mesh": WIKI_DIR / "DOF-MESH",
    "governance": WIKI_DIR / "DOF-MESH",
    "claude": WIKI_DIR / "Claude-Code",
    "claude-code": WIKI_DIR / "Claude-Code",
    "obsidian": WIKI_DIR / "Claude-Code",
    "blockchain": WIKI_DIR / "Blockchain",
    "conflux": WIKI_DIR / "Blockchain",
    "avalanche": WIKI_DIR / "Blockchain",
    "proyecto": WIKI_DIR / "Proyectos",
    "proyectos": WIKI_DIR / "Proyectos",
    "enigma": WIKI_DIR / "Proyectos",
    "snowrail": WIKI_DIR / "Proyectos",
}

DOF_SYNC_MAP = {
    "INTEL_CLAUDE_CODE_ARCH_APR2026.md": WIKI_DIR / "Claude-Code" / "intel-claude-code.md",
    "PLAN_ACCION_APR2026.md":            WIKI_DIR / "DOF-MESH" / "plan-accion-abril-2026-full.md",
    "CONFLUX_HACKFEST_PAPER.md":         WIKI_DIR / "Blockchain" / "conflux-paper.md",
    "ARCHITECTURE.md":                   WIKI_DIR / "DOF-MESH" / "arquitectura-full.md",
}

# ─── Helpers ──────────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[àáâãäå]', 'a', text)
    text = re.sub(r'[èéêë]', 'e', text)
    text = re.sub(r'[ìíîï]', 'i', text)
    text = re.sub(r'[òóôõö]', 'o', text)
    text = re.sub(r'[ùúûü]', 'u', text)
    text = re.sub(r'[ñ]', 'n', text)
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s]+', '-', text)
    return text[:60]

def detect_section(tags: list, title: str) -> Path:
    combined = " ".join(tags + [title.lower()])
    for keyword, path in SECTION_MAP.items():
        if keyword in combined:
            return path
    return WIKI_DIR / "DOF-MESH"  # default

def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")

def file_hash(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()[:8]

def write_note(dest: Path, title: str, body: str, tags: list, extra_meta: dict = None):
    dest.parent.mkdir(parents=True, exist_ok=True)
    meta = {
        "tags": tags,
        "fecha": now_str(),
        "estado": "activo",
    }
    if extra_meta:
        meta.update(extra_meta)
    # Header
    content = f"---\n"
    for k, v in meta.items():
        if isinstance(v, list):
            content += f"{k}: [{', '.join(v)}]\n"
        else:
            content += f"{k}: {v}\n"
    content += f"---\n\n# {title}\n\n{body}\n"
    dest.write_text(content, encoding="utf-8")
    console.print(f"  [green]✓[/green] {dest.relative_to(VAULT_PATH)}")

# ─── Comando: add ─────────────────────────────────────────────────────────────

def cmd_add(title: str, content: str, tags_str: str = "", section: str = ""):
    tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []
    slug = slugify(title)

    if section:
        dest_dir = SECTION_MAP.get(section.lower(), WIKI_DIR / "DOF-MESH")
    else:
        dest_dir = detect_section(tags, title)

    dest = dest_dir / f"{slug}.md"
    write_note(dest, title, content, tags)
    console.print(Panel(f"[bold green]Nota creada:[/bold green] {dest}", expand=False))

# ─── Comando: process ─────────────────────────────────────────────────────────

def cmd_process():
    """Procesa todos los archivos en raw/ → wiki/"""
    RAW_DIR.mkdir(exist_ok=True)
    raw_files = list(RAW_DIR.glob("*.md")) + list(RAW_DIR.glob("*.txt"))

    if not raw_files:
        console.print("[yellow]No hay archivos en raw/ para procesar[/yellow]")
        return

    console.print(f"\n[bold]Procesando {len(raw_files)} archivos de raw/...[/bold]\n")

    for raw_file in raw_files:
        _process_file(raw_file)

    console.print("\n[bold green]Proceso completado.[/bold green]")

BINARY_EXTENSIONS = {".pdf", ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls",
                     ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp",
                     ".html", ".htm", ".epub", ".csv"}

def _process_file(raw_file: Path):
    title = raw_file.stem.replace("-", " ").replace("_", " ").title()
    suffix = raw_file.suffix.lower()

    # — Convertir binarios con markitdown —
    if suffix in BINARY_EXTENSIONS:
        if not MARKITDOWN_OK:
            console.print(f"  [red]✗[/red] {raw_file.name} — markitdown no disponible")
            return
        try:
            console.print(f"  [cyan]→[/cyan] Convirtiendo {raw_file.name} con markitdown...")
            result = _MARKITDOWN.convert(str(raw_file))
            body = result.text_content
            meta_tags = ["convertido", suffix.lstrip(".")]
        except Exception as e:
            console.print(f"  [red]✗[/red] Error convirtiendo {raw_file.name}: {e}")
            return
    else:
        # Texto plano / Markdown
        text = raw_file.read_text(encoding="utf-8", errors="replace")
        meta_tags = []
        body = text
        
        if text.startswith("---"):
            try:
                parts = text.split("---", 2)
                if len(parts) >= 3:
                    meta = yaml.safe_load(parts[1]) or {}
                    meta_tags = meta.get("tags", [])
                    if isinstance(meta_tags, str):
                        meta_tags = [meta_tags]
                    body = parts[2].strip()
            except Exception:
                pass

    # Detectar sección
    filename_tags = raw_file.stem.lower().split("-")
    tags = list(set(meta_tags + filename_tags))
    dest_dir = detect_section(tags, title)
    slug = slugify(title)
    dest = dest_dir / f"{slug}.md"

    if dest.exists():
        console.print(f"  [yellow]~[/yellow] {raw_file.name} → ya existe {dest.name}")
    else:
        write_note(dest, title, body, tags, {"fuente": f"raw/{raw_file.name}", "formato_origen": suffix})
        # Marcar como procesado
        processed_dir = RAW_DIR / "_procesados"
        processed_dir.mkdir(exist_ok=True)
        raw_file.rename(processed_dir / raw_file.name)

# ─── Comando: watch ───────────────────────────────────────────────────────────

def cmd_watch():
    """Vigila raw/ en tiempo real y procesa automáticamente"""
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        console.print("[red]Instala watchdog: pip3 install watchdog --break-system-packages[/red]")
        return

    WATCHED_EXTENSIONS = {".md", ".txt", ".pdf", ".docx", ".doc", ".pptx",
                          ".png", ".jpg", ".jpeg", ".html", ".epub", ".csv", ".xlsx"}

    class Handler(FileSystemEventHandler):
        def on_created(self, event):
            if event.is_directory:
                return
            path = Path(event.src_path)
            if path.suffix.lower() in WATCHED_EXTENSIONS:
                time.sleep(1.0)  # esperar que termine de escribir/copiar
                console.print(f"\n[cyan]Archivo detectado:[/cyan] {path.name}")
                _process_file(path)

    RAW_DIR.mkdir(exist_ok=True)
    observer = Observer()
    observer.schedule(Handler(), str(RAW_DIR), recursive=False)
    observer.start()
    console.print(Panel(
        f"[bold green]Vigilando:[/bold green] {RAW_DIR}\n"
        f"Formatos aceptados: .md .txt .pdf .docx .pptx .png .jpg .html .epub .csv\n"
        f"Arrastra cualquier archivo a raw/ → se convierte a Markdown automáticamente.\n"
        f"[dim]Ctrl+C para detener[/dim]",
        title="Second Brain — Watch Mode"
    ))
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

# ─── Comando: search ──────────────────────────────────────────────────────────

def cmd_search(query: str):
    """Busca en todas las notas del vault"""
    query_lower = query.lower()
    results = []

    for md_file in WIKI_DIR.rglob("*.md"):
        text = md_file.read_text(encoding="utf-8", errors="replace")
        if query_lower in text.lower():
            # Contar ocurrencias y extraer contexto
            lines = text.split("\n")
            matches = [(i+1, line.strip()) for i, line in enumerate(lines)
                      if query_lower in line.lower() and line.strip()]
            results.append((md_file, len(matches), matches[:2]))

    if not results:
        console.print(f"[yellow]Sin resultados para: '{query}'[/yellow]")
        return

    results.sort(key=lambda x: x[1], reverse=True)
    table = Table(title=f"Búsqueda: '{query}' — {len(results)} notas")
    table.add_column("Nota", style="cyan")
    table.add_column("Hits", style="yellow", justify="right")
    table.add_column("Contexto", style="dim")

    for md_file, hits, sample_lines in results[:15]:
        rel = str(md_file.relative_to(VAULT_PATH))
        ctx = sample_lines[0][1][:60] + "..." if sample_lines else ""
        table.add_row(rel, str(hits), ctx)

    console.print(table)

# ─── Comando: health ──────────────────────────────────────────────────────────

def cmd_health():
    """Verifica el estado del vault"""
    console.print(Panel("[bold]Second Brain — Health Check[/bold]", expand=False))

    all_notes = list(WIKI_DIR.rglob("*.md"))
    raw_files = list(RAW_DIR.glob("*.md")) + list(RAW_DIR.glob("*.txt")) if RAW_DIR.exists() else []

    # Contar por sección
    sections = {}
    for note in all_notes:
        section = note.parent.name
        sections[section] = sections.get(section, 0) + 1

    # Detectar notas sin frontmatter
    no_frontmatter = []
    stale_notes = []
    now_ts = datetime.now().timestamp()
    for note in all_notes:
        text = note.read_text(encoding="utf-8", errors="replace")
        if not text.startswith("---"):
            no_frontmatter.append(note.name)
        else:
            try:
                parts = text.split("---", 2)
                if len(parts) >= 3:
                    meta = yaml.safe_load(parts[1]) or {}
                    fecha_str = meta.get("fecha", "")
                    if fecha_str:
                        fecha = datetime.strptime(str(fecha_str), "%Y-%m-%d")
                        if (now_ts - fecha.timestamp()) > 30 * 86400:
                            stale_notes.append(note.name)
            except Exception:
                pass

    # Tabla resumen
    table = Table()
    table.add_column("Métrica", style="cyan")
    table.add_column("Valor", style="green")
    table.add_row("Total notas", str(len(all_notes)))
    table.add_row("Archivos en raw/ (sin procesar)", str(len(raw_files)))
    table.add_row("Sin frontmatter", str(len(no_frontmatter)))
    table.add_row("Notas > 30 días sin actualizar", str(len(stale_notes)))
    for section, count in sorted(sections.items()):
        table.add_row(f"  Sección: {section}", str(count))
    console.print(table)

    if raw_files:
        console.print(f"\n[yellow]⚠ {len(raw_files)} archivos en raw/ sin procesar[/yellow]")
        console.print("  Ejecuta: python3 scripts/second_brain.py process")

    if no_frontmatter:
        console.print(f"\n[yellow]⚠ Notas sin frontmatter: {', '.join(no_frontmatter[:5])}[/yellow]")

    console.print("\n[bold green]✓ Health check completado[/bold green]")

# ─── Comando: sync ────────────────────────────────────────────────────────────

def cmd_sync():
    """Sincroniza documentos clave de DOF-MESH docs/ → vault wiki/"""
    console.print(Panel("[bold]Sincronizando DOF-MESH docs/ → Obsidian vault[/bold]", expand=False))

    synced = 0
    for src_name, dest_path in DOF_SYNC_MAP.items():
        src = DOF_DOCS / src_name
        if not src.exists():
            console.print(f"  [yellow]~[/yellow] {src_name} — no encontrado en docs/")
            continue

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        src_text = src.read_text(encoding="utf-8", errors="replace")

        # Agregar frontmatter si no tiene
        if not src_text.startswith("---"):
            slug = slugify(src.stem)
            header = f"---\ntags: [dof-mesh, sincronizado]\nfecha: {now_str()}\nestado: sincronizado\nfuente: docs/{src_name}\n---\n\n"
            src_text = header + src_text

        dest_path.write_text(src_text, encoding="utf-8")
        console.print(f"  [green]✓[/green] {src_name} → {dest_path.relative_to(VAULT_PATH)}")
        synced += 1

    # Sync sessions ESTADO_ACTUAL
    estado_src = Path("/Users/jquiceva/equipo-de-agentes/docs/09_sessions/ESTADO_ACTUAL.md")
    if estado_src.exists():
        dest = WIKI_DIR / "DOF-MESH" / "estado-sesiones.md"
        text = estado_src.read_text(encoding="utf-8", errors="replace")
        if not text.startswith("---"):
            text = f"---\ntags: [dof-mesh, sesiones, estado]\nfecha: {now_str()}\nestado: sincronizado\nfuente: docs/09_sessions/ESTADO_ACTUAL.md\n---\n\n" + text
        dest.write_text(text, encoding="utf-8")
        console.print(f"  [green]✓[/green] ESTADO_ACTUAL.md → wiki/DOF-MESH/estado-sesiones.md")
        synced += 1

    console.print(f"\n[bold green]✓ Sincronizados {synced} documentos[/bold green]")

# ─── Comando: template ────────────────────────────────────────────────────────

def cmd_template(tipo: str = "nota"):
    """Crea plantillas en templates/"""
    templates = {
        "nota": """---
tags: []
fecha: {fecha}
estado: activo
---

# Título

## Resumen

## Detalles

## Ver también

""",
        "aprendizaje": """---
tags: [aprendizaje]
fecha: {fecha}
estado: activo
tipo: aprendizaje
---

# Aprendizaje: Título

## Qué aprendí

## Por qué importa

## Cómo aplicarlo

## Fuente

""",
        "proyecto": """---
tags: [proyecto]
fecha: {fecha}
estado: activo
tipo: proyecto
---

# Proyecto: Nombre

## Objetivo

## Stack técnico

## Estado actual

## Pendientes

## Recursos

""",
    }

    TEMPLATES_DIR = VAULT_PATH / "templates"
    TEMPLATES_DIR.mkdir(exist_ok=True)

    for name, content in templates.items():
        dest = TEMPLATES_DIR / f"{name}.md"
        dest.write_text(content.format(fecha=now_str()), encoding="utf-8")
        console.print(f"  [green]✓[/green] templates/{name}.md")

    console.print(f"\n[green]Plantillas creadas en templates/[/green]")

# ─── Entrypoint ───────────────────────────────────────────────────────────────

def print_help():
    console.print(Panel(
        "[bold cyan]Second Brain CLI — DOF Mesh Legion[/bold cyan]\n\n"
        "[bold]Comandos:[/bold]\n"
        "  [green]add[/green] 'título' --content 'texto' --tags tag1,tag2   Crea nota\n"
        "  [green]process[/green]                                             Procesa raw/\n"
        "  [green]watch[/green]                                               Vigila raw/ en tiempo real\n"
        "  [green]search[/green] 'query'                                     Busca en vault\n"
        "  [green]health[/green]                                              Estado del vault\n"
        "  [green]sync[/green]                                                Sync DOF-MESH docs/ → vault\n"
        "  [green]template[/green]                                            Genera plantillas\n",
        title="second_brain.py",
        expand=False
    ))

def main():
    args = sys.argv[1:]
    if not args:
        print_help()
        return

    cmd = args[0].lower()

    if cmd == "add":
        if len(args) < 2:
            console.print("[red]Uso: add 'título' --content 'texto' --tags tag1,tag2[/red]")
            return
        title = args[1]
        content = ""
        tags = ""
        section = ""
        i = 2
        while i < len(args):
            if args[i] == "--content" and i+1 < len(args):
                content = args[i+1]; i += 2
            elif args[i] == "--tags" and i+1 < len(args):
                tags = args[i+1]; i += 2
            elif args[i] == "--section" and i+1 < len(args):
                section = args[i+1]; i += 2
            else:
                i += 1
        cmd_add(title, content, tags, section)

    elif cmd == "process":
        cmd_process()

    elif cmd == "watch":
        cmd_watch()

    elif cmd == "search":
        if len(args) < 2:
            console.print("[red]Uso: search 'query'[/red]")
            return
        cmd_search(" ".join(args[1:]))

    elif cmd == "health":
        cmd_health()

    elif cmd == "sync":
        cmd_sync()

    elif cmd == "template":
        tipo = args[1] if len(args) > 1 else "nota"
        cmd_template(tipo)

    else:
        console.print(f"[red]Comando desconocido: {cmd}[/red]")
        print_help()

if __name__ == "__main__":
    main()
