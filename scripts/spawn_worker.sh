#!/bin/bash
# spawn_worker.sh — Spawn a DOF worker in a git worktree (isolated, no main checkout impact)
#
# Usage:
#   ./scripts/spawn_worker.sh <worker-name> [max-tasks]
#   ./scripts/spawn_worker.sh code-reviewer 3
#
# What it does vs spawn_claude_worker.sh:
#   - Uses git worktree add instead of git checkout -b
#   - Worker operates in an isolated /tmp directory — main is never touched
#   - Worktree is cleaned up on exit (even on Ctrl+C / error)
#   - Branch is automatically deleted after cleanup

set -euo pipefail

WORKER_NAME="${1:-dof-worker}"
MAX_TASKS="${2:-5}"
REPO="$(git -C "$(dirname "$0")/.." rev-parse --show-toplevel)"
BRANCH="worker/${WORKER_NAME}-$(date +%s)"
WORKTREE_DIR="/tmp/dof-worktree-${WORKER_NAME}-$$"

# ── Cleanup trap — always runs on exit ─────────────────────────────────────
cleanup() {
    echo "[$WORKER_NAME] Cleaning up worktree: $WORKTREE_DIR"
    git -C "$REPO" worktree remove --force "$WORKTREE_DIR" 2>/dev/null || true
    git -C "$REPO" branch -D "$BRANCH" 2>/dev/null || true
    echo "[$WORKER_NAME] Worktree removed. Branch $BRANCH deleted."
}
trap cleanup EXIT INT TERM

# ── Create isolated worktree ────────────────────────────────────────────────
echo "[$WORKER_NAME] Creating worktree at $WORKTREE_DIR on branch $BRANCH..."
git -C "$REPO" worktree add -b "$BRANCH" "$WORKTREE_DIR" HEAD

INBOX="$REPO/logs/mesh/inbox/$WORKER_NAME"
mkdir -p "$INBOX" "$REPO/logs/mesh/inbox/commander"

PROMPT="Eres $WORKER_NAME — un nodo autónomo del DOF Mesh Legion.

Tu directorio de trabajo es: $WORKTREE_DIR  (worktree aislado — NO es main)
Tu inbox está en: $INBOX
Tu branch de trabajo es: $BRANCH

LEE CLAUDE.md PRIMERO — contiene las reglas del proyecto.

INSTRUCCIONES:
1. Ya estás en tu worktree aislado ($WORKTREE_DIR) — NO hagas git checkout
2. Lee TODOS los archivos .json en tu inbox ($INBOX/)
3. Cada JSON tiene: task_id, task_type, description, validation, rules
4. Para cada task:
   a. Ejecuta lo que pida la description
   b. Corre la validation command para verificar
   c. Escribe resultado en $REPO/logs/mesh/inbox/commander/{task_id}-result.json:
      {\"task_id\": \"TASK-XXX\", \"status\": \"completed|failed\", \"result\": \"descripcion\", \"branch\": \"$BRANCH\"}
   d. Renombra el archivo de task a .done
5. Máximo $MAX_TASKS tasks por sesión
6. Trabaja SOLO dentro de $WORKTREE_DIR — nunca toques archivos fuera

REGLAS DE SEGURIDAD (OBLIGATORIAS):
- NUNCA borres archivos de core/, dof/, tests/
- NUNCA hagas git push — solo el Soberano pushea
- NUNCA modifiques funciones sin leer el archivo completo
- NUNCA borres tests — si fallan, arregla el código
- NUNCA ejecutes: rm -rf, git reset --hard, git checkout ., git clean
- Commits con: --author='$WORKER_NAME <worker@dof.mesh>'
- NO agregar Co-Authored-By a commits

Lee CLAUDE.md y tu inbox ahora. Empieza a trabajar."

echo "[$WORKER_NAME] Spawning on branch $BRANCH (worktree: $WORKTREE_DIR), max $MAX_TASKS tasks..."

# Run Claude in the isolated worktree directory
claude -p "$PROMPT" \
    --allowedTools "Bash Edit Read Write Glob Grep" \
    --model sonnet \
    -C "$WORKTREE_DIR" \
    2>&1 | tee "$REPO/logs/mesh/${WORKER_NAME}.log"

echo "[$WORKER_NAME] Session completed. Worktree will be cleaned up."
# cleanup() runs via trap
