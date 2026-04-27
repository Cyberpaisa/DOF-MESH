#!/bin/bash
# 🧪 DOF-MESH: Test End-to-End (Punto 6 Checklist Kimi)
# Uso: ./verify_soar_e2e.sh <target_container_name>

TARGET=$1
if [ -z "$TARGET" ]; then
    echo "Uso: $0 <target_container_name>"
    exit 1
fi

echo "--- [1] Generando Scan de Prueba ---"
echo "Nmap scan report for $TARGET (10.10.10.254)" > /tmp/e2e_scan.txt
echo "PORT     STATE SERVICE" >> /tmp/e2e_scan.txt
echo "80/tcp   open  http" >> /tmp/e2e_scan.txt
echo "443/tcp  open  https" >> /tmp/e2e_scan.txt
echo "8080/tcp open  http-proxy (Rogue Service Detected)" >> /tmp/e2e_scan.txt

echo "--- [2] Ejecutando Analista con SOAR-Trigger ---"
python3 security_analyst.py \
    --input /tmp/e2e_scan.txt \
    --target "$TARGET" \
    --output reports/e2e_report.md \
    --soar-trigger

echo "--- [3] SOAR: Procesando Inbox ---"
# Simulando ejecución del usuario soar
sudo -u soar python3 defensive_soar.py --process

echo "--- [4] SOAR: Verificando Ticket ---"
TICKET_ID=$(python3 defensive_soar.py --status | grep -oE "\[[a-z0-9]{8}\]" | tr -d '[]' | tail -n 1)

if [ -z "$TICKET_ID" ]; then
    echo "❌ Error: No se generó ticket para $TARGET."
    exit 1
fi

echo "✅ Ticket Detectado: $TICKET_ID"

echo "--- [5] SOAR: Aprobación Humana ---"
sudo -u soar python3 defensive_soar.py --approve "$TICKET_ID"

echo "--- [6] Verificando Audit Log ---"
tail -n 1 /var/lib/soar/audit.log

echo "--- E2E TEST COMPLETADO ---"
