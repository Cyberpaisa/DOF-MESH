#!/usr/bin/env python3
"""Nota diaria DOF-MESH. LaunchAgent 7am. Uso: python3 scripts/daily_capture.py [--force|--status]"""
import json, subprocess, sys, re
from datetime import datetime
from pathlib import Path

VAULT = Path.home() / "cerebro cyber" / "cerebro cyber"
REPO = Path.home() / "equipo-de-agentes"
DATE = datetime.now().strftime("%Y-%m-%d")
WD = {"Monday":"Lunes","Tuesday":"Martes","Wednesday":"Miércoles","Thursday":"Jueves",
      "Friday":"Viernes","Saturday":"Sábado","Sunday":"Domingo"}[datetime.now().strftime("%A")]

def git_log():
    try:
        r = subprocess.run(["git","log","--oneline","-3"], cwd=REPO, capture_output=True, text=True)
        return r.stdout.strip() or "sin commits"
    except: return "?"

def uncommitted():
    try:
        r = subprocess.run(["git","status","--short"], cwd=REPO, capture_output=True, text=True)
        return len([l for l in r.stdout.splitlines() if l.strip()])
    except: return 0

def latest_asr():
    try:
        d = sorted((REPO/"tests/red_team/reports").glob("*.json"))
        if not d: return 0.0
        data = json.loads(d[-1].read_text())
        return float(data.get("asr_percent") or data.get("asr") or 0)
    except: return 0.0

def test_count():
    try:
        c = (REPO/"docs/09_sessions/ESTADO_ACTUAL.md").read_text(errors="ignore")
        # Prioridad 1: "Tests discovered | 4,778"
        m = re.search(r"Tests\s+discovered[^\d]*([\d,]+)", c, re.I)
        if m: return m.group(1)
        # Prioridad 2: "4,xxx tests (discovered|passing|ejecutables|OK)"
        m2 = re.search(r"([\d,]{4,7})\s*tests?\s*(?:discovered|passing|ejecutables|OK)", c, re.I)
        return m2.group(1) if m2 else "4,778"
    except: return "4,778"

def daemon_status():
    try:
        r = subprocess.run(["ps","aux"], capture_output=True, text=True)
        n = sum(1 for l in r.stdout.splitlines() if "autonomous_daemon" in l and "grep" not in l)
        return f"{n} daemon(s) activos" if n else "daemon inactivo"
    except: return "?"

def inbox_count():
    inbox = VAULT / "+Entrada"
    return len(list(inbox.glob("*.md"))) if inbox.exists() else 0

def show_status():
    asr = latest_asr()
    emoji = "🔴" if asr > 50 else "🟡" if asr > 15 else "🟢"
    print(f"\n🧠 DOF-MESH — {DATE}")
    print(f"  Último commit: {git_log().split(chr(10))[0]}")
    print(f"  Sin commitear: {uncommitted()}")
    print(f"  ASR:           {emoji} {asr:.1f}%")
    print(f"  Tests:         {test_count()}")
    print(f"  Daemon:        {daemon_status()}")
    print(f"  Vault inbox:   {inbox_count()} notas\n")

def create_note(force=False):
    d = VAULT / "Calendario" / "Diario"; d.mkdir(parents=True, exist_ok=True)
    p = d / f"{DATE}.md"
    if p.exists() and not force:
        print(f"Ya existe: {p}\n→ Usa --force"); return p
    asr = latest_asr()
    emoji = "🔴" if asr > 50 else "🟡" if asr > 15 else "🟢"
    content = f"""---
type: daily
date: {DATE}
project: DOF-MESH
status: active
tags: [diario, {DATE[:7]}]
---
# {WD} {DATE}
## 🎯 3 Prioridades
- [ ]
- [ ]
- [ ]
---
## 🤖 Estado automático ({datetime.now().strftime("%H:%M")})
| Tests | ASR | Sin commit | Daemon | Vault inbox |
|---|---|---|---|---|
| {test_count()} | {emoji} {asr:.1f}% | {uncommitted()} | {daemon_status()} | {inbox_count()} |

**Últimos commits:**
```
{git_log()}
```
---
## 📥 Capturas del día
### Observaciones
### Reacciones
### Patrones
### Números propios
---
## ✅ Hecho hoy
## 📌 Para mañana
## 💡 Ideas abiertas
"""
    p.write_text(content, encoding="utf-8")
    print(f"✅ Nota diaria: {p}")
    return p

def main():
    args = sys.argv[1:]
    if "--status" in args: show_status(); return
    create_note("--force" in args)
    show_status()

if __name__ == "__main__": main()
