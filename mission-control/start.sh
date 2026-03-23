#!/bin/bash
# Mission Control — Lanzar dashboard
cd "/Users/jquiceva/equipo de agentes/mission-control"

# Si ya está corriendo, solo abrir el navegador
if lsof -ti:3000 > /dev/null 2>&1; then
    open http://localhost:3000
    exit 0
fi

# Si no está corriendo, iniciar y abrir
NEXT_PUBLIC_GATEWAY_OPTIONAL=true pnpm dev > /tmp/mission_control.log 2>&1 &
sleep 4
open http://localhost:3000
