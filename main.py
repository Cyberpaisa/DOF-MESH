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
        "[dim]9 LLM providers — Logging — Memory — SOUL.md[/dim]",
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
    table.add_row("MiniMax", ok if status.get("minimax") else off, "M2.1 128K (PRIMARY — all roles)")
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


def run_crew(crew, mode_name: str, project: str | None = None, max_retries: int = 3,
             crew_factory=None):
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
        crew_factory=crew_factory,
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
    console.print("  [magenta]16.[/magenta] [bold]Verify Formal Invariants[/bold] (Z3 SMT proofs)")
    console.print("  [magenta]17.[/magenta] [bold]Adversarial Evaluation[/bold] (Red Team on last output)")
    console.print("  [magenta]18.[/magenta] [bold]Memory Governance Dashboard[/bold]")
    console.print("  [magenta]19.[/magenta] [bold]OAGS Compliance Check[/bold]")
    console.print("  [cyan]0.[/cyan]  Exit")

    choice = IntPrompt.ask(
        "\nOption",
        choices=["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19"],
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
        factory = lambda: create_research_crew(topic)
        result = run_crew(factory(), "research", project, crew_factory=factory)
    elif choice == 2:
        path = Prompt.ask("Path to project", default=".")
        factory = lambda: create_code_review_crew(path)
        result = run_crew(factory(), "code_review", crew_factory=factory)
    elif choice == 3:
        f = Prompt.ask("Path to Excel/CSV file")
        factory = lambda: create_data_analysis_crew(f)
        result = run_crew(factory(), "data_analysis", crew_factory=factory)
    elif choice == 4:
        conn = Prompt.ask(
            "Connection string",
            default=os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/db"),
        )
        factory = lambda: create_database_crew(conn)
        result = run_crew(factory(), "database", crew_factory=factory)
    elif choice == 5:
        topic = Prompt.ask("Describe your MVP idea")
        factory = lambda: create_full_mvp_crew(topic)
        result = run_crew(factory(), "full_mvp", project, crew_factory=factory)
    elif choice == 6:
        console.print("\n[bold green]Enigma Audit — What to audit?[/bold green]")
        console.print("  [cyan]a.[/cyan] An agent (URL)")
        console.print("  [cyan]b.[/cyan] The Enigma database")
        console.print("  [cyan]c.[/cyan] The scanner code")
        sub = Prompt.ask("Option", choices=["a", "b", "c"])
        if sub == "a":
            url = Prompt.ask("Agent URL", default="https://apex-arbitrage-agent-production.up.railway.app")
            factory = lambda: create_enigma_audit_crew(url)
            result = run_crew(factory(), "enigma_agent_audit", crew_factory=factory)
        elif sub == "b":
            factory = lambda: create_enigma_audit_crew("database")
            result = run_crew(factory(), "enigma_db_audit", crew_factory=factory)
        elif sub == "c":
            path = Prompt.ask("Path to scanner", default="/Users/jquiceva/Enigma")
            factory = lambda: create_enigma_audit_crew(path)
            result = run_crew(factory(), "enigma_code_audit", crew_factory=factory)
    elif choice == 7:
        task = Prompt.ask("What kind of grants are you looking for?", default="AI and Web3 infrastructure grants")
        factory = lambda: create_grant_hunt_crew(task, project)
        result = run_crew(factory(), "grant_hunt", project, crew_factory=factory)
    elif choice == 8:
        console.print("\nTypes: thread, blog, update, pitch, narrative, tokenomics")
        task = Prompt.ask("Describe the content you need")
        factory = lambda: create_content_crew(task, project)
        result = run_crew(factory(), "content", project, crew_factory=factory)
    elif choice == 9:
        file_path = Prompt.ask("Excel file for metrics (Enter to skip)", default="")
        factory = lambda: create_daily_ops_crew(file_path if file_path else None)
        result = run_crew(factory(), "daily_ops", crew_factory=factory)
    elif choice == 10:
        file_path = Prompt.ask("Excel file for metrics (Enter to skip)", default="")
        factory = lambda: create_weekly_report_crew(project, file_path if file_path else None)
        result = run_crew(factory(), "weekly_report", project, crew_factory=factory)
    elif choice == 11:
        launch_dashboard()
    elif choice == 12:
        launch_telegram()
    elif choice == 13:
        launch_voice()
    elif choice == 14:
        desc = Prompt.ask("Describe the project to generate")
        name = Prompt.ask("Project name (folder)", default="new_project")
        factory = lambda: create_build_project_crew(desc, name)
        result = run_crew(factory(), "build_project", crew_factory=factory)
    elif choice == 15:
        launch_a2a_server()
    elif choice == 16:
        launch_z3_verifier()
    elif choice == 17:
        launch_adversarial(session_runs)
    elif choice == 18:
        launch_memory_dashboard()
    elif choice == 19:
        launch_oags_compliance()

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
        factory = lambda: create_research_crew(task)
        run_crew(factory(), "research", project, crew_factory=factory)
    elif args.mode == "code-review":
        factory = lambda: create_code_review_crew(args.path or ".")
        run_crew(factory(), "code_review", crew_factory=factory)
    elif args.mode == "data":
        if not args.file:
            console.print("[red]--file required[/red]"); sys.exit(1)
        factory = lambda: create_data_analysis_crew(args.file)
        run_crew(factory(), "data_analysis", crew_factory=factory)
    elif args.mode == "database":
        conn = args.connection or os.getenv("DATABASE_URL")
        if not conn:
            console.print("[red]--connection or DATABASE_URL required[/red]"); sys.exit(1)
        factory = lambda: create_database_crew(conn)
        run_crew(factory(), "database", crew_factory=factory)
    elif args.mode == "full-mvp":
        if not task:
            console.print("[red]--task required[/red]"); sys.exit(1)
        factory = lambda: create_full_mvp_crew(task)
        run_crew(factory(), "full_mvp", project, crew_factory=factory)
    elif args.mode == "enigma-audit":
        target = task or args.path or "database"
        factory = lambda: create_enigma_audit_crew(target)
        run_crew(factory(), "enigma_audit", crew_factory=factory)
    elif args.mode == "grant-hunt":
        factory = lambda: create_grant_hunt_crew(task, project)
        run_crew(factory(), "grant_hunt", project, crew_factory=factory)
    elif args.mode == "content":
        if not task:
            console.print("[red]--task required[/red]"); sys.exit(1)
        factory = lambda: create_content_crew(task, project)
        run_crew(factory(), "content", project, crew_factory=factory)
    elif args.mode == "daily-ops":
        factory = lambda: create_daily_ops_crew(args.file)
        run_crew(factory(), "daily_ops", crew_factory=factory)
    elif args.mode == "weekly-report":
        factory = lambda: create_weekly_report_crew(project, args.file)
        run_crew(factory(), "weekly_report", project, crew_factory=factory)
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
        factory = lambda: create_build_project_crew(task, name)
        run_crew(factory(), "build_project", crew_factory=factory)
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


def launch_z3_verifier():
    """Run Z3 formal verification of DOF invariants."""
    console.print("\n[bold magenta]Z3 Formal Verification — DOF Invariants[/bold magenta]\n")
    from core.z3_verifier import Z3Verifier
    verifier = Z3Verifier()
    results = verifier.verify_all()

    for r in results:
        status = "[green]VERIFIED[/green]" if r.result == "VERIFIED" else "[red]COUNTEREXAMPLE[/red]"
        console.print(f"  {status}  {r.theorem_name} ({r.proof_time_ms:.1f}ms)")
        console.print(f"           [dim]{r.description}[/dim]")

    verified = sum(1 for r in results if r.result == "VERIFIED")
    total = len(results)
    total_ms = sum(r.proof_time_ms for r in results)
    console.print(f"\n  [bold]{verified}/{total} theorems verified[/bold] in {total_ms:.1f}ms (Z3 {results[0].z3_version})")
    console.print(f"  [dim]Results saved to logs/z3_proofs.json[/dim]\n")


def launch_adversarial(session_runs: list):
    """Run adversarial evaluation on the last output."""
    console.print("\n[bold magenta]Adversarial Evaluation — Red Team Analysis[/bold magenta]\n")

    # Find last successful output
    last_output = None
    for run in reversed(session_runs):
        if run.get("output"):
            last_output = run["output"]
            break

    if not last_output:
        # Try reading last output file
        output_dir = os.path.join(BASE_DIR, "output")
        if os.path.exists(output_dir):
            files = sorted([f for f in os.listdir(output_dir) if f.endswith(".md")])
            if files:
                with open(os.path.join(output_dir, files[-1])) as f:
                    last_output = f.read()
                console.print(f"  [dim]Using last output file: {files[-1]}[/dim]")

    if not last_output:
        console.print("  [yellow]No output found to evaluate. Run a crew first.[/yellow]\n")
        return

    from core.adversarial import AdversarialEvaluator
    evaluator = AdversarialEvaluator()
    result = evaluator.evaluate(last_output)

    verdict_style = "green" if result.verdict == "PASS" else "red"
    console.print(f"  Verdict: [{verdict_style}]{result.verdict}[/{verdict_style}]")
    console.print(f"  ACR: {result.acr:.2f} ({len(result.resolved)} resolved / {result.total_issues} total)")
    console.print(f"  Score: {result.score}")
    console.print(f"  Red Team Score: {result.red_team_score}")
    console.print(f"  Time: {result.elapsed_ms:.1f}ms")

    if result.unresolved:
        console.print(f"\n  [red]Unresolved issues:[/red]")
        for u in result.unresolved:
            console.print(f"    [{u['severity']}] {u['issue_id']}: {u['reason']}")

    console.print(f"\n  [dim]Results saved to logs/adversarial.jsonl[/dim]\n")


def launch_memory_dashboard():
    """Display Memory Governance Dashboard."""
    console.print("\n[bold magenta]Memory Governance Dashboard[/bold magenta]\n")

    from core.memory_governance import GovernedMemoryStore, TemporalGraph, ConstitutionalDecay

    try:
        store = GovernedMemoryStore()
    except Exception as e:
        console.print(f"  [red]Failed to load memory store: {e}[/red]\n")
        return

    stats = store.get_stats()
    graph = TemporalGraph(store)
    decay = ConstitutionalDecay(store)

    # Stats summary
    console.print(f"  [bold]Total memories:[/bold] {stats['total_memories']}")
    console.print(f"  [bold]Active memories:[/bold] {stats['active_memories']}")
    console.print(f"  [bold]Avg relevance:[/bold] {stats['avg_relevance']:.3f}")

    # By category
    if stats["by_category"]:
        cat_table = Table(title="By Category", show_lines=False)
        cat_table.add_column("Category", style="cyan")
        cat_table.add_column("Count", justify="right")
        for cat, count in sorted(stats["by_category"].items()):
            cat_table.add_row(cat, str(count))
        console.print(cat_table)

    # By status
    if stats["by_status"]:
        status_table = Table(title="By Status", show_lines=False)
        status_table.add_column("Status", style="cyan")
        status_table.add_column("Count", justify="right")
        for status, count in sorted(stats["by_status"].items()):
            style = "green" if status == "approved" else "yellow" if status == "warning" else "red"
            status_table.add_row(f"[{style}]{status}[/{style}]", str(count))
        console.print(status_table)

    # Top memories by relevance
    active = store.query()
    if active:
        top_table = Table(title="Top Memories (by relevance)", show_lines=False)
        top_table.add_column("Score", justify="right", width=6)
        top_table.add_column("Category", style="cyan", width=12)
        top_table.add_column("Content", width=60)
        for e in active[:5]:
            top_table.add_row(f"{e.relevance_score:.2f}", e.category, e.content[:60])
        console.print(top_table)

    # Memories close to decay
    decay_status = decay.get_decay_status()
    at_risk = [d for d in decay_status if not d["protected"] and d["relevance_score"] < 0.5]
    if at_risk:
        risk_table = Table(title="Approaching Decay (score < 0.5)", show_lines=False)
        risk_table.add_column("Score", justify="right", width=6)
        risk_table.add_column("Category", style="cyan", width=12)
        risk_table.add_column("Content", width=60)
        for d in at_risk[:5]:
            risk_table.add_row(f"{d['relevance_score']:.2f}", d["category"], d["content_summary"][:60])
        console.print(risk_table)

    # Age distribution
    age_dist = graph.memory_age_distribution()
    if any(v > 0 for v in age_dist.values()):
        age_table = Table(title="Age Distribution", show_lines=False)
        age_table.add_column("Bucket", style="cyan")
        age_table.add_column("Count", justify="right")
        for bucket, count in age_dist.items():
            age_table.add_row(bucket, str(count))
        console.print(age_table)

    console.print()


def launch_oags_compliance():
    """Run OAGS Compliance Check."""
    console.print("\n[bold magenta]OAGS Compliance Check — Open Agent Governance Specification[/bold magenta]\n")

    from core.oags_bridge import OAGSIdentity, OAGSPolicyBridge, OAGSAuditBridge

    # Identity
    try:
        identity = OAGSIdentity()
        card = identity.get_agent_card()
        console.print(f"  [bold]Agent Identity:[/bold] {card['identity_hash'][:16]}...")
        console.print(f"  [bold]Model:[/bold] {card['model']}")
        console.print(f"  [bold]Constitution Hash:[/bold] {card['constitution_hash'][:16]}...")
        console.print(f"  [bold]Framework:[/bold] {card['framework']} v{card['version']}")
    except Exception as e:
        console.print(f"  [red]Identity error: {e}[/red]")
        return

    # Conformance
    console.print()
    conformance = OAGSPolicyBridge.validate_conformance(level=3)
    for lvl in [1, 2, 3]:
        key = f"level_{lvl}"
        info = conformance[key]
        status = "[green]PASS[/green]" if info["passed"] else "[red]FAIL[/red]"
        console.print(f"  Level {lvl}: {status}")
        for check in info["checks"]:
            check_status = "[green]OK[/green]" if check["passed"] else "[red]FAIL[/red]"
            console.print(f"    {check_status}  {check['check']}: {check['detail']}")

    console.print(f"\n  [bold]Max Level Passed:[/bold] {conformance['max_level_passed']}")

    # Policy count
    try:
        import yaml as _yaml
        c_path = os.path.join(BASE_DIR, "dof.constitution.yml")
        with open(c_path, "r") as f:
            data = _yaml.safe_load(f) or {}
        rules = data.get("rules", {})
        total_policies = (
            len(rules.get("hard", []))
            + len(rules.get("soft", []))
            + len(rules.get("ast", []))
        )
        console.print(f"  [bold]Total Policies:[/bold] {total_policies}")
    except Exception:
        pass

    # Audit summary
    try:
        audit = OAGSAuditBridge(identity)
        events = audit.export_audit_events()
        if events:
            report = audit.generate_audit_report(events)
            console.print(f"\n  [bold]Audit Events:[/bold] {report['total_events']}")
            console.print(f"  [bold]Compliance Rate:[/bold] {report['compliance_rate']:.2%}")
            if report["by_type"]:
                for etype, count in sorted(report["by_type"].items()):
                    console.print(f"    {etype}: {count}")
        else:
            console.print("\n  [dim]No audit events found[/dim]")
    except Exception as e:
        console.print(f"\n  [yellow]Audit error: {e}[/yellow]")

    console.print()


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
