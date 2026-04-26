#!/bin/bash
# verify_lab.example.sh — Sovereign Lab Healthcheck
set -uo pipefail

echo "=== DOF-MESH :: Lab Security Verification ==="

# 1. Check Infrastructure Daemon
if docker info >/dev/null 2>&1; then
    echo "  [OK] Container daemon active"
else
    echo "  [FAIL] Container daemon inactive"
    exit 1
fi

# 2. Check Network Isolation (Mandatory)
# Attempt to ping a public DNS (should fail in a secure lab)
if ping -c 1 -W 2 8.8.8.8 >/dev/null 2>&1; then
    echo "  [CRITICAL] Security breach: Network is NOT isolated."
    exit 3
else
    echo "  [OK] Network isolation verified (Air-gap active)"
fi

# 3. Check Kernel Hardening
KPTR=$(sysctl -n kernel.kptr_restrict)
if [ "$KPTR" -eq 2 ]; then
    echo "  [OK] Kernel symbol restriction active"
else
    echo "  [WARN] Kernel symbols exposed (Expected restrict=2)"
fi

echo "=== Verification Complete ==="
