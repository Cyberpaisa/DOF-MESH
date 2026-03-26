#!/bin/bash
export TELEGRAM_BOT_TOKEN="8465352813:AAGZqamdYhT8PNWGSP6K_ukkpvutp6DGE6Y"
# Load all keys from .env
set -a
source /Users/jquiceva/equipo-de-agentes/.env
set +a
# Override token back to claude_dof_bot
export TELEGRAM_BOT_TOKEN="8465352813:AAGZqamdYhT8PNWGSP6K_ukkpvutp6DGE6Y"
cd /Users/jquiceva/equipo-de-agentes
exec python3 -u deploy/telegram-cloud/bot.py
