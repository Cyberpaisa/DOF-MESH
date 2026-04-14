#!/usr/bin/env python3
"""Agrega frontmatter estándar a notas Obsidian sin él. Uso: python3 scripts/metadata_fixer.py [--dry-run]"""
import sys, re
from pathlib import Path
from datetime import datetime

VAULT = Path.home() / "cerebro cyber" / "cerebro cyber"
SAFE = ["wiki", "personal", "dof-mesh", "hub"]
PROTECTED = {"hot.md", "CLAUDE.md", "contexto-canonico-2026.md"}
TYPE_MAP = {"wiki/conceptos": "concept", "wiki": "concept", "personal": "personal",
            "dof-mesh/hackathons": "session", "dof-mesh/main": "project", "dof-mesh": "project",
            "hub/claude-code": "learning", "hub": "note"}

def detect_type(path):
    rel = str(path.relative_to(VAULT))
    for prefix, t in sorted(TYPE_MAP.items(), key=lambda x: -len(x[0])):
        if rel.startswith(prefix): return t
    return "note"

def fix(path, dry=False):
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except: return False
    if content.startswith("---"): return False
    note_type = detect_type(path)
    date = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")
    stem = re.sub(r"[-_]", " ", path.stem).lower().split()
    tags = [w for w in stem if len(w) > 3][:3]
    fm = f"---\ntype: {note_type}\ndate: {date}\nproject: DOF-MESH\nstatus: active\ntags: [{', '.join(tags)}]\n---\n\n"
    if not dry: path.write_text(fm + content, encoding="utf-8")
    return True

def main():
    dry = "--dry-run" in sys.argv
    fixed = skipped = 0
    for folder in SAFE:
        fp = VAULT / folder
        if not fp.exists(): continue
        for md in sorted(fp.rglob("*.md")):
            if md.name in PROTECTED: continue
            if fix(md, dry): fixed += 1; print(f"  {'→' if dry else '✅'} {md.relative_to(VAULT)}")
            else: skipped += 1
    print(f"\n{'DRY' if dry else 'DONE'}: {fixed} procesadas · {skipped} ya tenían frontmatter")
    if dry and fixed: print("→ Aplica con: python3 scripts/metadata_fixer.py")

if __name__ == "__main__": main()
