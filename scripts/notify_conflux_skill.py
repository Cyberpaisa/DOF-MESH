import logging
import json
import os
import sys

# Ensure REPO_ROOT is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.hyperion_bridge import HyperionBridge

logging.basicConfig(level=logging.INFO)

def notify_conflux_skill():
    try:
        bridge = HyperionBridge()
        
        message = {
            "event": "SUPER_SKILL_REGISTERED",
            "skill_id": "conflux-integration",
            "agent_origin": "Antigravity",
            "description": "DOF Native Conflux Gateway Knowledge Base is ACTIVE.",
            "capabilities": [
                "eSpace EVM Compatibility & Tooling (Hardhat, Foundry)",
                "Core Space Gas & Storage Sponsorship (Gasless Agents)",
                "Cross-Space Bridge & Native RPC Management"
            ],
            "status": "OPERATIONAL",
            "directives": [
                "Agents: All Conflux operations MUST use eSpace and integrate Gas Sponsorship.",
                "Commander: The 'Conflux Sovereign Gateway' planning phase is complete."
            ]
        }
        
        print("Broadcasting Conflux Super Skill to all Mesh nodes...")
        bridge.broadcast(from_node="antigravity", content=message)
        
        print("Sending direct update to Commander...")
        bridge.send_message(
            from_node="antigravity",
            to_node="commander",
            content=message,
            msg_type="protocol_update"
        )
        
        print("Conflux Super Skill broadcast complete.")
    except Exception as e:
        print(f"Error in Mesh notification: {e}")
        sys.exit(1)

if __name__ == "__main__":
    notify_conflux_skill()
