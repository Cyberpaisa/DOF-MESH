#!/bin/bash
# ============================================================
# Auto Deploy to Oracle VPS
# Waits for VM IP in logs/vps_ip.txt, then provisions the full
# DOF Agent Legion system via SSH.
#
# Usage:
#   bash scripts/auto_deploy_vps.sh            # deploy
#   bash scripts/auto_deploy_vps.sh --dry-run  # print plan only
# ============================================================

set -euo pipefail

# --- Config ---
REPO_DIR="/Users/jquiceva/equipo-de-agentes"
IP_FILE="$REPO_DIR/logs/vps_ip.txt"
SSH_KEY="/Users/jquiceva/.ssh/id_ed25519"
SSH_USER="ubuntu"
VPS_DIR="/home/ubuntu/equipo-de-agentes"
LOCAL_ENV="$REPO_DIR/.env"

SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=10 -o LogLevel=ERROR"
MAX_SSH_ATTEMPTS=10
SSH_RETRY_INTERVAL=30

DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

log()  { echo -e "${GREEN}[DEPLOY]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()  { echo -e "${RED}[ERROR]${NC} $*"; }
step() { echo -e "\n${CYAN}${BOLD}==> $*${NC}"; }

# --- Allowed env vars (no Oracle passwords, no private infra secrets) ---
ALLOWED_ENV_KEYS=(
    DEEPSEEK_API_KEY
    SAMBANOVA_API_KEY
    CEREBRAS_API_KEY
    TELEGRAM_BOT_TOKEN
    QAION_WALLET_ADDRESS
    QAION_PRIVATE_KEY
    AVALANCHE_RPC_URL
)

extract_safe_env() {
    local tmpfile
    tmpfile=$(mktemp)
    for key in "${ALLOWED_ENV_KEYS[@]}"; do
        local val
        val=$(grep -E "^${key}=" "$LOCAL_ENV" 2>/dev/null | head -1 || true)
        [[ -n "$val" ]] && echo "$val" >> "$tmpfile"
    done
    echo "$tmpfile"
}

# --- Systemd unit generator ---
make_service() {
    local name="$1" desc="$2" exec_start="$3"
    cat <<UNIT
[Unit]
Description=$desc
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=$VPS_DIR
Environment=PATH=$VPS_DIR/.venv/bin:/usr/local/bin:/usr/bin:/bin
EnvironmentFile=$VPS_DIR/.env
ExecStart=$exec_start
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
UNIT
}

# ============================================================
# DRY RUN
# ============================================================
if $DRY_RUN; then
    step "DRY RUN — auto_deploy_vps.sh"
    echo ""
    echo "  1. Read VPS IP from: $IP_FILE"
    echo "  2. Wait for SSH (max ${MAX_SSH_ATTEMPTS} attempts, ${SSH_RETRY_INTERVAL}s apart)"
    echo "  3. Install system packages: python3 python3-pip python3-venv git tmux"
    echo "  4. rsync local repo to $VPS_DIR (excludes: .venv, __pycache__, .git, logs/, node_modules)"
    echo "  5. Create Python venv and install requirements.txt"
    echo "  6. Copy safe env vars: ${ALLOWED_ENV_KEYS[*]}"
    echo "  7. Create systemd services:"
    echo "     - dof-telegram.service  (interfaces/telegram_bot.py)"
    echo "     - dof-dashboard.service (scripts/streamlit_dashboard.py)"
    echo "     - dof-mesh.service      (scripts/run_mesh_agent.py)"
    echo "  8. Open firewall ports: 22, 80, 443, 8501, 8765"
    echo "  9. Enable and start all services"
    echo " 10. Print status and URLs"
    echo ""
    echo "  SSH key:  $SSH_KEY"
    echo "  SSH user: $SSH_USER"
    echo "  VPS dir:  $VPS_DIR"
    echo ""
    log "Dry run complete. No changes made."
    exit 0
fi

# ============================================================
# STEP 1 — Read IP
# ============================================================
step "Step 1: Reading VPS IP"

if [[ ! -f "$IP_FILE" ]]; then
    err "IP file not found: $IP_FILE"
    err "Run oracle_vm_grabber.sh first to provision the VM."
    exit 1
fi

VPS_IP=$(cat "$IP_FILE" | tr -d '[:space:]')

if [[ -z "$VPS_IP" ]]; then
    err "IP file is empty: $IP_FILE"
    exit 1
fi

log "VPS IP: $VPS_IP"

# ============================================================
# STEP 2 — Wait for SSH
# ============================================================
step "Step 2: Waiting for SSH on $VPS_IP"

SSH_CMD="ssh $SSH_OPTS -i $SSH_KEY ${SSH_USER}@${VPS_IP}"
ATTEMPT=0
SSH_READY=false

while [[ $ATTEMPT -lt $MAX_SSH_ATTEMPTS ]]; do
    ATTEMPT=$((ATTEMPT + 1))
    log "SSH attempt $ATTEMPT/$MAX_SSH_ATTEMPTS..."

    if $SSH_CMD "echo ssh_ok" 2>/dev/null | grep -q "ssh_ok"; then
        SSH_READY=true
        break
    fi

    if [[ $ATTEMPT -lt $MAX_SSH_ATTEMPTS ]]; then
        warn "SSH not ready. Retrying in ${SSH_RETRY_INTERVAL}s..."
        sleep "$SSH_RETRY_INTERVAL"
    fi
done

if ! $SSH_READY; then
    err "SSH never became available after $MAX_SSH_ATTEMPTS attempts."
    exit 1
fi

log "SSH connected successfully."

# ============================================================
# STEP 3 — Install system packages
# ============================================================
step "Step 3: Installing system packages"

$SSH_CMD "sudo apt update -qq && sudo apt install -y -qq python3 python3-pip python3-venv git tmux"

log "System packages installed."

# ============================================================
# STEP 4 — Rsync repo to VPS
# ============================================================
step "Step 4: Syncing codebase to VPS"

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

log "Codebase synced."

# ============================================================
# STEP 5 — Create venv and install deps
# ============================================================
step "Step 5: Setting up Python environment"

$SSH_CMD "cd $VPS_DIR && python3 -m venv .venv && .venv/bin/pip install --upgrade pip -q && .venv/bin/pip install -r requirements.txt -q"

log "Python environment ready."

# ============================================================
# STEP 6 — Copy safe env vars
# ============================================================
step "Step 6: Copying environment variables"

if [[ -f "$LOCAL_ENV" ]]; then
    SAFE_ENV=$(extract_safe_env)
    SAFE_COUNT=$(wc -l < "$SAFE_ENV" | tr -d ' ')
    log "Sending $SAFE_COUNT safe env vars (of ${#ALLOWED_ENV_KEYS[@]} allowed)"
    scp $SSH_OPTS -i "$SSH_KEY" "$SAFE_ENV" "${SSH_USER}@${VPS_IP}:${VPS_DIR}/.env"
    rm -f "$SAFE_ENV"
    log "Environment variables copied."
else
    warn "No local .env found at $LOCAL_ENV — skipping."
fi

# ============================================================
# STEP 7 — Create systemd services
# ============================================================
step "Step 7: Creating systemd services"

# Telegram bot
TELEGRAM_UNIT=$(make_service \
    "dof-telegram" \
    "DOF Telegram Bot" \
    "$VPS_DIR/.venv/bin/python3 $VPS_DIR/interfaces/telegram_bot.py")

# Streamlit dashboard
DASHBOARD_UNIT=$(make_service \
    "dof-dashboard" \
    "DOF Streamlit Dashboard" \
    "$VPS_DIR/.venv/bin/python3 -m streamlit run $VPS_DIR/scripts/streamlit_dashboard.py --server.port 8501 --server.address 0.0.0.0")

# Mesh worker
MESH_UNIT=$(make_service \
    "dof-mesh" \
    "DOF DeepSeek Mesh Worker" \
    "$VPS_DIR/.venv/bin/python3 $VPS_DIR/scripts/run_mesh_agent.py")

$SSH_CMD "sudo tee /etc/systemd/system/dof-telegram.service > /dev/null" <<< "$TELEGRAM_UNIT"
$SSH_CMD "sudo tee /etc/systemd/system/dof-dashboard.service > /dev/null" <<< "$DASHBOARD_UNIT"
$SSH_CMD "sudo tee /etc/systemd/system/dof-mesh.service > /dev/null" <<< "$MESH_UNIT"

log "Systemd service files created."

# ============================================================
# STEP 8 — Open firewall
# ============================================================
step "Step 8: Configuring firewall"

$SSH_CMD "
    sudo iptables -I INPUT -p tcp --dport 22 -j ACCEPT
    sudo iptables -I INPUT -p tcp --dport 80 -j ACCEPT
    sudo iptables -I INPUT -p tcp --dport 443 -j ACCEPT
    sudo iptables -I INPUT -p tcp --dport 8501 -j ACCEPT
    sudo iptables -I INPUT -p tcp --dport 8765 -j ACCEPT
    sudo netfilter-persistent save 2>/dev/null || true
"

log "Firewall ports opened: 22, 80, 443, 8501, 8765"

# ============================================================
# STEP 9 — Enable and start services
# ============================================================
step "Step 9: Starting services"

$SSH_CMD "
    sudo systemctl daemon-reload
    sudo systemctl enable dof-telegram dof-dashboard dof-mesh
    sudo systemctl restart dof-telegram dof-dashboard dof-mesh
"

log "All services enabled and started."

# ============================================================
# STEP 10 — Final status
# ============================================================
step "Step 10: Deployment status"

echo ""
echo "==========================================="
echo "  DOF Agent Legion — VPS Deployment Done"
echo "==========================================="
echo ""
echo "  IP:        $VPS_IP"
echo "  SSH:       ssh -i $SSH_KEY ${SSH_USER}@${VPS_IP}"
echo ""
echo "  Services:"

$SSH_CMD "
    for svc in dof-telegram dof-dashboard dof-mesh; do
        status=\$(systemctl is-active \$svc 2>/dev/null || echo 'unknown')
        printf '    %-20s %s\n' \"\$svc\" \"\$status\"
    done
"

echo ""
echo "  URLs:"
echo "    Dashboard:  http://${VPS_IP}:8501"
echo "    WebSocket:  ws://${VPS_IP}:8765"
echo "    SSH:        ssh -i $SSH_KEY ${SSH_USER}@${VPS_IP}"
echo ""
echo "==========================================="
log "Deployment complete."
