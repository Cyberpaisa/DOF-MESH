"""
Hyperion Shard Dashboard — DOF Mesh Mission Control.

Visualiza el estado de los 10 shards de Hyperion, la latencia P99 y la carga distribuida.
Consumo directo de HyperionBridge.status().
"""

import os
import time
import json
import logging
from pathlib import Path
from core.hyperion_bridge import HyperionBridge

# Colors for terminal
GREEN = "\033[92m"
BLUE = "\033[94m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"

logging.basicConfig(level=logging.ERROR)

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def render_shard_bar(percentage, width=20):
    filled = int(width * percentage / 100)
    bar = "█" * filled + "░" * (width - filled)
    color = GREEN if percentage < 50 else (YELLOW if percentage < 80 else RED)
    return f"{color}[{bar}] {percentage:3.0f}%{RESET}"

def main():
    bridge = HyperionBridge()
    
    try:
        while True:
            clear_screen()
            status = bridge.status()
            q_status = status.get("queue", {})
            shards = status.get("shards", {}).get("shards", [])
            dispatched = status.get("dispatched_by_node", {})
            
            print(f"{BOLD}{CYAN}═══ DOF MESH HYPERION MISSION CONTROL (LEGION MODE) ═══{RESET}")
            print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Queue Size: {BLUE}{BOLD}{q_status.get('qsize', 0)}{RESET} tasks")
            print(f"Throughput: {GREEN}{BOLD}402,000 tps (Target){RESET}")
            print("-" * 55)
            
            print(f"{BOLD}SHARD DISTRIBUTION (Raft Consensus){RESET}")
            for i, shard in enumerate(shards):
                load = (shard.get("task_count", 0) / 100) * 100 # Mock scaling
                print(f"Shard {i:02d} [{shard.get('leader', 'N/A'):10s}]: {render_shard_bar(min(100, load))}")
            
            print("-" * 55)
            print(f"{BOLD}NODE DISPATCH LOAD{RESET}")
            # Show top 5 busy nodes
            sorted_nodes = sorted(dispatched.items(), key=lambda x: x[1], reverse=True)[:5]
            for node, count in sorted_nodes:
                print(f"  {node:15s} : {YELLOW}{count:4d} tasks{RESET}")
            
            if not sorted_nodes:
                print("  Waiting for traffic...")
            
            print("-" * 55)
            print(f"{BOLD}SYSTEM FLAGS{RESET}")
            emergency_active = os.path.exists("logs/mesh/EMERGENCY_MODE_v1.json")
            print(f"  Emergency Mode : {'[ACTIVE]' if emergency_active else '[INACTIVE]'}")
            print(f"  Token Protocol : {'[CONSERVE]' if emergency_active else '[NORMAL]'}")
            
            print(f"\n{BOLD}(CTRL+C to exit dashboard, system continues in background){RESET}")
            time.sleep(1)
            
    except KeyboardInterrupt:
        print(f"\n{CYAN}Dashboard closed. Legion operating in background.{RESET}")

if __name__ == "__main__":
    main()
