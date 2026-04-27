#!/usr/bin/env python3
"""
Translate the DOF-MESH Book to English.
Uses local inference via Ollama to deterministically translate Markdown files while strictly
preserving Obsidian-Flavored Markdown syntax (Wikilinks, Callouts, Frontmatter).

This script uses standard 'requests' to ensure 100% sovereignty, avoiding external wrappers
like litellm which suffered from supply chain attacks (CVE-2026-35030).

Usage:
  python3 scripts/translate_book_to_english.py
"""

import os
import sys
import json
import urllib.request
from pathlib import Path
from rich.console import Console
from rich.progress import track

console = Console()

SOURCE_DIR = Path("docs/03_book")
TARGET_DIR = Path("docs/03_book_en")

# For local AGI sovereignty, use the default team fallback model
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_URL = "http://localhost:11434/api/chat"

SYSTEM_PROMPT = """You are a professional technical translator specializing in computer science, cryptography, and autonomous agents.
Your task is to translate the following text from Spanish to English.

CRITICAL RULES (Spec-Driven Translation):
1. PRESERVE ALL OBSIDIAN MARKDOWN:
   - Wikilinks MUST NOT BE TRANSLATED internally. Example: `[[BOOK_CH1_PROBLEM]]` stays exactly `[[BOOK_CH1_PROBLEM]]`. If it has an alias `[[BOOK_CH1_PROBLEM|El Problema]]`, you can translate the alias: `[[BOOK_CH1_PROBLEM|The Problem]]`.
   - Callouts MUST NOT BE BROKEN. Keep `> [!tip]`, `> [!warning]`, etc.
   - Frontmatter (YAML blocks between `---`) keys stay the same, you can translate the string values.
2. PRESERVE ALL CODE BLOCKS: Do not translate variable names, file paths, or shell commands inside ` ``` ` blocks.
3. PRESERVE ALL GITHUB MARKDOWN: Keep tables, lists, bold, and italic formatting exactly as they are.
4. TONE: Maintain the authoritative, "hacker philosophy", and deterministic tone of the original author.
5. Do not add conversational intro/outro text (e.g., "Here is the translation:"). Output ONLY the translated markdown.
"""

def translate_file(file_path: Path) -> str:
    """Read a markdown file and translate it using Local Ollama API."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    data = {
        "model": DEFAULT_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Please translate the following markdown file to English:\n\n{content}"}
        ],
        "stream": False,
        "options": {
            "temperature": 0.1
        }
    }

    req = urllib.request.Request(
        OLLAMA_URL, 
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result.get("message", {}).get("content", "")
    except urllib.error.URLError as e:
        console.print(f"[red]Connection error: Could not reach Ollama at {OLLAMA_URL}. Is Ollama running?[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error translating {file_path.name}: {str(e)}[/red]")
        return ""

def main():
    if not SOURCE_DIR.exists():
        console.print(f"[red]Source directory {SOURCE_DIR} not found.[/red]")
        sys.exit(1)

    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    
    md_files = list(SOURCE_DIR.glob("*.md"))
    if not md_files:
        console.print("[yellow]No markdown files found to translate.[/yellow]")
        sys.exit(0)

    console.print(f"[bold blue]Found {len(md_files)} chapters. Starting Sovereign Translation Pipeline...[/bold blue]")
    console.print(f"Using local inference model: [bold green]{DEFAULT_MODEL}[/bold green]")

    success_count = 0
    for md_file in track(md_files, description="Translating chapters..."):
        target_file = TARGET_DIR / md_file.name
        
        # Skip if already translated to save compute costs
        if target_file.exists() and target_file.stat().st_size > 0:
            continue
            
        translated_content = translate_file(md_file)
        
        if translated_content:
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(translated_content)
            success_count += 1

    console.print(f"\n[bold green]Translation complete. {success_count} new files processed.[/bold green]")
    console.print(f"Check the [bold cyan]{TARGET_DIR}[/bold cyan] directory for the English copy of the book.")

if __name__ == "__main__":
    main()
