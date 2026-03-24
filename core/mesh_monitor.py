#!/usr/bin/env python3
"""
DOF Mesh Monitor - real-time monitoring of mesh nodes and messages.
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, deque
import threading
import argparse


class MeshMonitor:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.nodes_file = Path("logs/mesh/nodes.json")
        self.messages_file = Path("logs/mesh/messages.jsonl")
        self.status_file = Path("logs/mesh/monitor.jsonl")
        self.alert_callbacks = []
        self.node_status = {}
        self.message_counts = defaultdict(lambda: deque(maxlen=120))  # 60 min at 30s poll
        self.error_counts = defaultdict(lambda: deque(maxlen=120))
        self.last_check = None
        self._stop_event = threading.Event()
        self._poll_thread = None
        self._ensure_dirs()

    def _ensure_dirs(self):
        self.nodes_file.parent.mkdir(parents=True, exist_ok=True)
        self.messages_file.parent.mkdir(parents=True, exist_ok=True)
        self.status_file.parent.mkdir(parents=True, exist_ok=True)

    def register_alert_callback(self, callback):
        """Register a function to call when an alert triggers."""
        self.alert_callbacks.append(callback)

    def _call_alert_callbacks(self, alert_type, data):
        for cb in self.alert_callbacks:
            try:
                cb(alert_type, data)
            except Exception:
                pass

    def _read_nodes(self):
        if not self.nodes_file.exists():
            return {}
        try:
            with open(self.nodes_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def _read_messages(self):
        if not self.messages_file.exists():
            return []
        messages = []
        try:
            with open(self.messages_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        messages.append(json.loads(line))
        except (json.JSONDecodeError, IOError):
            pass
        return messages

    def _update_counts(self, messages):
        now = time.time()
        cutoff = now - 60  # last minute
        for node_id in list(self.message_counts.keys()):
            # trim old counts
            while (self.message_counts[node_id] and
                   self.message_counts[node_id][0][0] < cutoff):
                self.message_counts[node_id].popleft()
            while (self.error_counts[node_id] and
                   self.error_counts[node_id][0][0] < cutoff):
                self.error_counts[node_id].popleft()

        for msg in messages:
            ts = msg.get('timestamp', now)
            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts).timestamp()
                except ValueError:
                    ts = now
            node = msg.get('from_node', 'unknown')
            self.message_counts[node].append((ts, msg))
            if msg.get('status', '').upper() in ('ERROR', 'FAILED'):
                self.error_counts[node].append((ts, msg))

    def check(self):
        """Perform a single monitoring cycle."""
        nodes = self._read_nodes()
        messages = self._read_messages()
        self._update_counts(messages)
        now = datetime.now()
        self.last_check = now

        alerts = []
        for node_id, node_data in nodes.items():
            last_active = node_data.get('last_active')
            if isinstance(last_active, str):
                try:
                    last_active = datetime.fromisoformat(last_active)
                except ValueError:
                    last_active = None
            alive = False
            if last_active:
                alive = (now - last_active) < timedelta(seconds=90)
            msg_count = len(self.message_counts[node_id])
            err_count = len(self.error_counts[node_id])
            error_rate = (err_count / msg_count * 100) if msg_count > 0 else 0.0

            self.node_status[node_id] = {
                'alive': alive,
                'last_active': last_active.isoformat() if last_active else None,
                'message_rate': msg_count,  # messages per minute
                'error_rate': error_rate,
                'timestamp': now.isoformat()
            }

            if not alive:
                alerts.append({
                    'type': 'node_offline',
                    'node': node_id,
                    'last_active': last_active.isoformat() if last_active else None
                })
            if error_rate > 10.0:
                alerts.append({
                    'type': 'high_error_rate',
                    'node': node_id,
                    'error_rate': error_rate
                })

        for alert in alerts:
            self._call_alert_callbacks(alert['type'], alert)

        status_log = {
            'timestamp': now.isoformat(),
            'nodes': self.node_status,
            'alerts': alerts
        }
        try:
            with open(self.status_file, 'a') as f:
                f.write(json.dumps(status_log) + '\n')
        except IOError:
            pass

        return status_log

    def start(self, interval=30):
        """Start background polling thread."""
        if self._poll_thread and self._poll_thread.is_alive():
            return
        self._stop_event.clear()
        def poll_loop():
            while not self._stop_event.is_set():
                self.check()
                self._stop_event.wait(interval)
        self._poll_thread = threading.Thread(target=poll_loop, daemon=True)
        self._poll_thread.start()

    def stop(self):
        """Stop background polling."""
        self._stop_event.set()
        if self._poll_thread:
            self._poll_thread.join(timeout=5)

    def get_status(self):
        """Return current status dict."""
        if not self.last_check:
            self.check()
        return {
            'timestamp': self.last_check.isoformat() if self.last_check else None,
            'nodes': self.node_status
        }


def get_monitor():
    """Singleton accessor."""
    return MeshMonitor()


def print_dashboard(monitor, interval=5):
    """Print ASCII table every interval seconds."""
    try:
        while True:
            os.system('clear' if os.name == 'posix' else 'cls')
            status = monitor.check()
            print(f"DOF Mesh Monitor - {status['timestamp']}\n")
            print("Node ID           | Alive | Msgs/min | Error % | Last Active")
            print("-" * 70)
            for node_id, data in status['nodes'].items():
                alive = 'YES' if data['alive'] else 'NO'
                rate = data['message_rate']
                err = f"{data['error_rate']:.1f}"
                last = data['last_active'] or 'unknown'
                if len(last) > 16:
                    last = last[:13] + '...'
                print(f"{node_id:16} | {alive:5} | {rate:8} | {err:7} | {last}")
            if status['alerts']:
                print("\nALERTS:")
                for a in status['alerts']:
                    print(f"  - {a['type']}: {a['node']}")
            sys.stdout.flush()
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nDashboard stopped.")


def main():
    parser = argparse.ArgumentParser(description='DOF Mesh Monitor')
    parser.add_argument('--dashboard', action='store_true',
                        help='Start ASCII dashboard')
    parser.add_argument('--check', action='store_true',
                        help='Print current status and exit')
    args = parser.parse_args()

    monitor = get_monitor()
    if args.dashboard:
        print_dashboard(monitor)
    elif args.check:
        status = monitor.check()
        print(json.dumps(status, indent=2))
    else:
        monitor.start()
        print(f"Monitor started (polling every 30s). Status log: {monitor.status_file}")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            monitor.stop()
            print("Monitor stopped.")


if __name__ == '__main__':
    main()
