#!/usr/bin/env python3
"""
connection_finder.py — Conexiones cross-domain entre notas del vault.
Uso: python3 scripts/connection_finder.py --week [--prompt]
"""
import sys, re
from datetime import datetime, timedelta
from pathlib import Path

VAULT = Path.home() / "cerebro cyber" / "cerebro cyber"
IGNORE = {"hot.md", "CLAUDE.md", "contexto-canonico-2026.md"}
IGNORE_DIRS = {".obsidian", ".trash"}
DOF_AGENTS = ["lider_orquestador", "arquitecto", "developer", "investigador",
              "qa_engineer", "seguridad_blockchain", "experto_ideacion",
              "experto_multichain", "devops", "bizdev", "product_manager"]

def load_notes(days=7, query=""):
    cutoff = datetime.now() - timedelta(days=days)
    notes = []
    for md in VAULT.rglob("*.md"):
        if md.name in IGNORE or any(d in md.parts for d in IGNORE_DIRS): continue
        try:
            mtime = datetime.fromtimestamp(md.stat().st_mtime)
        except: continue
        if mtime < cutoff: continue
        content = md.read_text(encoding="utf-8", errors="ignore")
        if query and query.lower() not in content.lower(): continue
        m = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        title = m.group(1) if m else md.stem
        tm = re.search(r"^tags:\s*\[(.+)\]", content, re.MULTILINE)
        tags = tm.group(1) if tm else ""
        notes.append({"file": md.name, "title": title, "tags": tags,
                       "excerpt": content[200:500].replace("\n", " ").strip()})
    return sorted(notes, key=lambda x: x.get("file", ""))[:25]

def build_prompt(notes):
    block = "\n\n".join([
        f"[{i+1}] **{n['title']}** — tags: {n['tags']}\n{n['excerpt'][:280]}"
        for i, n in enumerate(notes)])
    return f"""Soy Cyber Paisa — DOF-MESH (governance IA determinística).
Mis 11 agentes: {', '.join(DOF_AGENTS)}

{len(notes)} notas recientes del vault:

{block}

Encuentra 3 conexiones NO OBVIAS. Para cada una:
1. Notas conectadas (A ↔ B)
2. Principio subyacente común
3. Hook de contenido (1 línea para Twitter/LinkedIn)
4. Agente DOF más relevante
5. Acción concreta en código o publicación

Responde como JSON: {{"connections": [{{"nota_a":"","nota_b":"","principio":"","hook":"","agente_dof":"","accion":""}}]}}"""

def main():
    args = sys.argv[1:]
    days = 30 if "--month" in args else 7
    query = args[args.index("--query")+1] if "--query" in args and args.index("--query")+1 < len(args) else ""
    notes = load_notes(days, query)
    if not notes:
        print(f"Sin notas en últimos {days} días. Usa --month"); return
    prompt = build_prompt(notes)
    print(f"📊 {len(notes)} notas · {days} días\n{'='*60}")
    print(prompt)
    print(f"{'='*60}\n→ Solo prompt: python3 scripts/connection_finder.py --prompt | pbcopy")

if __name__ == "__main__": main()
