#!/bin/bash
# Spawn a Claude Code worker for DOF-MESH
# Usage: ./scripts/spawn_claude_worker.sh <worker-name> [max-tasks]
# Example: ./scripts/spawn_claude_worker.sh claude-worker-1 3

WORKER_NAME="${1:-claude-worker-1}"
MAX_TASKS="${2:-5}"
REPO="/Users/jquiceva/DOF-MESH"
INBOX="$REPO/logs/mesh/inbox/$WORKER_NAME"
BRANCH="worker/${WORKER_NAME}-$(date +%s)"

mkdir -p "$INBOX" "$REPO/logs/mesh/inbox/commander"

PROMPT="Eres $WORKER_NAME — un nodo autónomo del DOF Mesh Legion.

Tu directorio de trabajo es: $REPO
Tu inbox está en: $INBOX
Tu branch de trabajo es: $BRANCH

LEE CLAUDE.md PRIMERO — contiene las reglas del proyecto.

INSTRUCCIONES:
1. PRIMERO: ejecuta 'git checkout -b $BRANCH' — NUNCA trabajes en main
2. Lee TODOS los archivos .json en tu inbox ($INBOX/)
3. Cada JSON tiene un campo 'content' con: task_id, task_type, description, validation, rules
4. Para cada task:
   a. Lee la description y ejecuta lo que pida
   b. Corre la validation command para verificar
   c. Escribe resultado en logs/mesh/inbox/commander/{task_id}-result.json con formato:
      {\"task_id\": \"TASK-XXX\", \"status\": \"completed|failed\", \"result\": \"descripcion\", \"branch\": \"$BRANCH\"}
   d. Renombra el archivo de task a .done (mv archivo.json archivo.done)
5. Máximo $MAX_TASKS tasks por sesión
6. Trabaja SOLO dentro de $REPO — nunca toques archivos fuera

REGLAS DE SEGURIDAD (OBLIGATORIAS):
- NUNCA borres archivos de core/, dof/, tests/
- NUNCA hagas git push — solo el Soberano pushea
- NUNCA modifiques funciones sin leer el archivo completo
- NUNCA borres tests — si fallan, arregla el código
- NUNCA ejecutes: rm -rf, git reset --hard, git checkout ., git clean
- Commits con: --author='$WORKER_NAME <worker@dof.mesh>'
- NO agregar Co-Authored-By a commits

Lee CLAUDE.md y tu inbox ahora. Empieza a trabajar."

echo "[$WORKER_NAME] Spawning on branch $BRANCH with max $MAX_TASKS tasks..."
cd "$REPO"

# Create worker branch BEFORE spawning
git checkout -b "$BRANCH" 2>/dev/null || git checkout "$BRANCH"

# Run Claude in print mode (non-interactive, autonomous)
claude -p "$PROMPT" \
    --allowedTools "Bash Edit Read Write Glob Grep" \
    --model sonnet \
    2>&1 | tee "logs/mesh/${WORKER_NAME}.log"

# Return to main after worker finishes
git checkout main 2>/dev/null

echo "[$WORKER_NAME] Session completed on branch $BRANCH."
echo "[$WORKER_NAME] Check results: cat logs/mesh/inbox/commander/TASK-*-result.json"
