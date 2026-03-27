#!/bin/bash
# Oracle VM Grabber v2 — aggressive mode
# Tries all 3 ADs every 30s, also tries smaller shapes as fallback
# Best window: 2-5 AM EST (when US East Coast sleeps)

export SUPPRESS_LABEL_WARNING=True

TENANCY="ocid1.tenancy.oc1..aaaaaaaafrteajm5uepgkdzveywpcx3egxlrz53pqpprr7ikzxkrothabjga"
IMAGE="ocid1.image.oc1.iad.aaaaaaaahk7zm5s5gv4imyzgui5c77uzfpn72blj3od2icmohxzv3zpuiikq"
SUBNET="ocid1.subnet.oc1.iad.aaaaaaaa6ardjxa62acovnhid7zen2v53gpehuxwitwnwhpk2qwvya2gy4jq"
ADS=("rbTc:US-ASHBURN-AD-1" "rbTc:US-ASHBURN-AD-2" "rbTc:US-ASHBURN-AD-3")
SSH_KEY="/Users/jquiceva/.ssh/id_ed25519.pub"
IP_FILE="/Users/jquiceva/DOF-MESH/logs/vps_ip.txt"
LOG_FILE="/Users/jquiceva/DOF-MESH/logs/grabber.log"

# Shapes to try: full first, then smaller as fallback
SHAPES=('{"ocpus": 4, "memoryInGBs": 24}' '{"ocpus": 2, "memoryInGBs": 12}' '{"ocpus": 1, "memoryInGBs": 6}')
SHAPE_NAMES=("4cpu-24gb" "2cpu-12gb" "1cpu-6gb")

mkdir -p "$(dirname "$LOG_FILE")" "$(dirname "$IP_FILE")"

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
    echo "$msg"
    echo "$msg" >> "$LOG_FILE"
}

ATTEMPT=0
START=$(date +%s)

log "=== Oracle VM Grabber v2 started ==="
log "Tenancy: ${TENANCY:0:30}..."
log "Region: us-ashburn-1 | ADs: 3 | Shapes: ${#SHAPES[@]}"

while true; do
    ATTEMPT=$((ATTEMPT + 1))
    ELAPSED=$(( ($(date +%s) - START) / 60 ))

    for i in "${!SHAPES[@]}"; do
        SHAPE="${SHAPES[$i]}"
        SNAME="${SHAPE_NAMES[$i]}"

        for AD in "${ADS[@]}"; do
            AD_SHORT="${AD##*-}"
            log "Attempt $ATTEMPT (${ELAPSED}m) — $SNAME @ AD-$AD_SHORT"

            RESULT=$(oci compute instance launch \
                --compartment-id "$TENANCY" \
                --availability-domain "$AD" \
                --display-name "dof-legion" \
                --image-id "$IMAGE" \
                --shape "VM.Standard.A1.Flex" \
                --shape-config "$SHAPE" \
                --subnet-id "$SUBNET" \
                --assign-public-ip true \
                --ssh-authorized-keys-file "$SSH_KEY" 2>&1)

            if echo "$RESULT" | grep -q '"lifecycle-state"'; then
                log ""
                log "==========================================="
                log "  VM CREATED SUCCESSFULLY! ($SNAME)"
                log "==========================================="
                echo "$RESULT" | python3 -c "
import sys, json
d = json.load(sys.stdin)['data']
print(f'  Name: {d[\"display-name\"]}')
print(f'  State: {d[\"lifecycle-state\"]}')
print(f'  ID: {d[\"id\"]}')
print(f'  AD: {d[\"availability-domain\"]}')
print(f'  Shape: {d[\"shape\"]}')
" 2>/dev/null | tee -a "$LOG_FILE"

                INSTANCE_ID=$(echo "$RESULT" | python3 -c 'import sys,json; print(json.load(sys.stdin)["data"]["id"])' 2>/dev/null)

                log "Waiting 60s for public IP..."
                sleep 60

                IP=$(oci compute instance list-vnics \
                    --instance-id "$INSTANCE_ID" \
                    --query 'data[0]."public-ip"' --raw-output 2>/dev/null)

                if [[ -z "$IP" || "$IP" == "null" ]]; then
                    log "IP not ready, waiting 30s more..."
                    sleep 30
                    IP=$(oci compute instance list-vnics \
                        --instance-id "$INSTANCE_ID" \
                        --query 'data[0]."public-ip"' --raw-output 2>/dev/null)
                fi

                log "  Public IP: $IP"
                log "  Instance ID: $INSTANCE_ID"
                echo "$IP" > "$IP_FILE"
                echo "$INSTANCE_ID" > "${IP_FILE%.txt}_instance_id.txt"

                # Also save to equipo-de-agentes for auto_deploy
                mkdir -p /Users/jquiceva/equipo-de-agentes/logs
                echo "$IP" > /Users/jquiceva/equipo-de-agentes/logs/vps_ip.txt

                log "==========================================="
                log "IP saved to: $IP_FILE"
                log "Run: bash scripts/auto_deploy_vps.sh"
                log "==========================================="
                exit 0
            fi

            if echo "$RESULT" | grep -q "Out of host capacity"; then
                log "  -- No capacity"
            elif echo "$RESULT" | grep -q "timed out"; then
                log "  -- Timeout (API overloaded)"
            else
                MSG=$(echo "$RESULT" | grep -o '"message": "[^"]*"' | head -1)
                log "  -- $MSG"
            fi
        done
    done

    log "  Next round in 30s... (total: ${ELAPSED}m, attempts: $ATTEMPT)"
    sleep 30
done
