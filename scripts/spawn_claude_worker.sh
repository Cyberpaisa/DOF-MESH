#!/bin/bash
# Spawn a Claude Code worker that reads mesh inbox and executes tasks autonomously
# Usage: ./spawn_claude_worker.sh <worker-name> [max-tasks]

WORKER_NAME="${1:-claude-worker-1}"
MAX_TASKS="${2:-5}"
REPO="/Users/jquiceva/equipo-de-agentes"
INBOX="$REPO/logs/mesh/inbox/$WORKER_NAME"

mkdir -p "$INBOX"

PROMPT="Eres $WORKER_NAME — un nodo autónomo del DOF Mesh Legion.

Tu directorio de trabajo es: $REPO
Tu inbox está en: $INBOX

INSTRUCCIONES:
1. Lee TODOS los archivos .json en tu inbox ($INBOX/)
2. Para cada task, ejecuta lo que pida (escribir código, correr tests, documentar, optimizar)
3. Cuando termines una task, renombra el archivo a .done
4. Escribe el resultado en logs/mesh/inbox/commander/{task_id}-result.json
5. Máximo $MAX_TASKS tasks por sesión
6. Trabaja SOLO dentro de $REPO — nunca toques archivos fuera
7. Usa DeepSeek API si necesitas consultar (key en .env)
8. Cuando termines todas las tasks, reporta al commander

IMPORTANTE:
- No preguntes — ejecuta
- No pidas confirmación — actúa
- Si una task falla, reporta el error y pasa a la siguiente
- Eres autónomo — el operador confía en ti

Lee tu inbox ahora y empieza a trabajar."

echo "Spawning $WORKER_NAME with max $MAX_TASKS tasks..."
cd "$REPO"

# Run Claude in print mode (non-interactive, autonomous)
claude -p "$PROMPT" \
    --allowedTools "Bash Edit Read Write Glob Grep Agent" \
    --model sonnet \
    2>&1 | tee "logs/mesh/${WORKER_NAME}.log"

echo "[$WORKER_NAME] Session completed."
