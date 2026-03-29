#!/usr/bin/env python3
"""
DOF Mesh Status — Quick single-run status check.
Reads all mesh state files and emits a JSON summary or ASCII table.

Usage:
    python3 scripts/mesh_status.py                  # JSON output
    python3 scripts/mesh_status.py --format table   # ASCII table
    python3 scripts/mesh_status.py --check          # exit 0=healthy, 1=degraded
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR    = Path(__file__).resolve().parent
REPO_ROOT     = SCRIPT_DIR.parent
MESH_DIR      = REPO_ROOT / "logs" / "mesh"
NODES_FILE    = MESH_DIR / "nodes.json"
MESSAGES_FILE = MESH_DIR / "messages.jsonl"
EVENTS_FILE   = MESH_DIR / "mesh_events.jsonl"

# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict | list | None:
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _load_jsonl(path: Path, tail: int = 1000) -> list[dict]:
    lines: list[dict] = []
    try:
        with path.open("r", encoding="utf-8") as fh:
            raw = fh.readlines()
        for line in raw[-tail:]:
            line = line.strip()
            if not line:
                continue
            try:
                lines.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    except FileNotFoundError:
        pass
    return lines


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_active(status: str) -> bool:
    return (status or "").lower() in ("active", "running")


def _infer_provider(model: str) -> str:
    model = (model or "").lower()
    if model.startswith("claude"):
        return "anthropic"
    if "ollama:" in model or "qwen" in model:
        return "ollama"
    return "unknown"


def _provider_breakdown(nodes: dict) -> dict[str, int]:
    breakdown: dict[str, int] = {}
    for n in nodes.values():
        provider = n.get("provider") or _infer_provider(n.get("model", ""))
        breakdown[provider] = breakdown.get(provider, 0) + 1
    return breakdown


def _last_event(events: list[dict]) -> str:
    if not events:
        return "none"
    last = events[-1]
    return last.get("event") or last.get("iso") or str(last.get("timestamp", "unknown"))


def _message_rate(messages: list[dict], window: int = 300) -> float:
    """Messages per minute in the last *window* seconds."""
    now = time.time()
    cutoff = now - window
    recent = sum(
        1 for m in messages
        if _to_float(m.get("timestamp", 0)) >= cutoff
    )
    return recent * (60.0 / window)


def _to_float(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


# ---------------------------------------------------------------------------
# Build summary dict
# ---------------------------------------------------------------------------

def build_summary() -> dict:
    nodes    = _load_json(NODES_FILE) or {}
    messages = _load_jsonl(MESSAGES_FILE)
    events   = _load_jsonl(EVENTS_FILE)

    total        = len(nodes)
    active_nodes = [nid for nid, n in nodes.items() if _is_active(n.get("status", ""))]
    active_count = len(active_nodes)
    health_pct   = round((active_count / total * 100) if total else 0.0, 1)
    breakdown    = _provider_breakdown(nodes)

    return {
        "timestamp":          datetime.now(timezone.utc).isoformat(),
        "node_count":         total,
        "active_nodes":       active_count,
        "active_node_ids":    sorted(active_nodes),
        "message_count":      len(messages),
        "message_rate_per_min": round(_message_rate(messages), 2),
        "event_count":        len(events),
        "last_event":         _last_event(events),
        "health_percentage":  health_pct,
        "healthy":            health_pct > 50.0,
        "provider_breakdown": breakdown,
        "data_dir":           str(MESH_DIR),
    }


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------

def _print_json(summary: dict) -> None:
    print(json.dumps(summary, indent=2, ensure_ascii=False))


def _print_table(summary: dict) -> None:
    """Print a clean ASCII table without external dependencies."""
    sep = "+" + "-" * 36 + "+" + "-" * 36 + "+"
    fmt = "| {:<34} | {:<34} |"

    rows = [
        ("Timestamp",           summary["timestamp"]),
        ("Node Count",          str(summary["node_count"])),
        ("Active Nodes",        str(summary["active_nodes"])),
        ("Active Node IDs",     ", ".join(summary["active_node_ids"]) or "none"),
        ("Message Count",       str(summary["message_count"])),
        ("Message Rate (/min)", str(summary["message_rate_per_min"])),
        ("Event Count",         str(summary["event_count"])),
        ("Last Event",          str(summary["last_event"])[:34]),
        ("Health %",            f"{summary['health_percentage']}%"),
        ("Healthy",             "YES" if summary["healthy"] else "NO"),
        ("Data Directory",      str(summary["data_dir"])[:34]),
    ]

    print(sep)
    print(fmt.format("FIELD", "VALUE"))
    print(sep)
    for field, value in rows:
        # Long values: wrap across extra rows
        while len(value) > 34:
            print(fmt.format(field, value[:34]))
            field = ""
            value = value[34:]
        print(fmt.format(field, value))
    print(sep)

    # Provider breakdown sub-table
    breakdown = summary.get("provider_breakdown", {})
    if breakdown:
        print()
        sep2 = "+" + "-" * 20 + "+" + "-" * 10 + "+"
        fmt2 = "| {:<18} | {:>8} |"
        print(sep2)
        print(fmt2.format("PROVIDER", "NODES"))
        print(sep2)
        for provider, count in sorted(breakdown.items(), key=lambda x: -x[1]):
            print(fmt2.format(provider[:18], count))
        print(sep2)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="DOF Mesh Status — quick single-run status check"
    )
    parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="json",
        help="Output format: json (default) or table",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        default=False,
        help="Exit 0 if healthy (>50%% nodes active), 1 otherwise",
    )
    args = parser.parse_args()

    summary = build_summary()

    if not args.check:
        if args.format == "table":
            _print_table(summary)
        else:
            _print_json(summary)

    if args.check:
        healthy = summary["healthy"]
        if not healthy:
            # Still print a brief status even in --check mode
            active  = summary["active_nodes"]
            total   = summary["node_count"]
            health  = summary["health_percentage"]
            print(
                f"DEGRADED: {active}/{total} nodes active ({health}%)",
                file=sys.stderr,
            )
            sys.exit(1)
        else:
            active  = summary["active_nodes"]
            total   = summary["node_count"]
            health  = summary["health_percentage"]
            print(f"OK: {active}/{total} nodes active ({health}%)")
            sys.exit(0)


if __name__ == "__main__":
    main()
