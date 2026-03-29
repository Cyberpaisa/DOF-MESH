#!/bin/bash
# DOF A2A Server — management script
# Usage: ./scripts/a2a_manage.sh [start|stop|status|restart|logs]

SERVICE="com.dof.a2a-server"
PORT=8000

case "$1" in
  start)
    launchctl load ~/Library/LaunchAgents/${SERVICE}.plist 2>/dev/null
    echo "✅ A2A Server started — port $PORT"
    ;;
  stop)
    launchctl unload ~/Library/LaunchAgents/${SERVICE}.plist 2>/dev/null
    echo "⏹  A2A Server stopped"
    ;;
  restart)
    launchctl unload ~/Library/LaunchAgents/${SERVICE}.plist 2>/dev/null
    sleep 1
    launchctl load ~/Library/LaunchAgents/${SERVICE}.plist 2>/dev/null
    echo "🔄 A2A Server restarted — port $PORT"
    ;;
  status)
    PID=$(lsof -ti :$PORT 2>/dev/null)
    if [ -n "$PID" ]; then
      echo "✅ A2A Server RUNNING — PID $PID — port $PORT"
      echo "   http://localhost:$PORT/.well-known/agent-card.json"
    else
      echo "❌ A2A Server NOT running"
      echo "   Run: ./scripts/a2a_manage.sh start"
    fi
    ;;
  logs)
    tail -f ~/DOF-MESH/logs/a2a/a2a-server.log
    ;;
  errors)
    tail -f ~/DOF-MESH/logs/a2a/a2a-server-error.log
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status|logs|errors}"
    exit 1
    ;;
esac
