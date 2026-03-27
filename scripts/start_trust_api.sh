#!/bin/bash
# start_trust_api.sh — Arranca el servicio Trust Score API
# Cyber Paisa / Enigma Group — DOF Mesh Legion
cd "$(dirname "$0")/.."
PYTHONPATH=. python3 interfaces/trust_api.py --port ${PORT:-8004}
