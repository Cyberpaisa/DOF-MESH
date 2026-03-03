#!/usr/bin/env python3
"""
CrewAI Pro — 8 Agentes Especializados + Mission Control
Cyber Paisa / Enigma Group
6 proveedores gratuitos — Memoria + Planning + Pydantic + Multi-proyecto

Uso:
    python main.py                                              (interactivo)
    python main.py --mode research --task "Mi idea"
    python main.py --mode code-review --path ./proyecto
    python main.py --mode data --file datos.xlsx
    python main.py --mode full-mvp --task "App DeFi"
    python main.py --mode database --connection "postgresql://..."
    python main.py --mode grant-hunt --project "FLARE" --task "Grants de AI en Avalanche"
    python main.py --mode content --project "FLARE" --task "Hilo Twitter sobre progreso"
    python main.py --mode daily-ops
    python main.py --mode weekly-report --project "FLARE"
    python main.py --mode dashboard
    python main.py --mode telegram
    python main.py --mode voice
"""

import os
import sys
import json
import argparse
import subprocess
import threading
from datetime import datetime

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from rich.table import Table

load_dotenv()
console = Console()


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def show_banner():
    console.print(Panel.fit(
        "[bold cyan]CrewAI Pro — 8 Agentes + Kernel Boot[/bold cyan]\n"
        "[dim]Cyber Paisa / Enigma Group[/dim]\n"
        "[dim]8 proveedores LLM — Logging — Memory — SOUL.md[/dim]",
        border_style="cyan",
    ))


def show_status():
    from llm_config import validate_keys
    try:
        status = validate_keys()
    except ValueError as e:
        console.print(f"\n[red]{e}[/red]")
        sys.exit(1)

    table = Table(title="API Keys")
    table.add_column("Proveedor", style="cyan")
    table.add_column("Estado")
    table.add_column("Uso")

    ok = "[green]OK[/green]"
    off = "[dim]--[/dim]"
    table.add_row("Groq", ok if status["groq"] else "[red]FALTA[/red]", "Llama 3.3 (Researcher), Qwen3-32B (Organizer)")
    table.add_row("NVIDIA NIM", ok if status["nvidia"] else off, "Kimi K2.5 (Architect), Qwen3.5-397B (Strategist)")
    table.add_row("Cerebras", ok if status["cerebras"] else off, "GPT-OSS 120B (Data, QA, Verifier)")
    table.add_row("Gemini", ok if status["gemini"] else off, "2.5 Flash (backup, 20 req/día free)")
    table.add_row("OpenRouter", ok if status["openrouter"] else off, "Hermes 405B (backup)")
    table.add_row("SambaNova", ok if status["sambanova"] else off, "DeepSeek V3.2 (backup)")
    table.add_row("Zhipu AI", ok if status.get("zhipu") else off, "GLM-4.7-Flash 128K (Strategy, Narrative)")
    table.add_row("", "", "")
    table.add_row("Serper", ok if status.get("serper") else off, "Google Search (2,500/mes)")
    table.add_row("Tavily", ok if status.get("tavily") else off, "AI Search (1,000/mes)")
    console.print(table)


def show_agents():
    table = Table(title="8 Agentes")
    table.add_column("#", width=3)
    table.add_column("Agente", style="bold")
    table.add_column("Tools")
    table.add_column("Modelo")

    table.add_row("1", "Code Architect", "analyze_code, list_files, tech_stack, write_file, exec_python, run_cmd, git", "Kimi K2.5 (NVIDIA) > Kimi K2 (Groq)")
    table.add_row("2", "Research Analyst", "web_search, web_research + pre-research", "Llama 3.3 (Groq) > DeepSeek V3.2 (NV)")
    table.add_row("3", "MVP Strategist", "-- (SOUL.md DeFi rules)", "Qwen3.5-397B (NV) > GLM-4.7 (Zhipu) > Groq")
    table.add_row("4", "Data Engineer", "read_excel, query_db, analyze_data", "GPT-OSS 120B (Cerebras) > GPT-OSS (Groq)")
    table.add_row("5", "Project Organizer", "scan_dir, organize, list_files", "Qwen3-32B (Groq) > GLM-4.7 (Zhipu)")
    table.add_row("6", "QA Reviewer", "analyze_code, web_search", "GPT-OSS 120B (Cerebras) > Llama 3.3 (Groq)")
    table.add_row("7", "Verifier", "web_search", "GPT-OSS 120B (Cerebras) > Llama 3.3 (Groq)")
    table.add_row("8", "Narrative & Growth", "web_search, web_research", "GLM-4.7 (Zhipu) > DeepSeek V3.2 (NV) > Groq")
    console.print(table)

    console.print("\n[bold green]Optimizaciones activas:[/bold green]")
    console.print("  [green]>[/green] Reglas constitucionales (calidad de output)")
    console.print("  [green]>[/green] Outputs Pydantic (estructura garantizada)")
    console.print("  [green]>[/green] SOUL.md por agente (personalidad)")
    console.print("  [green]>[/green] Web search: Serper > Tavily > DuckDuckGo")
    console.print("  [green]>[/green] Code execution (write, exec, run, git)")
    console.print("  [green]>[/green] Agente Verifier (#7) (fact-checking)")
    console.print("  [green]>[/green] Agente Narrative (#8) (grants, contenido, growth)")
    console.print("  [green]>[/green] Multi-proyecto (--project)")


def show_projects():
    """Muestra los proyectos registrados en projects.yaml."""
    import yaml
    projects_path = os.path.join(os.path.dirname(__file__), "config", "projects.yaml")
    if not os.path.exists(projects_path):
        console.print("[yellow]No hay projects.yaml configurado[/yellow]")
        return
    with open(projects_path, "r") as f:
        data = yaml.safe_load(f)
    if not data or "projects" not in data:
        console.print("[yellow]No hay proyectos registrados[/yellow]")
        return

    table = Table(title="Proyectos Registrados")
    table.add_column("Nombre", style="bold cyan")
    table.add_column("Ecosistema")
    table.add_column("Estado")
    table.add_column("Equipo")
    for p in data["projects"]:
        status_style = "green" if p.get("status") == "active" else "yellow"
        table.add_row(
            p["name"],
            p.get("ecosystem", "?"),
            f"[{status_style}]{p.get('status', '?')}[/{status_style}]",
            ", ".join(p.get("team", [])) or "--",
        )
    console.print(table)


# ═══════════════════════════════════════════════════════
# KERNEL BOOT — Fase 1
# ═══════════════════════════════════════════════════════

def kernel_boot():
    """Fase 1: Lee estado, logs recientes, propone bloques de trabajo."""
    console.print("\n[bold yellow]KERNEL BOOT[/bold yellow]")

    # 1. Verificar SYSTEM.md
    system_path = os.path.join(BASE_DIR, "SYSTEM.md")
    if os.path.exists(system_path):
        console.print("  [green]>[/green] SYSTEM.md cargado")
    else:
        console.print("  [yellow]![/yellow] SYSTEM.md no encontrado")

    # 2. Leer _index.md (estado)
    index_path = os.path.join(BASE_DIR, "_index.md")
    if os.path.exists(index_path):
        with open(index_path, "r") as f:
            index_content = f.read()
        # Extraer última fecha
        for line in index_content.split("\n"):
            if "**Fecha:**" in line:
                console.print(f"  [green]>[/green] Última sesión: {line.split('**Fecha:**')[1].strip()}")
                break
    else:
        console.print("  [yellow]![/yellow] _index.md no encontrado — primera ejecución")

    # 3. Leer últimas ejecuciones del log
    log_path = os.path.join(BASE_DIR, "logs", "execution_log.jsonl")
    recent_runs = []
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            lines = f.readlines()
        for line in lines[-10:]:  # últimas 10
            try:
                recent_runs.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                continue

    if recent_runs:
        console.print(f"  [green]>[/green] {len(recent_runs)} ejecuciones recientes")
        # Mostrar últimas 3
        table = Table(title="Últimas Ejecuciones", show_lines=False, padding=(0, 1))
        table.add_column("Fecha", style="dim", width=16)
        table.add_column("Crew", style="cyan")
        table.add_column("Estado")
        table.add_column("Tiempo", justify="right")
        for run in recent_runs[-3:]:
            ts = run.get("timestamp", "?")[:16]
            status_str = "[green]OK[/green]" if run.get("status") == "success" else "[red]ERROR[/red]"
            duration = f"{run.get('duration_sec', '?')}s"
            table.add_row(ts, run.get("crew", "?"), status_str, duration)
        console.print(table)

        # Calcular métricas
        successes = sum(1 for r in recent_runs if r.get("status") == "success")
        errors = sum(1 for r in recent_runs if r.get("status") == "error")
        if recent_runs:
            avg_time = sum(r.get("duration_sec", 0) for r in recent_runs) / len(recent_runs)
            console.print(f"  [dim]Tasa éxito: {successes}/{len(recent_runs)} | Tiempo promedio: {avg_time:.0f}s[/dim]")
    else:
        console.print("  [dim]Sin ejecuciones previas — sistema limpio[/dim]")

    # 4. Proponer bloques de trabajo
    console.print("\n[bold]Bloques sugeridos:[/bold]")
    suggestions = _suggest_work_blocks(recent_runs)
    for i, s in enumerate(suggestions, 1):
        console.print(f"  [cyan]{i}.[/cyan] {s}")

    return recent_runs


def _suggest_work_blocks(recent_runs: list) -> list:
    """Propone 1-3 bloques de trabajo basado en historial."""
    suggestions = []
    crews_run = {r.get("crew") for r in recent_runs}
    errors = [r for r in recent_runs if r.get("status") == "error"]

    # Si hay errores recientes, sugerir re-run
    if errors:
        last_error = errors[-1]
        suggestions.append(f"Re-ejecutar {last_error.get('crew', '?')} (falló: {last_error.get('error', '?')[:60]})")

    # Sugerir crews no ejecutados recientemente
    all_crews = {"research", "code_review", "grant_hunt", "content", "daily_ops", "weekly_report", "build_project"}
    unused = all_crews - crews_run
    if unused:
        suggestions.append(f"Probar crew no usado: {', '.join(list(unused)[:3])}")

    # Siempre sugerir daily-ops si no se corrió hoy
    today = datetime.now().strftime("%Y-%m-%d")
    today_runs = [r for r in recent_runs if r.get("timestamp", "").startswith(today)]
    if not any(r.get("crew") == "daily_ops" for r in today_runs):
        suggestions.append("Ejecutar Daily Ops (rutina matutina)")

    if not suggestions:
        suggestions.append("Sistema listo — elige un crew del menú")

    return suggestions[:3]


# ═══════════════════════════════════════════════════════
# SESSION LIFECYCLE
# ═══════════════════════════════════════════════════════

def save_session_snapshot(runs_this_session: list):
    """Guarda snapshot de la sesión al cerrar."""
    snapshot_path = os.path.join(BASE_DIR, "memory", "last_session.md")
    index_path = os.path.join(BASE_DIR, "_index.md")
    now = datetime.now()

    # Generar snapshot
    snapshot = f"# Última Sesión\n"
    snapshot += f"- **Fecha:** {now:%Y-%m-%d %H:%M}\n"
    snapshot += f"- **Crews ejecutados:** {len(runs_this_session)}\n\n"

    if runs_this_session:
        snapshot += "## Ejecuciones\n"
        for run in runs_this_session:
            status = run.get("status", "?")
            crew = run.get("crew", "?")
            duration = run.get("duration_sec", "?")
            snapshot += f"- {crew}: {status} ({duration}s)\n"
    else:
        snapshot += "_No se ejecutaron crews en esta sesión._\n"

    os.makedirs(os.path.dirname(snapshot_path), exist_ok=True)
    with open(snapshot_path, "w") as f:
        f.write(snapshot)

    # Actualizar _index.md
    # Leer logs completos para métricas
    log_path = os.path.join(BASE_DIR, "logs", "execution_log.jsonl")
    all_runs = []
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            for line in f:
                try:
                    all_runs.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue

    total = len(all_runs)
    successes = sum(1 for r in all_runs if r.get("status") == "success")
    avg_time = sum(r.get("duration_sec", 0) for r in all_runs) / max(total, 1)

    # Crew más usado
    from collections import Counter
    crew_counts = Counter(r.get("crew", "?") for r in all_runs)
    most_used = crew_counts.most_common(1)[0] if crew_counts else ("—", 0)

    # Últimas 5 ejecuciones para mostrar
    recent_lines = ""
    for r in all_runs[-5:]:
        ts = r.get("timestamp", "?")[:16]
        status = r.get("status", "?")
        crew = r.get("crew", "?")
        recent_lines += f"- `{ts}` | {crew} | {status} | {r.get('duration_sec', '?')}s\n"

    index = f"""# _index — Estado del Sistema
# Auto-actualizado por Kernel Boot

## Última Sesión
- **Fecha:** {now:%Y-%m-%d %H:%M}
- **Crews ejecutados:** {len(runs_this_session)}

## Últimas Ejecuciones
{recent_lines if recent_lines else '_Sin ejecuciones._'}

## Métricas del Sistema
- **Total ejecuciones:** {total}
- **Tasa de éxito:** {successes}/{total} ({successes/max(total,1)*100:.0f}%)
- **Crew más usado:** {most_used[0]} ({most_used[1]}x)
- **Tiempo promedio:** {avg_time:.0f}s
"""
    with open(index_path, "w") as f:
        f.write(index)

    console.print(f"\n[dim]Sesión guardada en memory/last_session.md[/dim]")
    console.print(f"[dim]_index.md actualizado[/dim]")


LOG_FILE = os.path.join(os.path.dirname(__file__), "logs", "execution_log.jsonl")


def _log_execution(entry: dict):
    """Append una línea JSON al log de ejecuciones."""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


COOLDOWN_SEC = 15  # Cooldown entre crew runs para evitar rate limits


# ── Supervisor-integrated crew execution ──
from core.crew_runner import run_crew as run_crew_supervised


def run_crew(crew, mode_name: str, project: str | None = None, max_retries: int = 3):
    """Ejecuta un crew con supervisor + governance + tracing completo.

    Mantiene la firma pública original. Internamente delega a
    core.crew_runner.run_crew (supervisor, governance, checkpointing, tracing).
    Preserva: Rich console output, archivo .md, execution_log.jsonl.
    """
    out_dir = f"output/{project}" if project else "output"
    os.makedirs(out_dir, exist_ok=True)

    project_label = f" [{project}]" if project else ""
    agents_used = [a.role for a in crew.agents]
    console.print(f"\n[bold green]Ejecutando {mode_name}{project_label}...[/bold green]")
    console.print(f"[dim]Agentes: {', '.join(agents_used)}[/dim]")
    console.print(f"[dim]Supervisor: ON | Governance: ON | Tracing: ON[/dim]\n")
    start = datetime.now()

    # Extraer input_text del primer task del crew
    input_text = ""
    if hasattr(crew, "tasks") and crew.tasks:
        input_text = getattr(crew.tasks[0], "description", "")

    log_entry = {
        "timestamp": start.isoformat(),
        "crew": mode_name,
        "project": project,
        "agents": agents_used,
        "agents_count": len(agents_used),
        "status": "running",
        "duration_sec": 0,
        "output_path": None,
        "error": None,
    }

    # Llamar al orquestador completo
    result = run_crew_supervised(
        crew_name=mode_name,
        crew=crew,
        input_text=input_text,
        max_retries=max_retries,
    )

    elapsed = datetime.now() - start

    if result["status"] == "error":
        log_entry.update({
            "status": "error",
            "duration_sec": round(elapsed.total_seconds(), 1),
            "error": result.get("error", "unknown"),
        })
        _log_execution(log_entry)
        console.print(f"\n[red]Error: {result.get('error', 'unknown')}[/red]")
        if result.get("retries", 0) > 0:
            console.print(f"[dim]Reintentos usados: {result['retries']}[/dim]")
        return log_entry

    # Escribir output a archivo .md
    output_text = result.get("output", "")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = f"{out_dir}/{mode_name}_{ts}.md"

    sup = result.get("supervisor")
    gov = result.get("governance")
    sup_line = f"**Supervisor:** {sup['decision']} (score: {sup['score']:.1f})" if sup else "**Supervisor:** skipped"
    gov_line = f"**Governance:** {'PASS' if gov and gov['passed'] else 'FAIL'}" if gov else "**Governance:** N/A"

    with open(out, "w") as f:
        f.write(
            f"# {mode_name}{project_label}\n"
            f"**Fecha:** {datetime.now():%Y-%m-%d %H:%M}\n"
            f"**Tiempo:** {elapsed}\n"
            f"**Agentes:** {', '.join(agents_used)}\n"
            f"**Run ID:** {result.get('run_id', 'N/A')}\n"
            f"{sup_line}\n"
            f"{gov_line}\n\n---\n\n{output_text}"
        )

    status_mapped = "success" if result["status"] == "ok" else result["status"]
    log_entry.update({
        "status": status_mapped,
        "duration_sec": round(elapsed.total_seconds(), 1),
        "output_path": out,
        "run_id": result.get("run_id"),
        "supervisor_score": sup["score"] if sup else None,
        "supervisor_decision": sup["decision"] if sup else None,
        "governance_passed": gov["passed"] if gov else None,
        "retries": result.get("retries", 0),
        "trace_path": result.get("trace_path"),
    })
    _log_execution(log_entry)

    # Rich console output
    sup_info = f" | Supervisor: {sup['decision']} ({sup['score']:.1f})" if sup else ""
    gov_info = f" | Governance: {'PASS' if gov and gov['passed'] else 'FAIL'}" if gov else ""
    console.print(Panel(
        f"[green]Completado en {elapsed}[/green]{sup_info}{gov_info}\n"
        f"Guardado en: [cyan]{out}[/cyan]",
        border_style="green",
    ))
    console.print(f"\n{output_text}")
    return log_entry


def run_interactive():
    show_banner()
    show_status()
    show_agents()
    show_projects()

    # KERNEL BOOT — Fase 1
    recent_runs = kernel_boot()
    session_runs = []  # tracking de esta sesión

    console.print("\n[bold]Que quieres hacer?[/bold]\n")
    console.print("  [cyan]1.[/cyan]  Investigar y validar una idea")
    console.print("  [cyan]2.[/cyan]  Revisar codigo de un proyecto")
    console.print("  [cyan]3.[/cyan]  Analizar datos (Excel/CSV)")
    console.print("  [cyan]4.[/cyan]  Analizar base de datos")
    console.print("  [cyan]5.[/cyan]  MVP completo (research + plan + arquitectura)")
    console.print("  [green]6.[/green]  [bold]Enigma Audit[/bold] (auditar agente/scanner/DB)")
    console.print("  [green]7.[/green]  [bold]Grant Hunt[/bold] (buscar grants y oportunidades)")
    console.print("  [green]8.[/green]  [bold]Contenido[/bold] (threads, blogs, pitches, narrativas)")
    console.print("  [green]9.[/green]  [bold]Daily Ops[/bold] (rutina matutina COO)")
    console.print("  [green]10.[/green] [bold]Weekly Report[/bold] (preparacion reunion semanal)")
    console.print("  [cyan]11.[/cyan] Lanzar Dashboard (Streamlit)")
    console.print("  [cyan]12.[/cyan] Lanzar Telegram Bot")
    console.print("  [green]13.[/green] [bold]Modo Voz[/bold] (habla natural desde tu Mac)")
    console.print("  [green]14.[/green] [bold]Build Project[/bold] (genera proyecto con codigo real)")
    console.print("  [magenta]15.[/magenta] [bold]A2A Server[/bold] (exponer agentes como servicio)")
    console.print("  [cyan]0.[/cyan]  Salir")

    choice = IntPrompt.ask(
        "\nOpcion",
        choices=["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15"],
    )

    if choice == 0:
        save_session_snapshot(session_runs)
        sys.exit(0)

    from crew import (
        create_research_crew, create_code_review_crew,
        create_data_analysis_crew, create_database_crew, create_full_mvp_crew,
        create_enigma_audit_crew, create_grant_hunt_crew, create_content_crew,
        create_daily_ops_crew, create_weekly_report_crew, create_build_project_crew,
    )

    # Preguntar proyecto si aplica
    project = None
    if choice in (1, 5, 7, 8, 10):
        proj_input = Prompt.ask("Proyecto (Enter para modo general)", default="")
        project = proj_input if proj_input else None

    result = None
    if choice == 1:
        topic = Prompt.ask("Describe tu idea")
        result = run_crew(create_research_crew(topic), "research", project)
    elif choice == 2:
        path = Prompt.ask("Ruta al proyecto", default=".")
        result = run_crew(create_code_review_crew(path), "code_review")
    elif choice == 3:
        f = Prompt.ask("Ruta al archivo Excel/CSV")
        result = run_crew(create_data_analysis_crew(f), "data_analysis")
    elif choice == 4:
        conn = Prompt.ask(
            "Connection string",
            default=os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/db"),
        )
        result = run_crew(create_database_crew(conn), "database")
    elif choice == 5:
        topic = Prompt.ask("Describe tu idea de MVP")
        result = run_crew(create_full_mvp_crew(topic), "full_mvp", project)
    elif choice == 6:
        console.print("\n[bold green]Enigma Audit — Que auditar?[/bold green]")
        console.print("  [cyan]a.[/cyan] Un agente (URL)")
        console.print("  [cyan]b.[/cyan] La base de datos Enigma")
        console.print("  [cyan]c.[/cyan] El codigo del scanner")
        sub = Prompt.ask("Opcion", choices=["a", "b", "c"])
        if sub == "a":
            url = Prompt.ask("URL del agente", default="https://apex-arbitrage-agent-production.up.railway.app")
            result = run_crew(create_enigma_audit_crew(url), "enigma_agent_audit")
        elif sub == "b":
            result = run_crew(create_enigma_audit_crew("database"), "enigma_db_audit")
        elif sub == "c":
            path = Prompt.ask("Ruta al scanner", default="/Users/jquiceva/Enigma")
            result = run_crew(create_enigma_audit_crew(path), "enigma_code_audit")
    elif choice == 7:
        task = Prompt.ask("Que tipo de grants buscas?", default="Grants de AI e infraestructura Web3")
        result = run_crew(create_grant_hunt_crew(task, project), "grant_hunt", project)
    elif choice == 8:
        console.print("\nTipos: thread, blog, update, pitch, narrative, tokenomics")
        task = Prompt.ask("Describe el contenido que necesitas")
        result = run_crew(create_content_crew(task, project), "content", project)
    elif choice == 9:
        file_path = Prompt.ask("Archivo Excel para metricas (Enter para omitir)", default="")
        result = run_crew(
            create_daily_ops_crew(file_path if file_path else None),
            "daily_ops",
        )
    elif choice == 10:
        file_path = Prompt.ask("Archivo Excel para metricas (Enter para omitir)", default="")
        result = run_crew(
            create_weekly_report_crew(project, file_path if file_path else None),
            "weekly_report",
            project,
        )
    elif choice == 11:
        launch_dashboard()
    elif choice == 12:
        launch_telegram()
    elif choice == 13:
        launch_voice()
    elif choice == 14:
        desc = Prompt.ask("Describe el proyecto a generar")
        name = Prompt.ask("Nombre del proyecto (carpeta)", default="nuevo_proyecto")
        result = run_crew(create_build_project_crew(desc, name), "build_project")
    elif choice == 15:
        launch_a2a_server()

    # Trackear ejecución en sesión
    if result:
        session_runs.append(result)

    # Guardar snapshot al terminar
    save_session_snapshot(session_runs)


def run_cli(args):
    show_banner()
    show_status()

    from crew import (
        create_research_crew, create_code_review_crew,
        create_data_analysis_crew, create_database_crew, create_full_mvp_crew,
        create_enigma_audit_crew, create_grant_hunt_crew, create_content_crew,
        create_daily_ops_crew, create_weekly_report_crew, create_build_project_crew,
    )

    project = args.project
    task = args.task or args.topic or ""

    if args.mode == "research":
        if not task:
            console.print("[red]--task requerido[/red]"); sys.exit(1)
        run_crew(create_research_crew(task), "research", project)
    elif args.mode == "code-review":
        run_crew(create_code_review_crew(args.path or "."), "code_review")
    elif args.mode == "data":
        if not args.file:
            console.print("[red]--file requerido[/red]"); sys.exit(1)
        run_crew(create_data_analysis_crew(args.file), "data_analysis")
    elif args.mode == "database":
        conn = args.connection or os.getenv("DATABASE_URL")
        if not conn:
            console.print("[red]--connection o DATABASE_URL requerido[/red]"); sys.exit(1)
        run_crew(create_database_crew(conn), "database")
    elif args.mode == "full-mvp":
        if not task:
            console.print("[red]--task requerido[/red]"); sys.exit(1)
        run_crew(create_full_mvp_crew(task), "full_mvp", project)
    elif args.mode == "enigma-audit":
        target = task or args.path or "database"
        run_crew(create_enigma_audit_crew(target), "enigma_audit")
    elif args.mode == "grant-hunt":
        run_crew(create_grant_hunt_crew(task, project), "grant_hunt", project)
    elif args.mode == "content":
        if not task:
            console.print("[red]--task requerido[/red]"); sys.exit(1)
        run_crew(create_content_crew(task, project), "content", project)
    elif args.mode == "daily-ops":
        run_crew(create_daily_ops_crew(args.file), "daily_ops")
    elif args.mode == "weekly-report":
        run_crew(
            create_weekly_report_crew(project, args.file),
            "weekly_report",
            project,
        )
    elif args.mode == "dashboard":
        launch_dashboard()
    elif args.mode == "telegram":
        launch_telegram()
    elif args.mode == "voice":
        launch_voice()
    elif args.mode == "build":
        if not task:
            console.print("[red]--task requerido (descripcion del proyecto)[/red]"); sys.exit(1)
        name = args.project or "nuevo_proyecto"
        run_crew(create_build_project_crew(task, name), "build_project")
    elif args.mode == "a2a-server":
        launch_a2a_server()
    elif args.mode == "all":
        launch_all()


def launch_dashboard():
    """Lanza Streamlit dashboard."""
    dashboard_path = os.path.join(os.path.dirname(__file__), "interfaces", "streamlit_dashboard.py")
    if not os.path.exists(dashboard_path):
        console.print("[red]interfaces/streamlit_dashboard.py no encontrado[/red]")
        return
    console.print("[green]Lanzando Dashboard en http://localhost:8501 ...[/green]")
    subprocess.run(["streamlit", "run", dashboard_path, "--server.port", "8501"])


def launch_telegram():
    """Lanza Telegram bot."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        console.print("[red]TELEGRAM_BOT_TOKEN no configurado en .env[/red]")
        return
    console.print("[green]Lanzando Telegram Bot...[/green]")
    from interfaces.telegram_bot import start_bot
    start_bot()


def launch_voice():
    """Lanza modo voz continuo desde Mac."""
    console.print("[green]Lanzando Modo Voz...[/green]")
    from interfaces.voice_interface import start_voice_loop
    start_voice_loop()


def launch_a2a_server():
    """Lanza A2A Server — expone crews como servicios descubribles."""
    console.print("[magenta]Lanzando A2A Server...[/magenta]")
    console.print("[dim]Otros agentes pueden descubrirte en http://localhost:8000/.well-known/agent-card.json[/dim]")
    from a2a_server import start_server
    start_server(port=8000)


def launch_all():
    """Lanza dashboard + telegram en paralelo."""
    console.print("[green]Lanzando Mission Control completo...[/green]")

    # Telegram en thread
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if token:
        t = threading.Thread(target=launch_telegram, daemon=True)
        t.start()
        console.print("[green]Telegram Bot iniciado en background[/green]")
    else:
        console.print("[yellow]TELEGRAM_BOT_TOKEN no configurado, omitiendo[/yellow]")

    # Dashboard en foreground (bloquea)
    launch_dashboard()


def main():
    parser = argparse.ArgumentParser(description="CrewAI Pro — 8 Agentes + Mission Control")
    parser.add_argument(
        "--mode",
        choices=[
            "research", "code-review", "data", "database", "full-mvp",
            "enigma-audit", "grant-hunt", "content", "daily-ops",
            "weekly-report", "build", "dashboard", "telegram", "voice", "a2a-server", "all",
        ],
    )
    parser.add_argument("--task", help="Descripcion de la tarea")
    parser.add_argument("--topic", help="Alias de --task (compatibilidad)")
    parser.add_argument("--project", help="Nombre del proyecto (de projects.yaml)")
    parser.add_argument("--path", help="Ruta a proyecto/directorio")
    parser.add_argument("--file", help="Ruta a archivo Excel/CSV")
    parser.add_argument("--connection", help="Connection string de base de datos")
    args = parser.parse_args()

    if args.mode:
        run_cli(args)
    else:
        run_interactive()


if __name__ == "__main__":
    main()
