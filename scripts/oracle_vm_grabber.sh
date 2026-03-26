#!/bin/bash
# Oracle VM Grabber — retries every 60 seconds until a VM is provisioned
# ARM A1.Flex instances on Free Tier are scarce, this script keeps trying

export SUPPRESS_LABEL_WARNING=True

TENANCY="ocid1.tenancy.oc1..aaaaaaaafrteajm5uepgkdzveywpcx3egxlrz53pqpprr7ikzxkrothabjga"
IMAGE="ocid1.image.oc1.iad.aaaaaaaahk7zm5s5gv4imyzgui5c77uzfpn72blj3od2icmohxzv3zpuiikq"
SUBNET="ocid1.subnet.oc1.iad.aaaaaaaa6ardjxa62acovnhid7zen2v53gpehuxwitwnwhpk2qwvya2gy4jq"
ADS=("rbTc:US-ASHBURN-AD-1" "rbTc:US-ASHBURN-AD-2" "rbTc:US-ASHBURN-AD-3")
SSH_KEY="/Users/jquiceva/.ssh/id_ed25519.pub"

ATTEMPT=0
while true; do
    ATTEMPT=$((ATTEMPT + 1))
    for AD in "${ADS[@]}"; do
        echo "[$(date '+%H:%M:%S')] Attempt $ATTEMPT — Trying $AD..."

        RESULT=$(oci compute instance launch \
            --compartment-id "$TENANCY" \
            --availability-domain "$AD" \
            --display-name "dof-legion" \
            --image-id "$IMAGE" \
            --shape "VM.Standard.A1.Flex" \
            --shape-config '{"ocpus": 4, "memoryInGBs": 24}' \
            --subnet-id "$SUBNET" \
            --assign-public-ip true \
            --ssh-authorized-keys-file "$SSH_KEY" 2>&1)

        if echo "$RESULT" | grep -q '"lifecycle-state"'; then
            echo ""
            echo "═══════════════════════════════════════"
            echo "  ✅ VM CREATED SUCCESSFULLY!"
            echo "═══════════════════════════════════════"
            echo "$RESULT" | python3 -c "
import sys, json
d = json.load(sys.stdin)['data']
print(f'  Name: {d[\"display-name\"]}')
print(f'  State: {d[\"lifecycle-state\"]}')
print(f'  ID: {d[\"id\"]}')
print(f'  AD: {d[\"availability-domain\"]}')
print(f'  Shape: {d[\"shape\"]}')
" 2>/dev/null
            echo ""
            echo "Waiting for public IP..."
            sleep 30
            IP=$(oci compute instance list-vnics \
                --instance-id "$(echo "$RESULT" | python3 -c 'import sys,json; print(json.load(sys.stdin)["data"]["id"])' 2>/dev/null)" \
                --query 'data[0]."public-ip"' --raw-output 2>/dev/null)
            echo "  Public IP: $IP"
            echo "$IP" > /Users/jquiceva/equipo-de-agentes/logs/vps_ip.txt
            echo "═══════════════════════════════════════"
            exit 0
        fi

        if echo "$RESULT" | grep -q "Out of host capacity"; then
            echo "  ❌ No capacity"
        else
            echo "  ⚠️ $(echo "$RESULT" | grep -o '"message": "[^"]*"' | head -1)"
        fi
    done

    echo "  Waiting 60s before next round..."
    sleep 60
done
