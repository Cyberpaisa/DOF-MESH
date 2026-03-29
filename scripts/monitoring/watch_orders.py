#!/usr/bin/env python3
"""
Watch Orders — Monitor Telegram → Claude Code command queue.

Polls logs/commander/queue/ for new orders from Telegram /claude commands.
Shows them in real-time so the active Claude Code session can act on them.

Usage:
    python3 scripts/watch_orders.py           # Watch for new orders
    python3 scripts/watch_orders.py --once    # Check once and exit
    python3 scripts/watch_orders.py --list    # List all orders
"""

import json
import os
import sys
import time
from pathlib import Path

QUEUE_DIR = Path(__file__).parent.parent / "logs" / "commander" / "queue"


def list_orders(status_filter=None):
    """List all orders in the queue."""
    if not QUEUE_DIR.exists():
        print("No queue directory found.")
        return []

    orders = []
    for f in sorted(QUEUE_DIR.glob("*.json")):
        try:
            with open(f) as fh:
                order = json.load(fh)
                if status_filter is None or order.get("status") == status_filter:
                    orders.append(order)
        except Exception:
            pass
    return orders


def show_order(order):
    """Display an order nicely."""
    status_icon = {
        "pending": "🟡",
        "completed": "✅",
        "error": "❌",
        "in_progress": "🔄",
    }.get(order.get("status", "?"), "❓")

    print(f"\n{'='*60}")
    print(f"{status_icon} Order: {order.get('id', '?')}")
    print(f"   From: {order.get('from', '?')} (chat {order.get('chat_id', '?')})")
    print(f"   Time: {order.get('iso', '?')}")
    print(f"   Status: {order.get('status', '?')}")
    print(f"   Instruction: {order.get('instruction', '?')}")
    if order.get("result"):
        print(f"   Result: {order['result'][:200]}...")
    if order.get("elapsed_ms"):
        print(f"   Elapsed: {order['elapsed_ms']:.0f}ms")
    if order.get("error"):
        print(f"   Error: {order['error']}")
    print(f"{'='*60}")


def watch(interval=2):
    """Watch for new orders in real-time."""
    print(f"👁  Watching {QUEUE_DIR} for Telegram orders...")
    print(f"   Send /claude <order> from Telegram to see it here.")
    print(f"   Press Ctrl+C to stop.\n")

    seen = set()
    # Mark existing as seen
    if QUEUE_DIR.exists():
        for f in QUEUE_DIR.glob("*.json"):
            seen.add(f.name)

    try:
        while True:
            if QUEUE_DIR.exists():
                for f in sorted(QUEUE_DIR.glob("*.json")):
                    if f.name not in seen:
                        seen.add(f.name)
                        try:
                            with open(f) as fh:
                                order = json.load(fh)
                            show_order(order)
                        except Exception as e:
                            print(f"Error reading {f}: {e}")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopped watching.")


if __name__ == "__main__":
    if "--list" in sys.argv:
        orders = list_orders()
        if not orders:
            print("No orders in queue.")
        for o in orders:
            show_order(o)
    elif "--pending" in sys.argv:
        orders = list_orders("pending")
        if not orders:
            print("No pending orders.")
        for o in orders:
            show_order(o)
    elif "--once" in sys.argv:
        orders = list_orders("pending")
        if not orders:
            print("No pending orders.")
        else:
            for o in orders:
                show_order(o)
    else:
        watch()
