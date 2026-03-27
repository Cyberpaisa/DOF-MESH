#!/bin/bash
export TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:?Set TELEGRAM_BOT_TOKEN in .env}"
# Load all keys from .env
set -a
source /Users/jquiceva/equipo-de-agentes/.env
set +a
# Override token back to claude_dof_bot
export TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:?Set TELEGRAM_BOT_TOKEN in .env}"
cd /Users/jquiceva/equipo-de-agentes
exec python3 -u deploy/telegram-cloud/bot.py
