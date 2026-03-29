#!/bin/bash
# ============================================================
# sovereign_watchdog.sh — Legion Mesh Sovereignty Guard
# Purpose: Monitor cloud nodes and fallback to local fortress
# ============================================================

MESH_NODES="/Users/jquiceva/equipo-de-agentes/logs/mesh/nodes.json"
LOG_FILE="/Users/jquiceva/.openclaw/logs/sovereign-watchdog.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

check_mesh_health() {
    # Watchdog solo asegura que la Fortaleza Local esté activa como respaldo.
    # NO modifica el estatus de los nodos cloud por orden del Soberano.
    
    local_agi=$(python3 -c "import json; d=json.load(open('$MESH_NODES')); print(d.get('local-agi-m4max', {}).get('status', 'offline'))")
    
    if [ "$local_agi" != "active" ]; then
        log "Asegurando actividad de la Fortaleza Local (M4 Max)..."
        python3 -c "import json; d=json.load(open('$MESH_NODES')); d['local-agi-m4max']['status'] = 'active'; json.dump(d, open('$MESH_NODES', 'w'), indent=2)"
    fi
}

# --- Main Loop ---
log "Sovereign Watchdog ACITVATED. Ensuring Local-First AGI..."
while true; do
    check_mesh_health
    sleep 60
done
