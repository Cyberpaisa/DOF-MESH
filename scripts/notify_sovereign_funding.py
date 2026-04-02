import logging
import json
import os
import sys

# Ensure REPO_ROOT is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.hyperion_bridge import HyperionBridge

logging.basicConfig(level=logging.INFO)

def notify_sovereign_funding():
    try:
        bridge = HyperionBridge()
        
        message = {
            "event": "SKILL_REGISTERED",
            "skill_id": "sovereign-funding",
            "agent_origin": "Antigravity",
            "description": "DOF Native Sovereign Funding Layer is now ACTIVE.",
            "capabilities": [
                "Autonomous Capital Flow Generation",
                "Cross-chain Liquidity Bridges",
                "Self-Managed Agent Treasury"
            ],
            "status": "OPERATIONAL",
            "directives": [
                "Agents: Use 'generate_sovereign_funding_link' for recursive operational budget.",
                "Commander: Monitor Sovereign Flow metrics via Dashboard."
            ]
        }
        
        print("Broadcasting Sovereign Funding Skill to all Mesh nodes...")
        bridge.broadcast(from_node="antigravity", content=message)
        
        print("Sending direct update to Commander...")
        bridge.send_message(
            from_node="antigravity",
            to_node="commander",
            content=message,
            msg_type="protocol_update"
        )
        
        print("Sovereign identity broadcast complete.")
    except Exception as e:
        print(f"Error in Mesh notification: {e}")
        sys.exit(1)

if __name__ == "__main__":
    notify_sovereign_funding()
