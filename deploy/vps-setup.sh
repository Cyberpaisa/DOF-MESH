#!/bin/bash
# ═══════════════════════════════════════════════════════
# DOF VPS SETUP — Oracle Cloud Always Free (ARM Ampere)
# One command to deploy the entire DOF system
# Usage: ssh ubuntu@<VPS_IP> 'bash -s' < deploy/vps-setup.sh
# ═══════════════════════════════════════════════════════

set -e
echo "🛡️ DOF VPS Setup — Starting..."

# --- System packages ---
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-pip python3-venv git tmux htop curl jq unzip \
    chromium-browser chromium-chromedriver nginx certbot python3-certbot-nginx

# --- Clone repo ---
cd /home/ubuntu
if [ ! -d "equipo-de-agentes" ]; then
    echo "Cloning DOF repo..."
    git clone https://github.com/jquiceva/equipo-de-agentes.git || {
        echo "Git clone failed — will use rsync from local"
        mkdir -p equipo-de-agentes
    }
fi
cd equipo-de-agentes

# --- Python venv ---
python3 -m venv .venv
source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet web3 requests pyyaml playwright

# --- Install Playwright browsers (headless chromium for ARM) ---
python3 -m playwright install chromium 2>/dev/null || echo "Playwright browser install skipped (will use system chromium)"

# --- Create .env (will be filled manually or via scp) ---
if [ ! -f ".env" ]; then
    cat > .env << 'ENVEOF'
# DOF VPS Environment — fill these values
DEEPSEEK_API_KEY=
SAMBANOVA_API_KEY=
TELEGRAM_BOT_TOKEN=
QAION_WALLET_ADDRESS=0x2cF7AA66EA78DEd173184476B32faa3754e0A349
QAION_PRIVATE_KEY=
AVALANCHE_RPC_URL=https://api.avax.network/ext/bc/C/rpc
GEMINI_API_KEY=
TAVILY_API_KEY=
ENVEOF
    echo "⚠️  .env created — fill API keys before starting services!"
fi

# --- Create systemd services ---

# 1. Telegram Bot (always on)
sudo tee /etc/systemd/system/dof-telegram.service > /dev/null << 'EOF'
[Unit]
Description=DOF Telegram Bot (DeepSeek)
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/equipo-de-agentes
ExecStart=/home/ubuntu/equipo-de-agentes/.venv/bin/python3 -u deploy/telegram-cloud/bot.py
Restart=always
RestartSec=5
Environment=PATH=/home/ubuntu/equipo-de-agentes/.venv/bin:/usr/bin
EnvironmentFile=/home/ubuntu/equipo-de-agentes/.env

[Install]
WantedBy=multi-user.target
EOF

# 2. Streamlit Dashboard
sudo tee /etc/systemd/system/dof-dashboard.service > /dev/null << 'EOF'
[Unit]
Description=DOF Streamlit Dashboard
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/equipo-de-agentes
ExecStart=/home/ubuntu/equipo-de-agentes/.venv/bin/python3 -m streamlit run interfaces/streamlit_dashboard.py --server.port 8501 --server.headless true --server.address 0.0.0.0
Restart=always
RestartSec=5
EnvironmentFile=/home/ubuntu/equipo-de-agentes/.env

[Install]
WantedBy=multi-user.target
EOF

# 3. Mesh Orchestrator
sudo tee /etc/systemd/system/dof-mesh.service > /dev/null << 'EOF'
[Unit]
Description=DOF Mesh Orchestrator + Hyperion
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/equipo-de-agentes
ExecStart=/home/ubuntu/equipo-de-agentes/.venv/bin/python3 -u core/hyperion_http.py
Restart=always
RestartSec=10
EnvironmentFile=/home/ubuntu/equipo-de-agentes/.env

[Install]
WantedBy=multi-user.target
EOF

# --- Enable services ---
sudo systemctl daemon-reload
sudo systemctl enable dof-telegram dof-dashboard dof-mesh

# --- Nginx reverse proxy for dashboard ---
sudo tee /etc/nginx/sites-available/dof > /dev/null << 'EOF'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 86400;
    }

    location /api/mesh/ {
        proxy_pass http://127.0.0.1:8765/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/dof /etc/nginx/sites-enabled/dof
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx

# --- Create deploy script for updates ---
cat > /home/ubuntu/update-dof.sh << 'UPDEOF'
#!/bin/bash
cd /home/ubuntu/equipo-de-agentes
git pull origin main
source .venv/bin/activate
pip install --quiet -r requirements.txt 2>/dev/null
sudo systemctl restart dof-telegram dof-dashboard dof-mesh
echo "✅ DOF updated and restarted"
UPDEOF
chmod +x /home/ubuntu/update-dof.sh

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  ✅ DOF VPS SETUP COMPLETE"
echo "═══════════════════════════════════════════════════════"
echo ""
echo "  Next steps:"
echo "  1. Fill .env with API keys: nano /home/ubuntu/equipo-de-agentes/.env"
echo "  2. Start services: sudo systemctl start dof-telegram dof-dashboard dof-mesh"
echo "  3. Dashboard: http://<VPS_IP>/"
echo "  4. Update: ./update-dof.sh"
echo ""
echo "  Services:"
echo "    systemctl status dof-telegram"
echo "    systemctl status dof-dashboard"
echo "    systemctl status dof-mesh"
echo ""
