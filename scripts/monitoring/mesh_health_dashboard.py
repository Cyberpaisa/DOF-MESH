#!/usr/bin/env python3
"""
DOF Mesh Health Dashboard - Mission Control Edition
Advanced UI using standard Python libraries (ANSI & Unicode Box Drawing).
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# ANSI color codes & Unicode Blocks
# ---------------------------------------------------------------------------
RESET   = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"

# Tonalities
CYAN    = "\033[38;5;51m"
BLUE    = "\033[38;5;33m"
GREEN   = "\033[38;5;46m"
YELLOW  = "\033[38;5;226m"
RED     = "\033[38;5;196m"
PURPLE  = "\033[38;5;135m"
WHITE   = "\033[38;5;231m"
GRAY    = "\033[38;5;244m"

# Box drawing
TL, TR, BL, BR = "╔", "╗", "╚", "╝"
H, V = "═", "║"
L_T, R_T, T_T, B_T, M_T = "╠", "╣", "╦", "╩", "╬"
S_H, S_V = "─", "│"
S_LT, S_RT, S_TT, S_BT, S_MT = "├", "┤", "┬", "┴", "┼"

BLOCK = "█"
DARK_BLOCK = "▓"
LIGHT_BLOCK = "▒"

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR   = Path(__file__).resolve().parent
REPO_ROOT    = SCRIPT_DIR.parent
MESH_DIR     = REPO_ROOT / "logs" / "mesh"
NODES_FILE   = MESH_DIR / "nodes.json"
MESSAGES_FILE = MESH_DIR / "messages.jsonl"
EVENTS_FILE  = MESH_DIR / "mesh_events.jsonl"

def _load_json(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}

def _load_jsonl(path: Path, tail: int = 200) -> list:
    lines = []
    try:
        with path.open("r", encoding="utf-8") as fh:
            raw = fh.readlines()
        for line in raw[-tail:]:
            if line.strip():
                try:
                    lines.append(json.loads(line.strip()))
                except Exception:
                    pass
    except Exception:
        pass
    return lines

def _col(text: str, color: str) -> str:
    return f"{color}{text}{RESET}"

def _status_color(status: str) -> str:
    s = (status or "").lower()
    if s in ("active", "running"): return GREEN
    if s in ("idle", "pending"): return YELLOW
    return RED

def _infer_provider(model: str) -> str:
    m = (model or "").lower()
    if "claude" in m: return "anthropic"
    if "qwen" in m or "coder" in m or "llama" in m: return "ollama"
    if "gemini" in m: return "google"
    return "unknown"

def _rel_time(ts) -> str:
    try:
        ts = float(ts)
        if ts == 0: return "never"
        age = time.time() - ts
        if age < 60: return f"{int(age)}s ago"
        if age < 3600: return f"{int(age/60)}m ago"
        if age < 86400: return f"{int(age/3600)}h ago"
        return f"{int(age/86400)}d"
    except Exception:
        return "never"

def render_dashboard() -> str:
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    nodes = _load_json(NODES_FILE)
    events = _load_jsonl(EVENTS_FILE, tail=10)
    
    W = 110 # Total Width
    
    out = []
    out.append("\033[2J\033[H") # Clear screen
    
    # HEADER
    out.append(f"{CYAN}{TL}{H*(W-2)}{TR}{RESET}")
    title = " 🌐 DOF MESH : MISSION CONTROL "
    pad_left = (W - 2 - len(title)) // 2
    pad_right = W - 2 - len(title) - pad_left
    out.append(f"{CYAN}{V}{RESET}{BOLD}{WHITE}{' '*pad_left}{title}{' '*pad_right}{RESET}{CYAN}{V}{RESET}")
    
    subtitle = f" SYS.TIME: {now_str} | NODES: {len(nodes)} "
    pad_l2 = (W - 2 - len(subtitle)) // 2
    pad_r2 = W - 2 - len(subtitle) - pad_l2
    out.append(f"{CYAN}{V}{RESET}{GRAY}{' '*pad_l2}{subtitle}{' '*pad_r2}{RESET}{CYAN}{V}{RESET}")
    out.append(f"{CYAN}{L_T}{H*(W-2)}{R_T}{RESET}")
    
    # TABLE HEADER
    cw = [20, 10, 12, 25, 12, 12, 12] # Column widths
    headers = ["NODE ID", "STATUS", "ROLE", "SPECIALTY", "MSG ↑/↓", "LAST ACT.", "PROVIDER"]
    
    head_str = f"{CYAN}{V}{RESET} "
    for i, h in enumerate(headers):
        head_str += f"{BOLD}{CYAN}{h:<{cw[i]}}{RESET}"
        if i < len(headers)-1: head_str += f" {CYAN}{S_V}{RESET} "
    head_str += f" {CYAN}{V}{RESET}"
    out.append(head_str)
    
    # SEP
    sep_str = f"{CYAN}{L_T}{RESET}"
    for i, w in enumerate(cw):
        sep_str += f"{CYAN}{H*(w+2)}{RESET}"
        if i < len(cw)-1: sep_str += f"{CYAN}{T_T}{RESET}"
    sep_str += f"{CYAN}{R_T}{RESET}"
    # Replace the actual unicode to match inner borders
    sep_inner = f"{CYAN}{V}{RESET}" + f"{CYAN}{S_H}{RESET}".join(f"{CYAN}{S_H*(w+2)}{RESET}" for w in cw) + f"{CYAN}{V}{RESET}"
    
    out.append(f"{CYAN}{V}{RESET}" + f"{CYAN}{S_H}{RESET}".join(f"{CYAN}{S_H*(w+2)}{RESET}" for w in cw) + f"{CYAN}{V}{RESET}")
    
    # NODES
    active_count = 0
    prov_counts = {}
    
    for node_id, n in sorted(nodes.items()):
        status = (n.get("status") or "idle").lower()
        if status in ("active", "running"): active_count += 1
        
        role = str(n.get("role", "worker"))[:cw[2]]
        specialty = str(n.get("specialty") or n.get("model") or "")[:cw[3]]
        msgs = f"{n.get('messages_sent',0)}↑/{n.get('messages_received',0)}↓"
        last = _rel_time(n.get("last_active", 0))
        prov = str(n.get("provider") or _infer_provider(n.get("model", "")))[:cw[6]]
        prov_counts[prov] = prov_counts.get(prov, 0) + 1
        
        sc = _status_color(status)
        r_str = f"{CYAN}{V}{RESET} "
        r_str += f"{WHITE}{node_id[:cw[0]]:<{cw[0]}}{RESET} {CYAN}{S_V}{RESET} "
        r_str += f"{sc}{status[:cw[1]]:<{cw[1]}}{RESET} {CYAN}{S_V}{RESET} "
        r_str += f"{BLUE}{role:<{cw[2]}}{RESET} {CYAN}{S_V}{RESET} "
        r_str += f"{GRAY}{specialty:<{cw[3]}}{RESET} {CYAN}{S_V}{RESET} "
        r_str += f"{PURPLE}{msgs[:cw[4]]:<{cw[4]}}{RESET} {CYAN}{S_V}{RESET} "
        r_str += f"{GRAY}{last[:cw[5]]:<{cw[5]}}{RESET} {CYAN}{S_V}{RESET} "
        r_str += f"{CYAN}{prov:<{cw[6]}}{RESET}  {CYAN}{V}{RESET}"
        
        out.append(r_str)
        
    out.append(f"{CYAN}{L_T}{H*(W-2)}{R_T}{RESET}")
    
    # SUB-PANELS (SUMMARY & PROVIDERS)
    summary_title = " PERFORMANCE METRICS "
    out.append(f"{CYAN}{V}{RESET}{BOLD}{WHITE}{summary_title:<{W-2}}{RESET}{CYAN}{V}{RESET}")
    
    health = (active_count / len(nodes) * 100) if nodes else 0
    hc = GREEN if health > 60 else (YELLOW if health > 30 else RED)
    
    health_bar_len = 30
    filled = int((health / 100) * health_bar_len)
    bar = f"{hc}{BLOCK * filled}{GRAY}{LIGHT_BLOCK * (health_bar_len - filled)}{RESET}"
    
    summ_str = f" Nodos Activos: {active_count}/{len(nodes)}  |  Eficiencia de Malla: {hc}{health:.1f}%{RESET} {bar}"
    out.append(f"{CYAN}{V}{RESET} {summ_str:<{W-13 + (len(hc)+len(RESET)*2 + 10)}} {CYAN}{V}{RESET}")
    
    out.append(f"{CYAN}{V}{RESET}{' '*(W-2)}{CYAN}{V}{RESET}")
    out.append(f"{CYAN}{V}{RESET} {BOLD}TOP PROVIDERS:{RESET}{' '*81}{CYAN}{V}{RESET}")
    
    for p, c in sorted(prov_counts.items(), key=lambda x: -x[1])[:3]:
        pbar = f"{BLUE}{BLOCK * c}{RESET}"
        p_str = f" - {p.upper():<10} {pbar} ({c})"
        out.append(f"{CYAN}{V}{RESET} {p_str:<{W+5}} {CYAN}{V}{RESET}")
        
    out.append(f"{CYAN}{L_T}{H*(W-2)}{R_T}{RESET}")
    
    # RECENT EVENTS
    out.append(f"{CYAN}{V}{RESET}{BOLD}{WHITE} EVENT STREAM (LATEST){RESET}{' '*(W-24)}{CYAN}{V}{RESET}")
    out.append(f"{CYAN}{V}{RESET}{GRAY}{S_H*(W-2)}{RESET}{CYAN}{V}{RESET}")
    
    for ev in events[-5:]:
        ts = str(ev.get("timestamp", ""))[:19]
        action = str(ev.get("action") or ev.get("event", ""))[:20]
        node = str(ev.get("node_id") or "")[:20]
        dets = str(ev.get("details") or ev.get("status") or "")[:40]
        
        ev_str = f" {GRAY}{ts:<20}{RESET} {CYAN}{action:<20}{RESET} {WHITE}{node:<20}{RESET} {GRAY}{dets:<40}{RESET}"
        out.append(f"{CYAN}{V}{RESET}{ev_str:<{W+26}}{CYAN}{V}{RESET}")

    out.append(f"{CYAN}{BL}{H*(W-2)}{BR}{RESET}")
    
    return "\n".join(out)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch", action="store_true", default=True)
    parser.add_argument("--once", action="store_true", default=False)
    args = parser.parse_args()

    if args.once:
        print(render_dashboard())
        return

    try:
        while True:
            print(render_dashboard())
            time.sleep(2)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Terminated Mission Control.{RESET}\n")

if __name__ == "__main__":
    main()
