#!/usr/bin/env python3
"""
CrewAI Pro — 8 Specialized Agents + Mission Control
Cyber Paisa / Enigma Group
6 free-tier providers — Memory + Planning + Pydantic + Multi-project

Usage:
    python main.py                                              (interactive)
    python main.py --mode research --task "My idea"
    python main.py --mode code-review --path ./project
    python main.py --mode data --file data.xlsx
    python main.py --mode full-mvp --task "DeFi App"
    python main.py --mode database --connection "postgresql://..."
    python main.py --mode grant-hunt --project "FLARE" --task "AI grants on Avalanche"
    python main.py --mode content --project "FLARE" --task "Twitter thread on progress"
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
        "[bold cyan]CrewAI Pro — 8 Agents + Kernel Boot[/bold cyan]\n"
        "[dim]Cyber Paisa / Enigma Group[/dim]\n"
        "[dim]8 LLM providers — Logging — Memory — SOUL.md[/dim]",
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
    table.add_column("Provider", style="cyan")
    table.add_column("Status")
    table.add_column("Usage")

    ok = "[green]OK[/green]"
    off = "[dim]--[/dim]"
    table.add_row("Groq", ok if status["groq"] else "[red]MISSING[/red]", "Llama 3.3 (Researcher), Qwen3-32B (Organizer)")
    table.add_row("NVIDIA NIM", ok if status["nvidia"] else off, "Kimi K2.5 (Architect), Qwen3.5-397B (Strategist)")
    table.add_row("Cerebras", ok if status["cerebras"] else off, "GPT-OSS 120B (Data, QA, Verifier)")
    table.add_row("Gemini", ok if status["gemini"] else off, "2.5 Flash (backup, 20 req/day free)")
    table.add_row("OpenRouter", ok if status["openrouter"] else off, "Hermes 405B (backup)")
    table.add_row("SambaNova", ok if status["sambanova"] else off, "DeepSeek V3.2 (backup)")
    table.add_row("Zhipu AI", ok if status.get("zhipu") else off, "GLM-4.7-Flash 128K (Strategy, Narrative)")
    table.add_row("", "", "")
    table.add_row("Serper", ok if status.get("serper") else off, "Google Search (2,500/month)")
    table.add_row("Tavily", ok if status.get("tavily") else off, "AI Search (1,000/month)")
    console.print(table)


def show_agents():
    table = Table(title="8 Agents")
    table.add_column("#", width=3)
    table.add_column("Agent", style="bold")
    table.add_column("Tools")
    table.add_column("Model")

    table.add_row("1", "Code Architect", "analyze_code, list_files, tech_stack, write_file, exec_python, run_cmd, git", "Kimi K2.5 (NVIDIA) > Kimi K2 (Groq)")
    table.add_row("2", "Research Analyst", "web_search, web_research + pre-research", "Llama 3.3 (Groq) > DeepSeek V3.2 (NV)")
    table.add_row("3", "MVP Strategist", "-- (SOUL.md DeFi rules)", "Qwen3.5-397B (NV) > GLM-4.7 (Zhipu) > Groq")
    table.add_row("4", "Data Engineer", "read_excel, query_db, analyze_data", "GPT-OSS 120B (Cerebras) > GPT-OSS (Groq)")
    table.add_row("5", "Project Organizer", "scan_dir, organize, list_files", "Qwen3-32B (Groq) > GLM-4.7 (Zhipu)")
    table.add_row("6", "QA Reviewer", "analyze_code, web_search", "GPT-OSS 120B (Cerebras) > Llama 3.3 (Groq)")
    table.add_row("7", "Verifier", "web_search", "GPT-OSS 120B (Cerebras) > Llama 3.3 (Groq)")
    table.add_row("8", "Narrative & Growth", "web_search, web_research", "GLM-4.7 (Zhipu) > DeepSeek V3.2 (NV) > Groq")
    console.print(table)

    console.print("\n[bold green]Active optimizations:[/bold green]")
    console.print("  [green]>[/green] Constitutional rules (output quality)")
    console.print("  [green]>[/green] Pydantic outputs (guaranteed structure)")
    console.print("  [green]>[/green] SOUL.md per agent (personality)")
    console.print("  [green]>[/green] Web search: Serper > Tavily > DuckDuckGo")
    console.print("  [green]>[/green] Code execution (write, exec, run, git)")
    console.print("  [green]>[/green] Verifier agent (#7) (fact-checking)")
    console.print("  [green]>[/green] Narrative agent (#8) (grants, content, growth)")
    console.print("  [green]>[/green] Multi-project (--project)")


def show_projects():
    """Show registered projects from projects.yaml."""
    import yaml
    projects_path = os.path.join(os.path.dirname(__file__), "config", "projects.yaml")
    if not os.path.exists(projects_path):
        console.print("[yellow]No projects.yaml configured[/yellow]")
        return
    with open(projects_path, "r") as f:
        data = yaml.safe_load(f)
    if not data or "projects" not in data:
        console.print("[yellow]No registered projects[/yellow]")
        return

    table = Table(title="Registered Projects")
    table.add_column("Name", style="bold cyan")
    table.add_column("Ecosystem")
    table.add_column("Status")
    table.add_column("Team")
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
    """Phase 1: Read state, recent logs, propose work blocks."""
    console.print("\n[bold yellow]KERNEL BOOT[/bold yellow]")

    # 1. Check SYSTEM.md
    system_path = os.path.join(BASE_DIR, "SYSTEM.md")
    if os.path.exists(system_path):
        console.print("  [green]>[/green] SYSTEM.md loaded")
    else:
        console.print("  [yellow]![/yellow] SYSTEM.md not found")

    # 2. Read _index.md (state)
    index_path = os.path.join(BASE_DIR, "_index.md")
    if os.path.exists(index_path):
        with open(index_path, "r") as f:
            index_content = f.read()
        # Extract last date
        for line in index_content.split("\n"):
            if "**Date:**" in line or "**Fecha:**" in line:
                date_key = "**Date:**" if "**Date:**" in line else "**Fecha:**"
                console.print(f"  [green]>[/green] Last session: {line.split(date_key)[1].strip()}")
                break
    else:
        console.print("  [yellow]![/yellow] _index.md not found — first run")

    # 3. Read recent execution logs
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
        console.print(f"  [green]>[/green] {len(recent_runs)} recent executions")
        # Show last 3
        table = Table(title="Recent Executions", show_lines=False, padding=(0, 1))
        table.add_column("Date", style="dim", width=16)
        table.add_column("Crew", style="cyan")
        table.add_column("Status")
        table.add_column("Time", justify="right")
        for run in recent_runs[-3:]:
            ts = run.get("timestamp", "?")[:16]
            status_str = "[green]OK[/green]" if run.get("status") == "success" else "[red]ERROR[/red]"
            duration = f"{run.get('duration_sec', '?')}s"
            table.add_row(ts, run.get("crew", "?"), status_str, duration)
        console.print(table)

        # Calculate metrics
        successes = sum(1 for r in recent_runs if r.get("status") == "success")
        errors = sum(1 for r in recent_runs if r.get("status") == "error")
        if recent_runs:
            avg_time = sum(r.get("duration_sec", 0) for r in recent_runs) / len(recent_runs)
            console.print(f"  [dim]Success rate: {successes}/{len(recent_runs)} | Avg time: {avg_time:.0f}s[/dim]")
    else:
        console.print("  [dim]No previous executions — clean system[/dim]")

    # 4. Suggest work blocks
    console.print("\n[bold]Suggested blocks:[/bold]")
    suggestions = _suggest_work_blocks(recent_runs)
    for i, s in enumerate(suggestions, 1):
        console.print(f"  [cyan]{i}.[/cyan] {s}")

    return recent_runs


def _suggest_work_blocks(recent_runs: list) -> list:
    """Propose 1-3 work blocks based on history."""
    suggestions = []
    crews_run = {r.get("crew") for r in recent_runs}
    errors = [r for r in recent_runs if r.get("status") == "error"]

    # If recent errors, suggest re-run
    if errors:
        last_error = errors[-1]
        suggestions.append(f"Re-run {last_error.get('crew', '?')} (failed: {last_error.get('error', '?')[:60]})")

    # Suggest crews not recently run
    all_crews = {"research", "code_review", "grant_hunt", "content", "daily_ops", "weekly_report", "build_project"}
    unused = all_crews - crews_run
    if unused:
        suggestions.append(f"Try unused crew: {', '.join(list(unused)[:3])}")

    # Always suggest daily-ops if not run today
    today = datetime.now().strftime("%Y-%m-%d")
    today_runs = [r for r in recent_runs if r.get("timestamp", "").startswith(today)]
    if not any(r.get("crew") == "daily_ops" for r in today_runs):
        suggestions.append("Run Daily Ops (morning routine)")

    if not suggestions:
        suggestions.append("System ready — pick a crew from the menu")

    return suggestions[:3]


# ═══════════════════════════════════════════════════════
# SESSION LIFECYCLE
# ═══════════════════════════════════════════════════════

def save_session_snapshot(runs_this_session: list):
    """Save session snapshot on close."""
    snapshot_path = os.path.join(BASE_DIR, "memory", "last_session.md")
    index_path = os.path.join(BASE_DIR, "_index.md")
    now = datetime.now()

    # Generate snapshot
    snapshot = f"# Last Session\n"
    snapshot += f"- **Date:** {now:%Y-%m-%d %H:%M}\n"
    snapshot += f"- **Crews executed:** {len(runs_this_session)}\n\n"

    if runs_this_session:
        snapshot += "## Executions\n"
        for run in runs_this_session:
            status = run.get("status", "?")
            crew = run.get("crew", "?")
            duration = run.get("duration_sec", "?")
            snapshot += f"- {crew}: {status} ({duration}s)\n"
    else:
        snapshot += "_No crews were executed in this session._\n"

    os.makedirs(os.path.dirname(snapshot_path), exist_ok=True)
    with open(snapshot_path, "w") as f:
        f.write(snapshot)

    # Update _index.md
    # Read complete logs for metrics
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

    # Most used crew
    from collections import Counter
    crew_counts = Counter(r.get("crew", "?") for r in all_runs)
    most_used = crew_counts.most_common(1)[0] if crew_counts else ("—", 0)

    # Last 5 executions to display
    recent_lines = ""
    for r in all_runs[-5:]:
        ts = r.get("timestamp", "?")[:16]
        status = r.get("status", "?")
        crew = r.get("crew", "?")
        recent_lines += f"- `{ts}` | {crew} | {status} | {r.get('duration_sec', '?')}s\n"

    index = f"""# _index — System State
# Auto-updated by Kernel Boot

## Last Session
- **Date:** {now:%Y-%m-%d %H:%M}
- **Crews executed:** {len(runs_this_session)}

## Recent Executions
{recent_lines if recent_lines else '_No executions._'}

## System Metrics
- **Total executions:** {total}
- **Success rate:** {successes}/{total} ({successes/max(total,1)*100:.0f}%)
- **Most used crew:** {most_used[0]} ({most_used[1]}x)
- **Average time:** {avg_time:.0f}s
"""
    with open(index_path, "w") as f:
        f.write(index)

    console.print(f"\n[dim]Session saved to memory/last_session.md[/dim]")
    console.print(f"[dim]_index.md updated[/dim]")


LOG_FILE = os.path.join(os.path.dirname(__file__), "logs", "execution_log.jsonl")


def _log_execution(entry: dict):
    """Append a JSON line to the execution log."""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


COOLDOWN_SEC = 15  # Cooldown between crew runs to avoid rate limits


# ── Supervisor-integrated crew execution ──
from core.crew_runner import run_crew as run_crew_supervised


def run_crew(crew, mode_name: str, project: str | None = None, max_retries: int = 3):
    """Execute a crew with full supervisor + governance + tracing.

    Maintains the original public signature. Internally delegates to
    core.crew_runner.run_crew (supervisor, governance, checkpointing, tracing).
    Preserves: Rich console output, .md file, execution_log.jsonl.
    """
    out_dir = f"output/{project}" if project else "output"
    os.makedirs(out_dir, exist_ok=True)

    project_label = f" [{project}]" if project else ""
    agents_used = [a.role for a in crew.agents]
    console.print(f"\n[bold green]Running {mode_name}{project_label}...[/bold green]")
    console.print(f"[dim]Agents: {', '.join(agents_used)}[/dim]")
    console.print(f"[dim]Supervisor: ON | Governance: ON | Tracing: ON[/dim]\n")
    start = datetime.now()

    # Extract input_text from the crew's first task
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

    # Call the full orchestrator
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
            console.print(f"[dim]Retries used: {result['retries']}[/dim]")
        return log_entry

    # Write output to .md file
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
            f"**Date:** {datetime.now():%Y-%m-%d %H:%M}\n"
            f"**Time:** {elapsed}\n"
            f"**Agents:** {', '.join(agents_used)}\n"
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
        f"[green]Completed in {elapsed}[/green]{sup_info}{gov_info}\n"
        f"Saved to: [cyan]{out}[/cyan]",
        border_style="green",
    ))
    console.print(f"\n{output_text}")
    return log_entry


def run_interactive():
    show_banner()
    show_status()
    show_agents()
    show_projects()

    # KERNEL BOOT — Phase 1
    recent_runs = kernel_boot()
    session_runs = []  # session tracking

    console.print("\n[bold]What do you want to do?[/bold]\n")
    console.print("  [cyan]1.[/cyan]  Research and validate an idea")
    console.print("  [cyan]2.[/cyan]  Review project code")
    console.print("  [cyan]3.[/cyan]  Analyze data (Excel/CSV)")
    console.print("  [cyan]4.[/cyan]  Analyze database")
    console.print("  [cyan]5.[/cyan]  Full MVP (research + plan + architecture)")
    console.print("  [green]6.[/green]  [bold]Enigma Audit[/bold] (audit agent/scanner/DB)")
    console.print("  [green]7.[/green]  [bold]Grant Hunt[/bold] (find grants and opportunities)")
    console.print("  [green]8.[/green]  [bold]Content[/bold] (threads, blogs, pitches, narratives)")
    console.print("  [green]9.[/green]  [bold]Daily Ops[/bold] (COO morning routine)")
    console.print("  [green]10.[/green] [bold]Weekly Report[/bold] (weekly meeting prep)")
    console.print("  [cyan]11.[/cyan] Launch Dashboard (Streamlit)")
    console.print("  [cyan]12.[/cyan] Launch Telegram Bot")
    console.print("  [green]13.[/green] [bold]Voice Mode[/bold] (natural speech from your Mac)")
    console.print("  [green]14.[/green] [bold]Build Project[/bold] (generate project with real code)")
    console.print("  [magenta]15.[/magenta] [bold]A2A Server[/bold] (expose agents as a service)")
    console.print("  [cyan]0.[/cyan]  Exit")

    choice = IntPrompt.ask(
        "\nOption",
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

    # Ask for project if applicable
    project = None
    if choice in (1, 5, 7, 8, 10):
        proj_input = Prompt.ask("Project (Enter for general mode)", default="")
        project = proj_input if proj_input else None

    result = None
    if choice == 1:
        topic = Prompt.ask("Describe your idea")
        result = run_crew(create_research_crew(topic), "research", project)
    elif choice == 2:
        path = Prompt.ask("Path to project", default=".")
        result = run_crew(create_code_review_crew(path), "code_review")
    elif choice == 3:
        f = Prompt.ask("Path to Excel/CSV file")
        result = run_crew(create_data_analysis_crew(f), "data_analysis")
    elif choice == 4:
        conn = Prompt.ask(
            "Connection string",
            default=os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/db"),
        )
        result = run_crew(create_database_crew(conn), "database")
    elif choice == 5:
        topic = Prompt.ask("Describe your MVP idea")
        result = run_crew(create_full_mvp_crew(topic), "full_mvp", project)
    elif choice == 6:
        console.print("\n[bold green]Enigma Audit — What to audit?[/bold green]")
        console.print("  [cyan]a.[/cyan] An agent (URL)")
        console.print("  [cyan]b.[/cyan] The Enigma database")
        console.print("  [cyan]c.[/cyan] The scanner code")
        sub = Prompt.ask("Option", choices=["a", "b", "c"])
        if sub == "a":
            url = Prompt.ask("Agent URL", default="https://apex-arbitrage-agent-production.up.railway.app")
            result = run_crew(create_enigma_audit_crew(url), "enigma_agent_audit")
        elif sub == "b":
            result = run_crew(create_enigma_audit_crew("database"), "enigma_db_audit")
        elif sub == "c":
            path = Prompt.ask("Path to scanner", default="/Users/jquiceva/Enigma")
            result = run_crew(create_enigma_audit_crew(path), "enigma_code_audit")
    elif choice == 7:
        task = Prompt.ask("What kind of grants are you looking for?", default="AI and Web3 infrastructure grants")
        result = run_crew(create_grant_hunt_crew(task, project), "grant_hunt", project)
    elif choice == 8:
        console.print("\nTypes: thread, blog, update, pitch, narrative, tokenomics")
        task = Prompt.ask("Describe the content you need")
        result = run_crew(create_content_crew(task, project), "content", project)
    elif choice == 9:
        file_path = Prompt.ask("Excel file for metrics (Enter to skip)", default="")
        result = run_crew(
            create_daily_ops_crew(file_path if file_path else None),
            "daily_ops",
        )
    elif choice == 10:
        file_path = Prompt.ask("Excel file for metrics (Enter to skip)", default="")
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
        desc = Prompt.ask("Describe the project to generate")
        name = Prompt.ask("Project name (folder)", default="new_project")
        result = run_crew(create_build_project_crew(desc, name), "build_project")
    elif choice == 15:
        launch_a2a_server()

    # Track execution in session
    if result:
        session_runs.append(result)

    # Save snapshot on exit
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
            console.print("[red]--task required[/red]"); sys.exit(1)
        run_crew(create_research_crew(task), "research", project)
    elif args.mode == "code-review":
        run_crew(create_code_review_crew(args.path or "."), "code_review")
    elif args.mode == "data":
        if not args.file:
            console.print("[red]--file required[/red]"); sys.exit(1)
        run_crew(create_data_analysis_crew(args.file), "data_analysis")
    elif args.mode == "database":
        conn = args.connection or os.getenv("DATABASE_URL")
        if not conn:
            console.print("[red]--connection or DATABASE_URL required[/red]"); sys.exit(1)
        run_crew(create_database_crew(conn), "database")
    elif args.mode == "full-mvp":
        if not task:
            console.print("[red]--task required[/red]"); sys.exit(1)
        run_crew(create_full_mvp_crew(task), "full_mvp", project)
    elif args.mode == "enigma-audit":
        target = task or args.path or "database"
        run_crew(create_enigma_audit_crew(target), "enigma_audit")
    elif args.mode == "grant-hunt":
        run_crew(create_grant_hunt_crew(task, project), "grant_hunt", project)
    elif args.mode == "content":
        if not task:
            console.print("[red]--task required[/red]"); sys.exit(1)
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
            console.print("[red]--task required (project description)[/red]"); sys.exit(1)
        name = args.project or "new_project"
        run_crew(create_build_project_crew(task, name), "build_project")
    elif args.mode == "a2a-server":
        launch_a2a_server()
    elif args.mode == "all":
        launch_all()


def launch_dashboard():
    """Launch Streamlit dashboard."""
    dashboard_path = os.path.join(os.path.dirname(__file__), "interfaces", "streamlit_dashboard.py")
    if not os.path.exists(dashboard_path):
        console.print("[red]interfaces/streamlit_dashboard.py not found[/red]")
        return
    console.print("[green]Launching Dashboard at http://localhost:8501 ...[/green]")
    subprocess.run(["streamlit", "run", dashboard_path, "--server.port", "8501"])


def launch_telegram():
    """Launch Telegram bot."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        console.print("[red]TELEGRAM_BOT_TOKEN not configured in .env[/red]")
        return
    console.print("[green]Launching Telegram Bot...[/green]")
    from interfaces.telegram_bot import start_bot
    start_bot()


def launch_voice():
    """Launch continuous voice mode from Mac."""
    console.print("[green]Launching Voice Mode...[/green]")
    from interfaces.voice_interface import start_voice_loop
    start_voice_loop()


def launch_a2a_server():
    """Launch A2A Server — expose crews as discoverable services."""
    console.print("[magenta]Launching A2A Server...[/magenta]")
    console.print("[dim]Other agents can discover you at http://localhost:8000/.well-known/agent-card.json[/dim]")
    from a2a_server import start_server
    start_server(port=8000)


def launch_all():
    """Launch dashboard + telegram in parallel."""
    console.print("[green]Launching full Mission Control...[/green]")

    # Telegram in thread
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if token:
        t = threading.Thread(target=launch_telegram, daemon=True)
        t.start()
        console.print("[green]Telegram Bot started in background[/green]")
    else:
        console.print("[yellow]TELEGRAM_BOT_TOKEN not configured, skipping[/yellow]")

    # Dashboard en foreground (bloquea)
    launch_dashboard()


def main():
    parser = argparse.ArgumentParser(description="CrewAI Pro — 8 Agents + Mission Control")
    parser.add_argument(
        "--mode",
        choices=[
            "research", "code-review", "data", "database", "full-mvp",
            "enigma-audit", "grant-hunt", "content", "daily-ops",
            "weekly-report", "build", "dashboard", "telegram", "voice", "a2a-server", "all",
        ],
    )
    parser.add_argument("--task", help="Task description")
    parser.add_argument("--topic", help="Alias for --task (compatibility)")
    parser.add_argument("--project", help="Project name (from projects.yaml)")
    parser.add_argument("--path", help="Path to project/directory")
    parser.add_argument("--file", help="Path to Excel/CSV file")
    parser.add_argument("--connection", help="Database connection string")
    args = parser.parse_args()

    if args.mode:
        run_cli(args)
    else:
        run_interactive()


if __name__ == "__main__":
    main()
