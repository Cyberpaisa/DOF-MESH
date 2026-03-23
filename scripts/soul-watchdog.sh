#!/bin/bash
# ============================================================
# SOUL Watchdog — Integrity Monitor for DOF Agent Legion
# Detects unauthorized modifications to agent SOUL.md files
# Run via cron every minute or as a LaunchAgent
# ============================================================

WORKSPACE_DIR="$HOME/.openclaw"
BASELINE_DIR="$HOME/.openclaw/.soul-baselines"
BACKUP_DIR="$HOME/.openclaw/.soul-backups"
LOG_FILE="$HOME/.openclaw/soul-watchdog.log"
ALERT_METHOD="log"  # log | telegram | both

mkdir -p "$BASELINE_DIR" "$BACKUP_DIR"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

alert() {
  local msg="$1"
  log "ALERT: $msg"

  if [[ "$ALERT_METHOD" == "telegram" || "$ALERT_METHOD" == "both" ]]; then
    # Send Telegram alert to Cyber Paisa
    local BOT_TOKEN="8706259296:AAHIJgQu6x59tZZ-KgpvJHW-OPZVJFWZYew"
    local CHAT_ID="1353800773"
    curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
      -d chat_id="$CHAT_ID" \
      -d text="🚨 SOUL WATCHDOG: $msg" \
      -d parse_mode="Markdown" > /dev/null 2>&1
  fi
}

# --- INIT MODE: Create baselines ---
init_baselines() {
  log "Initializing baselines..."
  for soul in "$WORKSPACE_DIR"/workspace-*/SOUL.md; do
    [ -f "$soul" ] || continue
    agent=$(basename "$(dirname "$soul")" | sed 's/workspace-//')
    shasum -a 256 "$soul" | awk '{print $1}' > "$BASELINE_DIR/${agent}.sha256"
    cp "$soul" "$BACKUP_DIR/${agent}.SOUL.md.bak"
    log "Baseline set for $agent"
  done
  log "Baselines initialized for $(ls "$BASELINE_DIR"/*.sha256 2>/dev/null | wc -l | tr -d ' ') agents"
}

# --- CHECK MODE: Verify integrity ---
check_integrity() {
  local violations=0
  for soul in "$WORKSPACE_DIR"/workspace-*/SOUL.md; do
    [ -f "$soul" ] || continue
    agent=$(basename "$(dirname "$soul")" | sed 's/workspace-//')
    baseline_file="$BASELINE_DIR/${agent}.sha256"

    # No baseline = new agent, create one
    if [ ! -f "$baseline_file" ]; then
      shasum -a 256 "$soul" | awk '{print $1}' > "$baseline_file"
      cp "$soul" "$BACKUP_DIR/${agent}.SOUL.md.bak"
      log "New agent detected: $agent — baseline created"
      continue
    fi

    current_hash=$(shasum -a 256 "$soul" | awk '{print $1}')
    baseline_hash=$(cat "$baseline_file")

    if [ "$current_hash" != "$baseline_hash" ]; then
      violations=$((violations + 1))
      alert "$agent SOUL.md MODIFIED! Expected: ${baseline_hash:0:12}... Got: ${current_hash:0:12}..."

      # Save the tampered version for forensics
      cp "$soul" "$BACKUP_DIR/${agent}.SOUL.md.tampered.$(date +%s)"

      # Restore from backup
      if [ -f "$BACKUP_DIR/${agent}.SOUL.md.bak" ]; then
        cp "$BACKUP_DIR/${agent}.SOUL.md.bak" "$soul"
        log "RESTORED $agent SOUL.md from backup"
        alert "$agent SOUL.md RESTORED from backup"
      fi
    fi
  done

  if [ $violations -eq 0 ]; then
    log "CHECK OK — all SOULs intact"
  else
    alert "$violations SOUL(s) were tampered with and restored"
  fi
}

# --- UPDATE MODE: Accept current state as new baseline ---
update_baseline() {
  local agent="$1"
  if [ -z "$agent" ]; then
    echo "Usage: $0 update <agent-name>"
    echo "       $0 update all"
    exit 1
  fi

  if [ "$agent" = "all" ]; then
    init_baselines
    return
  fi

  local soul="$WORKSPACE_DIR/workspace-${agent}/SOUL.md"
  if [ ! -f "$soul" ]; then
    echo "SOUL.md not found for agent: $agent"
    exit 1
  fi

  shasum -a 256 "$soul" | awk '{print $1}' > "$BASELINE_DIR/${agent}.sha256"
  cp "$soul" "$BACKUP_DIR/${agent}.SOUL.md.bak"
  log "Baseline UPDATED for $agent"
  echo "Baseline updated for $agent"
}

# --- STATUS ---
show_status() {
  echo "=== SOUL Watchdog Status ==="
  echo ""
  for soul in "$WORKSPACE_DIR"/workspace-*/SOUL.md; do
    [ -f "$soul" ] || continue
    agent=$(basename "$(dirname "$soul")" | sed 's/workspace-//')
    baseline_file="$BASELINE_DIR/${agent}.sha256"

    if [ ! -f "$baseline_file" ]; then
      echo "  $agent: NO BASELINE"
      continue
    fi

    current_hash=$(shasum -a 256 "$soul" | awk '{print $1}')
    baseline_hash=$(cat "$baseline_file")

    if [ "$current_hash" = "$baseline_hash" ]; then
      echo "  $agent: OK"
    else
      echo "  $agent: MODIFIED!"
    fi
  done
  echo ""
  echo "Last 5 log entries:"
  tail -5 "$LOG_FILE" 2>/dev/null || echo "  (no logs yet)"
}

# --- MAIN ---
case "${1:-check}" in
  init)     init_baselines ;;
  check)    check_integrity ;;
  update)   update_baseline "$2" ;;
  status)   show_status ;;
  *)
    echo "Usage: $0 {init|check|update <agent>|status}"
    echo ""
    echo "  init    — Create baselines for all agent SOULs"
    echo "  check   — Verify integrity (run via cron)"
    echo "  update  — Accept current SOUL as new baseline"
    echo "  status  — Show current integrity status"
    exit 1
    ;;
esac
