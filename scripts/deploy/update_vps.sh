#!/bin/bash
# ============================================================
# Update VPS — rsync changes + restart services
# Quick push for code updates without full re-provisioning.
#
# Usage:
#   bash scripts/update_vps.sh              # sync + restart all
#   bash scripts/update_vps.sh --code-only  # sync only, no restart
#   bash scripts/update_vps.sh --restart    # restart only, no sync
# ============================================================

set -euo pipefail

# --- Config ---
REPO_DIR="/Users/jquiceva/equipo-de-agentes"
IP_FILE="$REPO_DIR/logs/vps_ip.txt"
SSH_KEY="/Users/jquiceva/.ssh/id_ed25519"
SSH_USER="ubuntu"
VPS_DIR="/home/ubuntu/equipo-de-agentes"

SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=10 -o LogLevel=ERROR"
SSH_CMD="ssh $SSH_OPTS -i $SSH_KEY"
SERVICES="dof-telegram dof-dashboard dof-mesh"

# --- Colors ---
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

log()  { echo -e "${GREEN}[UPDATE]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()  { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }
step() { echo -e "\n${CYAN}${BOLD}==> $*${NC}"; }

# --- Parse flags ---
DO_SYNC=true
DO_RESTART=true
case "${1:-}" in
    --code-only) DO_RESTART=false ;;
    --restart)   DO_SYNC=false ;;
    "") ;;
    *) err "Unknown flag: $1. Use --code-only or --restart." ;;
esac

# --- Read IP ---
[[ ! -f "$IP_FILE" ]] && err "IP file not found: $IP_FILE"
VPS_IP=$(cat "$IP_FILE" | tr -d '[:space:]')
[[ -z "$VPS_IP" ]] && err "IP file is empty."

log "VPS: ${SSH_USER}@${VPS_IP}"

# --- Verify SSH ---
if ! $SSH_CMD "${SSH_USER}@${VPS_IP}" "echo ok" &>/dev/null; then
    err "Cannot connect via SSH. Is the VM running?"
fi

# --- Sync code ---
if $DO_SYNC; then
    step "Syncing codebase"

    rsync -azP --delete \
        -e "ssh $SSH_OPTS -i $SSH_KEY" \
        --exclude='.venv' \
        --exclude='__pycache__' \
        --exclude='.git' \
        --exclude='node_modules' \
        --exclude='logs/' \
        --exclude='.env' \
        --exclude='*.pyc' \
        --exclude='oracle_key.json' \
        "$REPO_DIR/" "${SSH_USER}@${VPS_IP}:${VPS_DIR}/"

    log "Code synced."

    # Re-install deps if requirements.txt changed
    step "Updating Python dependencies"
    $SSH_CMD "${SSH_USER}@${VPS_IP}" "cd $VPS_DIR && .venv/bin/pip install -r requirements.txt -q"
    log "Dependencies updated."
fi

# --- Restart services ---
if $DO_RESTART; then
    step "Restarting services"

    $SSH_CMD "${SSH_USER}@${VPS_IP}" "
        sudo systemctl daemon-reload
        sudo systemctl restart $SERVICES
    "

    sleep 2

    step "Service status"
    $SSH_CMD "${SSH_USER}@${VPS_IP}" "
        for svc in $SERVICES; do
            status=\$(systemctl is-active \$svc 2>/dev/null || echo 'unknown')
            printf '  %-20s %s\n' \"\$svc\" \"\$status\"
        done
    "

    log "All services restarted."
fi

echo ""
echo "  Dashboard:  http://${VPS_IP}:8501"
echo "  SSH:        ssh -i $SSH_KEY ${SSH_USER}@${VPS_IP}"
echo ""
log "Update complete."
