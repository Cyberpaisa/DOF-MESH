#!/bin/bash
# verify_lab.sh — Healthcheck completo del Laboratorio Defensivo Soberano
# Ejecutar DENTRO de la VM como usuario dofoperator
# Uso: bash verify_lab.sh

set -uo pipefail

# Detección automática de audiencia (AGENTS.md §6)
JSON_MODE=false
if [[ "${1:-}" == "--json" ]] || ! [ -t 1 ]; then
    JSON_MODE=true
fi

PASS=0; FAIL=0; WARN=0
declare -a FINDINGS=()

ok()   { if $JSON_MODE; then FINDINGS+=("{\"status\":\"ok\",\"check\":\"$1\"}"); else echo "  ✅  $1"; fi; ((PASS++)) || true; }
fail() { if $JSON_MODE; then FINDINGS+=("{\"status\":\"fail\",\"check\":\"$1\"}"); else echo "  ❌  $1"; fi; ((FAIL++)) || true; }
warn() { if $JSON_MODE; then FINDINGS+=("{\"status\":\"warn\",\"check\":\"$1\"}"); else echo "  ⚠️   $1"; fi; ((WARN++)) || true; }

echo ""
echo "=== DOF-MESH :: Verificación del Laboratorio Defensivo ==="
echo ""

# 1. Verificar que Docker está corriendo
echo "[1/5] Docker daemon..."
if docker info >/dev/null 2>&1; then
    ok "Docker daemon activo"
else
    fail "Docker daemon no responde. Ejecuta: sudo systemctl start docker"
fi

# 2. Verificar que los contenedores están healthy
echo ""
echo "[2/5] Contenedores del lab..."
for container in lab_juiceshop lab_webgoat lab_traffic; do
    status=$(docker inspect --format='{{.State.Status}}' "$container" 2>/dev/null || echo "not_found")
    if [[ "$status" == "running" ]]; then
        ok "Contenedor $container: running"
    elif [[ "$status" == "not_found" ]]; then
        fail "Contenedor $container no existe. Ejecuta: docker compose -f docker-compose.lab.yml up -d"
    else
        fail "Contenedor $container: $status (esperado: running)"
    fi
done

# 3. Verificar que los targets responden en la red interna
echo ""
echo "[3/5] Conectividad a los targets..."
if curl -s --max-time 3 http://10.10.10.10:3000 >/dev/null 2>&1; then
    ok "Juice Shop responde en 10.10.10.10:3000"
else
    fail "Juice Shop no responde en 10.10.10.10:3000"
fi

if curl -s --max-time 3 http://10.10.10.11:8080/WebGoat/ >/dev/null 2>&1; then
    ok "WebGoat responde en 10.10.10.11:8080"
else
    fail "WebGoat no responde en 10.10.10.11:8080"
fi

# 4. Verificar aislamiento de red (debe FALLAR el ping a internet)
echo ""
echo "[4/5] Aislamiento de red (ping a 8.8.8.8 debe fallar)..."
if ping -c 1 -W 2 8.8.8.8 >/dev/null 2>&1; then
    fail "PELIGRO: La VM tiene acceso a internet. Verifica la configuración de UTM."
else
    ok "Red aislada correctamente — sin salida a internet"
fi

# 5. Verificar que Ollama responde con el modelo cargado
echo ""
echo "[5/5] Ollama y modelo dof-coder..."
if curl -s --max-time 5 http://localhost:11434/api/tags 2>/dev/null | grep -q "dof-coder"; then
    ok "Ollama activo y modelo dof-coder disponible"
elif curl -s --max-time 5 http://localhost:11434/api/tags >/dev/null 2>&1; then
    warn "Ollama activo pero dof-coder no encontrado. Ejecuta: ollama create dof-coder -f /opt/dof-mesh/models/Modelfile.vm"
else
    fail "Ollama no responde. Ejecuta: ollama serve &"
fi

# Resumen
if $JSON_MODE; then
    # Salida NDJSON para consumo por agentes (AGENTS.md §6)
    for finding in "${FINDINGS[@]}"; do echo "$finding"; done
    echo "{\"summary\":{\"pass\":$PASS,\"warn\":$WARN,\"fail\":$FAIL,\"ready\":$([ $FAIL -eq 0 ] && echo true || echo false)}}"
    exit $FAIL
fi

echo ""
echo "=== RESUMEN ==="
echo "  ✅ OK:      $PASS"
echo "  ⚠️  WARN:   $WARN"
echo "  ❌ FAIL:   $FAIL"
echo ""
if [[ $FAIL -eq 0 ]]; then
    echo "  🟢 Laboratorio listo para operar."
else
    echo "  🔴 Hay $FAIL fallo(s) bloqueantes. Resuelve los ❌ antes de comenzar."
fi
echo ""
exit $FAIL
