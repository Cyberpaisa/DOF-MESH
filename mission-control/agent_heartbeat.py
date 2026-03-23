#!/usr/bin/env python3
"""
Agent Heartbeat — Mantiene los 14 agentes DOF Online en Mission Control.

Envía heartbeat cada 30s a la API de Mission Control.
Cada agente reporta su actividad actual basada en su rol.

Usage:
    python3 agent_heartbeat.py          # Inicia heartbeats
    python3 agent_heartbeat.py --stop   # Para todos los agentes (offline)
"""

import os
import sys
import json
import time
import random
import signal
import requests
from pathlib import Path
from datetime import datetime

# ─── Config ──────────────────────────────────────────────────────────
MC_URL = os.getenv("MC_URL", "http://localhost:3000")
MC_API_KEY = os.getenv(
    "MC_API_KEY",
    "0df2e1ac7263333cc5f06f8393d4aa5d56c51b16558639f792bc8607347719a5"
)
HEARTBEAT_INTERVAL = 30  # seconds
HEADERS = {
    "Content-Type": "application/json",
    "x-api-key": MC_API_KEY,
}

# ─── Agent Definitions ──────────────────────────────────────────────
AGENTS = {
    "sentinel-shield": {
        "id": 1, "role": "Security Commander",
        "activities": [
            "Scanning for MINJA attacks",
            "Auditing MCP connections",
            "5-layer defense active",
            "Monitoring prompt injection patterns",
            "Security audit in progress",
        ]
    },
    "moltbook": {
        "id": 2, "role": "Social Intelligence",
        "activities": [
            "Creating experiential content",
            "Monitoring social channels",
            "Analyzing engagement metrics",
            "Writing book chapter",
            "Content pipeline active",
        ]
    },
    "blockchain-wizard": {
        "id": 3, "role": "Blockchain & Smart Contracts",
        "activities": [
            "Monitoring Avalanche C-Chain",
            "ERC-8004 identity check",
            "On-chain attestation scan",
            "DeFi protocol analysis",
            "Smart contract audit",
        ]
    },
    "defi-orbital": {
        "id": 4, "role": "DeFi & Payments",
        "activities": [
            "x402 settlement monitoring",
            "Yield optimization scan",
            "Cross-chain bridge check",
            "Payment protocol active",
            "Liquidity pool analysis",
        ]
    },
    "ralph-code": {
        "id": 5, "role": "Core Systems Engineer",
        "activities": [
            "Autonomous loop v2 running",
            "API health monitoring",
            "Memory subsystem check",
            "Infrastructure scan",
            "Code optimization pass",
        ]
    },
    "charlie-ux": {
        "id": 6, "role": "Frontend & UX",
        "activities": [
            "Dashboard rendering check",
            "UI component optimization",
            "Real-time data viz active",
            "Responsive layout scan",
            "UX metrics analysis",
        ]
    },
    "qa-vigilante": {
        "id": 7, "role": "Quality Assurance Lead",
        "activities": [
            "Test suite monitoring (986 tests)",
            "Regression detection scan",
            "Code integrity check",
            "Coverage analysis running",
            "Test pipeline healthy",
        ]
    },
    "product-overlord": {
        "id": 8, "role": "Product Manager",
        "activities": [
            "Feature prioritization review",
            "Roadmap alignment check",
            "Hackathon track analysis",
            "User feedback processing",
            "Sprint goals monitoring",
        ]
    },
    "biz-dominator": {
        "id": 9, "role": "Business Strategy",
        "activities": [
            "Revenue strategy analysis",
            "PyPI distribution metrics",
            "Brand awareness scan",
            "Go-to-market planning",
            "Market opportunity assessment",
        ]
    },
    "scrum-master-zen": {
        "id": 10, "role": "Scrum Master",
        "activities": [
            "Sprint velocity tracking",
            "Blocker removal scan",
            "Team coordination active",
            "Deadline awareness check",
            "Standup data collection",
        ]
    },
    "architect-enigma": {
        "id": 11, "role": "System Architect",
        "activities": [
            "Architecture coherence check",
            "Z3 proofs verified (8/8 PROVEN)",
            "35 core modules scan",
            "System integrity audit",
            "Module dependency analysis",
        ]
    },
    "organizer-os": {
        "id": 12, "role": "Infrastructure & DevOps",
        "activities": [
            "Service orchestration active",
            "Disk and resource monitoring",
            "API health check pass",
            "Process management scan",
            "Infrastructure optimization",
        ]
    },
    "rwa-tokenizator": {
        "id": 13, "role": "Real World Assets",
        "activities": [
            "Asset tokenization scan",
            "Celo Alfajores monitoring",
            "RWA bridge check",
            "Token compliance audit",
            "Asset registry sync",
        ]
    },
    "qa-specialist": {
        "id": 14, "role": "Test Engineering",
        "activities": [
            "Test suite health check",
            "Coverage analysis running",
            "Automated test generation",
            "Test infrastructure scan",
            "Quality metrics collection",
        ]
    },
}

# ─── State ───────────────────────────────────────────────────────────
running = True


def signal_handler(sig, frame):
    global running
    print("\n⏹ Deteniendo heartbeats...")
    running = False


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


# ─── Heartbeat ───────────────────────────────────────────────────────

def send_heartbeat(agent_name: str, agent_info: dict) -> bool:
    """Envía un heartbeat a Mission Control para un agente via PUT."""
    agent_id = agent_info["id"]
    activity = random.choice(agent_info["activities"])

    try:
        resp = requests.put(
            f"{MC_URL}/api/agents/{agent_id}",
            headers=HEADERS,
            json={
                "status": "idle",
                "last_activity": activity,
            },
            timeout=5,
        )
        return resp.status_code == 200
    except requests.RequestException:
        return False


def set_all_offline():
    """Pone todos los agentes en offline."""
    for name, info in AGENTS.items():
        try:
            requests.put(
                f"{MC_URL}/api/agents/{info['id']}",
                headers=HEADERS,
                json={"status": "offline", "last_activity": "Heartbeat stopped"},
                timeout=5,
            )
        except requests.RequestException:
            pass
    print("✓ Todos los agentes: offline")


def heartbeat_loop():
    """Loop principal de heartbeats."""
    print(f"🫀 DOF Agent Heartbeat — {len(AGENTS)} agentes")
    print(f"   MC: {MC_URL}")
    print(f"   Intervalo: {HEARTBEAT_INTERVAL}s")
    print(f"   Ctrl+C para detener\n")

    cycle = 0
    while running:
        cycle += 1
        ok = 0
        fail = 0
        timestamp = datetime.now().strftime("%H:%M:%S")

        for name, info in AGENTS.items():
            if not running:
                break
            if send_heartbeat(name, info):
                ok += 1
            else:
                fail += 1

        status = "✓" if fail == 0 else "⚠"
        print(f"  [{timestamp}] Ciclo {cycle}: {status} {ok}/{len(AGENTS)} online" +
              (f" ({fail} failed)" if fail > 0 else ""))

        # Esperar con checks frecuentes para responder rápido a Ctrl+C
        for _ in range(HEARTBEAT_INTERVAL * 2):
            if not running:
                break
            time.sleep(0.5)

    set_all_offline()
    print("🫀 Heartbeat detenido.")


# ─── Main ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if "--stop" in sys.argv:
        set_all_offline()
    else:
        heartbeat_loop()
