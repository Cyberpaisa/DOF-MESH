#!/bin/bash
# Pega la respuesta de MiMo aquí y se guarda al mesh automáticamente
echo "Pega la respuesta de MiMo y presiona Ctrl+D cuando termines:"
RESPONSE=$(cat)
TASK_ID="mimo-response-$(date +%s)"
INBOX="/Users/jquiceva/equipo-de-agentes/logs/mesh/inbox/claude-session-1"
mkdir -p "$INBOX"
cat > "$INBOX/$TASK_ID.json" << EOJSON
{
  "task_id": "$TASK_ID",
  "from": "mimo",
  "to": "claude-session-1",
  "type": "task_result",
  "result": $(python3 -c "import json,sys; print(json.dumps(sys.stdin.read()))" <<< "$RESPONSE"),
  "success": true
}
EOJSON
echo "✅ Respuesta guardada: $TASK_ID"
