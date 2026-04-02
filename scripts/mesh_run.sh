#!/bin/bash
# DOF-MESH SOVEREIGN BRIDGE
# This script transparently intercepts python commands and routes them
# to the isolated Sovereign Citadel (Docker) while keeping the UX exactly the same.

set -e

# Ensure Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "🚨 ERROR: Sovereign Citadel is offline. Please start OrbStack or Docker Desktop."
    exit 3
fi

# Ensure the container is up
CONTAINER_NAME="dof-mesh-citadel"
if [ ! "$(docker ps -q -f name=$CONTAINER_NAME)" ]; then
    echo "🛡️ Citadel is sleeping. Waking up the Sovereign Container..."
    docker-compose up -d
fi

# Route the command
if [ "$1" == "" ]; then
    echo "Usage: ./scripts/mesh_run.sh scripts/execute_global_evaluator.py [args...]"
    exit 1
fi

echo "🛡️ Routing execution through Air-Gap Citadel..."

# We use docker exec to run the command interactively (with TTY if available)
if [ -t 1 ] ; then
  docker exec -it $CONTAINER_NAME python3 "$@"
else
  # NDJSON pipe mode for Agent-First CLI
  docker exec $CONTAINER_NAME python3 "$@"
fi
