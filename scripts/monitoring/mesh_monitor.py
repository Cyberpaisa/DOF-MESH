#!/usr/bin/env python3
"""
DOF Mesh Monitor — Real-time mesh dashboard.
Reads logs/mesh/ and displays node status, message stats, events, and health.

Usage:
    python3 scripts/mesh_monitor.py          # single snapshot
    python3 scripts/mesh_monitor.py --live   # refresh every 5 seconds
    python3 scripts/mesh_monitor.py --json   # raw JSON output
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Resolve paths relative to repo root (parent of scripts/)
REPO_ROOT = Path(__file__).resolve().parent.parent
MESH_DIR = REPO_ROOT / "logs" / "mesh"
NODES_FILE = MESH_DIR / "nodes.json"
MESSAGES_FILE = MESH_DIR / "messages.jsonl"
EVENTS_FILE = MESH_DIR / "mesh_events.jsonl"
INBOX_DIR = MESH_DIR / "inbox"


# ── Data loaders ─────────────────────────────────────────────────────────────

def load_nodes() -> dict:
    """Load nodes.json → dict[node_id, node_data]."""
    if not NODES_FILE.exists():
        return {}
    try:
        with open(NODES_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def load_jsonl(path: Path) -> list[dict]:
    """Load a JSONL file → list of dicts."""
    if not path.exists():
        return []
    records = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def count_inbox(node_id: str) -> int:
    """Count pending messages in inbox/{node_id}/."""
    inbox = INBOX_DIR / node_id
    if not inbox.is_dir():
        return 0
    return len([f for f in inbox.iterdir() if f.is_file()])


# ── Stats computation ────────────────────────────────────────────────────────

def compute_stats() -> dict:
    nodes = load_nodes()
    messages = load_jsonl(MESSAGES_FILE)
    events = load_jsonl(EVENTS_FILE)

    # Per-node message counts from messages.jsonl
    sent_counts: dict[str, int] = {}
    recv_counts: dict[str, int] = {}
    for msg in messages:
        sender = msg.get("from_node", "?")
        receiver = msg.get("to_node", "?")
        sent_counts[sender] = sent_counts.get(sender, 0) + 1
        recv_counts[receiver] = recv_counts.get(receiver, 0) + 1

    # Inbox pending
    inbox_counts: dict[str, int] = {}
    if INBOX_DIR.is_dir():
        for d in INBOX_DIR.iterdir():
            if d.is_dir():
                inbox_counts[d.name] = len([f for f in d.iterdir() if f.is_file()])

    # Earliest timestamp for uptime
    all_timestamps = []
    for ev in events:
        ts = ev.get("timestamp")
        if isinstance(ts, (int, float)):
            all_timestamps.append(ts)
    for n in nodes.values():
        ts = n.get("created_at")
        if isinstance(ts, (int, float)):
            all_timestamps.append(ts)

    uptime_seconds = 0
    if all_timestamps:
        uptime_seconds = time.time() - min(all_timestamps)

    # Last 5 messages
    last_5 = messages[-5:] if messages else []

    # Last 10 events
    last_10_events = events[-10:] if events else []

    # Health summary
    statuses = {}
    for nid, ndata in nodes.items():
        statuses[ndata.get("status", "unknown")] = statuses.get(ndata.get("status", "unknown"), 0) + 1

    return {
        "nodes": nodes,
        "total_messages": len(messages),
        "total_events": len(events),
        "sent_counts": sent_counts,
        "recv_counts": recv_counts,
        "inbox_counts": inbox_counts,
        "uptime_seconds": uptime_seconds,
        "last_5_messages": last_5,
        "last_10_events": last_10_events,
        "status_summary": statuses,
    }


# ── Formatting helpers ───────────────────────────────────────────────────────

def fmt_duration(seconds: float) -> str:
    if seconds <= 0:
        return "N/A"
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    mins = int((seconds % 3600) // 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    parts.append(f"{mins}m")
    return " ".join(parts)


def fmt_timestamp(ts) -> str:
    """Format a timestamp (float or ISO string) to readable form."""
    if isinstance(ts, (int, float)):
        try:
            return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        except (OSError, ValueError):
            return str(ts)
    if isinstance(ts, str):
        return ts[:19]  # trim to seconds
    return "?"


def truncate(s: str, maxlen: int = 60) -> str:
    s = s.replace("\n", " ").strip()
    if len(s) > maxlen:
        return s[:maxlen - 3] + "..."
    return s


# ── ASCII rendering ─────────────────────────────────────────────────────────

def render_table(stats: dict) -> str:
    lines: list[str] = []

    nodes = stats["nodes"]
    total_msg = stats["total_messages"]
    total_ev = stats["total_events"]
    uptime = fmt_duration(stats["uptime_seconds"])

    # Header box
    title = "DOF MESH MONITOR -- LIVE STATUS"
    w = 62
    lines.append("")
    lines.append("+" + "=" * w + "+")
    lines.append("|" + title.center(w) + "|")
    lines.append("+" + "=" * w + "+")
    summary = f" Nodes: {len(nodes)} | Messages: {total_msg} | Events: {total_ev} | Uptime: {uptime} "
    lines.append("|" + summary.center(w) + "|")
    lines.append("+" + "=" * w + "+")
    lines.append("")

    # ── Node table ───────────────────────────────────────────────────────
    lines.append("  NODES")
    lines.append("  " + "-" * 78)
    hdr = f"  {'NODE':<16} {'STATUS':<10} {'MODEL':<24} {'IN/OUT':<10} {'INBOX':<6}"
    lines.append(hdr)
    lines.append("  " + "-" * 78)

    for nid, ndata in sorted(nodes.items()):
        status = ndata.get("status", "?")
        model = ndata.get("model", "?")
        msgs_in = ndata.get("messages_received", 0)
        msgs_out = ndata.get("messages_sent", 0)
        inbox = stats["inbox_counts"].get(nid, 0)
        row = f"  {nid:<16} {status:<10} {model:<24} {msgs_in}/{msgs_out:<8} {inbox}"
        lines.append(row)

    lines.append("")

    # ── Message stats ────────────────────────────────────────────────────
    lines.append("  MESSAGE STATS (from messages.jsonl)")
    lines.append("  " + "-" * 50)
    all_node_ids = sorted(set(list(stats["sent_counts"].keys()) + list(stats["recv_counts"].keys())))
    for nid in all_node_ids:
        s = stats["sent_counts"].get(nid, 0)
        r = stats["recv_counts"].get(nid, 0)
        lines.append(f"    {nid:<16}  sent: {s:<5}  recv: {r}")
    lines.append("")

    # ── Last 5 messages ──────────────────────────────────────────────────
    lines.append("  LAST 5 MESSAGES")
    lines.append("  " + "-" * 78)
    for msg in stats["last_5_messages"]:
        ts = fmt_timestamp(msg.get("timestamp"))
        fr = msg.get("from_node", "?")
        to = msg.get("to_node", "?")
        content = truncate(msg.get("content", ""), 50)
        lines.append(f"    [{ts}] {fr} -> {to}: {content}")
    if not stats["last_5_messages"]:
        lines.append("    (none)")
    lines.append("")

    # ── Last 10 events ───────────────────────────────────────────────────
    lines.append("  LAST 10 EVENTS")
    lines.append("  " + "-" * 78)
    for ev in stats["last_10_events"]:
        ts = fmt_timestamp(ev.get("timestamp", ev.get("iso", "?")))
        event_type = ev.get("event", "?")
        node = ev.get("node_id", ev.get("commander", ""))
        status = ev.get("status", "")
        detail = f"{event_type}"
        if node:
            detail += f" [{node}]"
        if status:
            detail += f" ({status})"
        lines.append(f"    [{ts}] {detail}")
    if not stats["last_10_events"]:
        lines.append("    (none)")
    lines.append("")

    # ── Health summary ───────────────────────────────────────────────────
    lines.append("  HEALTH SUMMARY")
    lines.append("  " + "-" * 40)
    for status, count in sorted(stats["status_summary"].items()):
        lines.append(f"    {status:<16} {count} node(s)")
    lines.append("")

    return "\n".join(lines)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="DOF Mesh Monitor — real-time mesh dashboard")
    parser.add_argument("--live", action="store_true", help="Refresh every 5 seconds")
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of table")
    args = parser.parse_args()

    if not MESH_DIR.is_dir():
        print(f"ERROR: Mesh directory not found: {MESH_DIR}")
        sys.exit(1)

    if args.live:
        try:
            while True:
                os.system("clear")
                stats = compute_stats()
                if args.json:
                    # Remove non-serializable bits
                    print(json.dumps(stats, indent=2, default=str))
                else:
                    print(render_table(stats))
                    print(f"  [auto-refresh 5s — Ctrl+C to exit]")
                time.sleep(5)
        except KeyboardInterrupt:
            print("\n  Monitor stopped.")
    else:
        stats = compute_stats()
        if args.json:
            print(json.dumps(stats, indent=2, default=str))
        else:
            print(render_table(stats))


if __name__ == "__main__":
    main()
