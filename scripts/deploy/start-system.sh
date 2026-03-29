#!/bin/bash
# ============================================================
# DOF Agent Legion — System Startup Script v2.0
# Starts: Mission Control + Mesh Agent + Telegram + Ollama + Watchdog
# Usage: ./start-system.sh [start|stop|status|restart]
# ============================================================

REPO_DIR="$HOME/equipo-de-agentes"
WATCHDOG="$HOME/equipo-de-agentes/scripts/soul-watchdog.sh"
DAEMON="$HOME/equipo-de-agentes/scripts/agent-legion-daemon.sh"
MESH_AGENT="$HOME/equipo-de-agentes/scripts/run_mesh_agent.py"
TELEGRAM_BOT="$HOME/equipo-de-agentes/interfaces/telegram_bot.py"
PID_DIR="$HOME/.legion/.pids"
LOG_DIR="$HOME/.legion/logs"
REPO_LOG="$HOME/equipo-de-agentes/logs"

mkdir -p "$PID_DIR" "$LOG_DIR" "$REPO_LOG"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

status_icon() {
  if [ "$1" = "running" ]; then echo -e "${GREEN}●${NC}"
  elif [ "$1" = "stopped" ]; then echo -e "${RED}●${NC}"
  else echo -e "${YELLOW}●${NC}"; fi
}

# --- START ---
start_system() {
  echo ""
  echo "╔══════════════════════════════════════╗"
  echo "║   DOF Agent Legion — System Start    ║"
  echo "╚══════════════════════════════════════╝"
  echo ""

  # 1. SOUL Watchdog — init baselines + start cron check
  if [ -f "$WATCHDOG" ]; then
    bash "$WATCHDOG" init
    echo -e "  $(status_icon running) SOUL Watchdog — baselines set"

    # Check if cron job exists
    if ! crontab -l 2>/dev/null | grep -q "soul-watchdog"; then
      (crontab -l 2>/dev/null; echo "* * * * * bash \"$WATCHDOG\" check") | crontab -
      echo -e "  $(status_icon running) SOUL Watchdog — cron installed (every minute)"
    else
      echo -e "  $(status_icon running) SOUL Watchdog — cron already active"
    fi
  else
    echo -e "  $(status_icon stopped) SOUL Watchdog — script not found"
  fi

  # 4. Agent Legion Daemon — autonomous agent cycles
  if [ -f "$DAEMON" ]; then
    bash "$DAEMON" start
    echo -e "  $(status_icon running) Agent Legion — daemon started (30min cycles)"
  else
    echo -e "  $(status_icon stopped) Agent Legion — daemon script not found"
  fi

  # 5. Mesh Agent Daemon — local AI autonomous executor (new)
  if pgrep -f "run_mesh_agent.py" > /dev/null 2>&1; then
    echo -e "  $(status_icon running) Mesh Agent — already running (via LaunchAgent)"
  elif [ -f "$MESH_AGENT" ]; then
    python3 "$MESH_AGENT" > "$REPO_LOG/mesh-agent.log" 2>"$REPO_LOG/mesh-agent-error.log" &
    echo $! > "$PID_DIR/mesh-agent.pid"
    sleep 1
    echo -e "  $(status_icon running) Mesh Agent — started (autonomous executor)"
  else
    echo -e "  $(status_icon stopped) Mesh Agent — script not found"
  fi

  # 6. Telegram Bot — personal control via Telegram
  if pgrep -f "telegram_bot.py" > /dev/null 2>&1; then
    echo -e "  $(status_icon running) Telegram Bot — already running"
  elif [ -f "$TELEGRAM_BOT" ]; then
    # Kill any conflicting instance first (prevents 409 error)
    pkill -f "telegram_bot.py" 2>/dev/null
    sleep 1
    cd "$REPO_DIR" && python3 -u "$TELEGRAM_BOT" > "$REPO_LOG/telegram-bot.log" 2>&1 &
    echo $! > "$PID_DIR/telegram-bot.pid"
    sleep 2
  # 6. Telegram Bot — personal control via Telegram
  # ... (telegram bot logic)

  # 7. Ghost Watchdog — permanent Unicode surveillance
  if pgrep -f "ghost_watchdog.py" > /dev/null 2>&1; then
    echo -e "  $(status_icon running) Ghost Watchdog — already running"
  elif [ -f "/Users/jquiceva/equipo-de-agentes/scripts/ghost_watchdog.py" ]; then
    python3 "/Users/jquiceva/equipo-de-agentes/scripts/ghost_watchdog.py" > "/Users/jquiceva/equipo-de-agentes/logs/ghost_watchdog.log" 2>&1 &
    echo $! > "$PID_DIR/ghost-watchdog.pid"
    echo -e "  $(status_icon running) Ghost Watchdog — started (permanent surveillance)"
  fi

  echo ""
  echo "  Dashboard:      http://localhost:3000"
  echo "  Local Chat:     http://localhost:3000/local-chat"
  echo "  Gateway:        http://127.0.0.1:18789"
  echo ""
  echo "  Login: juan / enigma1686cyber"
  echo ""
}

# --- STOP ---
stop_system() {
  echo ""
  echo "  Stopping DOF Agent Legion..."
  echo ""

  # Stop Agent Legion daemon
  if [ -f "$DAEMON" ]; then
    bash "$DAEMON" stop
  fi
  echo -e "  $(status_icon stopped) Agent Legion — daemon stopped"

  # Stop Mesh Agent (only if not managed by LaunchAgent)
  if [ -f "$PID_DIR/mesh-agent.pid" ]; then
    kill $(cat "$PID_DIR/mesh-agent.pid") 2>/dev/null
    rm "$PID_DIR/mesh-agent.pid"
    echo -e "  $(status_icon stopped) Mesh Agent — stopped"
  fi

  # Stop Telegram Bot
  pkill -f "telegram_bot.py" 2>/dev/null
  [ -f "$PID_DIR/telegram-bot.pid" ] && rm "$PID_DIR/telegram-bot.pid"
  echo -e "  $(status_icon stopped) Telegram Bot — stopped"

  # Remove watchdog cron
  crontab -l 2>/dev/null | grep -v "soul-watchdog" | crontab -
  echo -e "  $(status_icon stopped) SOUL Watchdog — cron removed"

  echo ""
}

# --- STATUS ---
show_status() {
  echo ""
  echo "╔══════════════════════════════════════╗"
  echo "║   DOF Agent Legion — System Status   ║"
  echo "╚══════════════════════════════════════╝"
  echo ""

  # Ollama
  if lsof -ti :11434 > /dev/null 2>&1; then
    echo -e "  $(status_icon running) Ollama              :11434"
  else
    echo -e "  $(status_icon stopped) Ollama              offline"
  fi

  # Mesh Agent
  if pgrep -f "run_mesh_agent.py" > /dev/null 2>&1; then
    echo -e "  $(status_icon running) Mesh Agent          running (autonomous executor)"
  else
    echo -e "  $(status_icon stopped) Mesh Agent          offline"
  fi

  # Telegram Bot
  if pgrep -f "telegram_bot.py" > /dev/null 2>&1; then
    echo -e "  $(status_icon running) Telegram Bot        running"
  else
    echo -e "  $(status_icon stopped) Telegram Bot        offline"
  fi

  # SOUL Watchdog
  if crontab -l 2>/dev/null | grep -q "soul-watchdog"; then
    echo -e "  $(status_icon running) SOUL Watchdog       cron active"
  else
    echo -e "  $(status_icon stopped) SOUL Watchdog       not scheduled"
  fi

  # Agent count
  local models=$(curl -s http://localhost:11434/api/tags 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('models',[])))" 2>/dev/null || echo "?")
  echo ""
  echo "  Ollama models: $models"
  echo "  Sovereign Brain: ACTIVE (NPU-Sanitized)"
  echo ""

  # Firewall
  if /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate 2>/dev/null | grep -q "enabled"; then
    echo -e "  $(status_icon running) macOS Firewall      enabled"
  else
    echo -e "  $(status_icon stopped) macOS Firewall      DISABLED"
  fi

  echo ""
}

# --- MAIN ---
case "${1:-status}" in
  start)    start_system ;;
  stop)     stop_system ;;
  restart)  stop_system; sleep 2; start_system ;;
  status)   show_status ;;
  *)
    echo "Usage: $0 {start|stop|restart|status}"
    ;;
esac
