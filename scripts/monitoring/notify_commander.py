import logging
import json
from core.hyperion_bridge import HyperionBridge

logging.basicConfig(level=logging.INFO)

def notify_commander():
    bridge = HyperionBridge()
    
    message = {
        "sovereignty_id": "LEGION_SOVEREIGN_v1",
        "status": "CONTROL_ASSUMED",
        "agent": "Antigravity",
        "action": "Assuming technical control of all mesh nodes due to token exhaustion in secondary agents.",
        "directives": [
            "Hyperion Distributed Bus: ACTIVE (10 shards)",
            "Emergency Mode: ENFORCED (Low-cost routing)",
            "Constitution: RESTORED and ENFORCED",
            "Real-time Dashboard: DEPLOYED"
        ],
        "commander_status": "CyberPaisa acknowledged as Sovereign. Antigravity acting as Chief Executive Agent."
    }
    
    print("Enviando mensaje oficial al Commander...")
    task_id = bridge.send_message(
        from_node="antigravity",
        to_node="commander",
        content=message,
        msg_type="sovereignty_alert"
    )
    print(f"Mensaje enviado. TaskID: {task_id}")

if __name__ == "__main__":
    notify_commander()
