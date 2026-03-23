#!/bin/bash
# ============================================================
# DOF Agent Legion — System Startup Script
# Starts: Mission Control + OpenClaw Gateway + SOUL Watchdog
# Usage: ./start-system.sh [start|stop|status|restart]
# ============================================================

MC_DIR="$HOME/equipo de agentes/mission-control"
WATCHDOG="$HOME/equipo de agentes/scripts/soul-watchdog.sh"
DAEMON="$HOME/equipo de agentes/scripts/agent-legion-daemon.sh"
PID_DIR="$HOME/.openclaw/.pids"
LOG_DIR="$HOME/.openclaw/logs"

mkdir -p "$PID_DIR" "$LOG_DIR"

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

  # 1. OpenClaw Gateway
  if lsof -ti :18789 > /dev/null 2>&1; then
    echo -e "  $(status_icon running) OpenClaw Gateway — already running"
  else
    echo -e "  $(status_icon stopped) OpenClaw Gateway — starting..."
    openclaw gateway start > "$LOG_DIR/gateway.log" 2>&1 &
    sleep 2
    if lsof -ti :18789 > /dev/null 2>&1; then
      echo -e "  $(status_icon running) OpenClaw Gateway — started on :18789"
    else
      echo -e "  $(status_icon stopped) OpenClaw Gateway — FAILED to start (check $LOG_DIR/gateway.log)"
    fi
  fi

  # 2. Mission Control
  if lsof -ti :3000 > /dev/null 2>&1; then
    echo -e "  $(status_icon running) Mission Control — already running on :3000"
  else
    echo -e "  $(status_icon stopped) Mission Control — starting..."
    cd "$MC_DIR" && npm run start > "$LOG_DIR/mission-control.log" 2>&1 &
    local mc_pid=$!
    echo $mc_pid > "$PID_DIR/mission-control.pid"
    sleep 3
    if lsof -ti :3000 > /dev/null 2>&1; then
      echo -e "  $(status_icon running) Mission Control — started on :3000"
    else
      echo -e "  $(status_icon stopped) Mission Control — FAILED (check $LOG_DIR/mission-control.log)"
    fi
  fi

  # 3. SOUL Watchdog — init baselines + start cron check
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

  echo ""
  echo "  Dashboard:  http://localhost:3000"
  echo "  Gateway:    http://127.0.0.1:18789"
  echo ""
  echo "  Login: juan / enigma1686cyber"
  echo ""
}

# --- STOP ---
stop_system() {
  echo ""
  echo "  Stopping DOF Agent Legion..."
  echo ""

  # Stop Mission Control
  if [ -f "$PID_DIR/mission-control.pid" ]; then
    kill $(cat "$PID_DIR/mission-control.pid") 2>/dev/null
    rm "$PID_DIR/mission-control.pid"
  fi
  # Also kill any node on :3000
  lsof -ti :3000 | xargs kill 2>/dev/null
  echo -e "  $(status_icon stopped) Mission Control — stopped"

  # Stop gateway
  openclaw gateway stop 2>/dev/null || lsof -ti :18789 | xargs kill 2>/dev/null
  echo -e "  $(status_icon stopped) OpenClaw Gateway — stopped"

  # Stop Agent Legion daemon
  if [ -f "$DAEMON" ]; then
    bash "$DAEMON" stop
  fi
  echo -e "  $(status_icon stopped) Agent Legion — daemon stopped"

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

  # Gateway
  if lsof -ti :18789 > /dev/null 2>&1; then
    echo -e "  $(status_icon running) OpenClaw Gateway    :18789"
  else
    echo -e "  $(status_icon stopped) OpenClaw Gateway    offline"
  fi

  # Mission Control
  if lsof -ti :3000 > /dev/null 2>&1; then
    echo -e "  $(status_icon running) Mission Control     :3000"
  else
    echo -e "  $(status_icon stopped) Mission Control     offline"
  fi

  # Ollama
  if lsof -ti :11434 > /dev/null 2>&1; then
    echo -e "  $(status_icon running) Ollama              :11434"
  else
    echo -e "  $(status_icon stopped) Ollama              offline"
  fi

  # BlockRun
  if lsof -ti :8402 > /dev/null 2>&1; then
    echo -e "  $(status_icon running) BlockRun Proxy      :8402"
  else
    echo -e "  $(status_icon stopped) BlockRun Proxy      offline"
  fi

  # SOUL Watchdog
  if crontab -l 2>/dev/null | grep -q "soul-watchdog"; then
    echo -e "  $(status_icon running) SOUL Watchdog       cron active"
  else
    echo -e "  $(status_icon stopped) SOUL Watchdog       not scheduled"
  fi

  # Agent count
  local agent_count=$(ls -d "$HOME/.openclaw"/workspace-*/SOUL.md 2>/dev/null | wc -l | tr -d ' ')
  echo ""
  echo "  Agents: $agent_count"
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
