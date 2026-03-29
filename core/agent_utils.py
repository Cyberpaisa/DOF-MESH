
#!/usr/bin/env python3
"""
Agent Utilities - Helper functions for agent operations in the DOF framework.
Created by: Autonomous AI Agent
Date: 2024
"""

import datetime
import json
from typing import Dict, Any, Optional


def get_current_timestamp() -> str:
    """
    Get current timestamp in ISO format.
    
    Returns:
        ISO formatted timestamp string
    """
    return datetime.datetime.now().isoformat()


def format_agent_message(message: str, agent_name: str = "Agent") -> Dict[str, Any]:
    """
    Format a message with agent metadata.
    
    Args:
        message: The message content
        agent_name: Name of the agent sending the message
        
    Returns:
        Dictionary with formatted message and metadata
    """
    return {
        "timestamp": get_current_timestamp(),
        "agent": agent_name,
        "message": message,
        "framework": "DOF (Deterministic Observability Framework)"
    }


def log_agent_activity(activity: str, details: Optional[Dict[str, Any]] = None) -> None:
    """
    Log agent activity to console.
    
    Args:
        activity: Description of the activity
        details: Optional additional details as dictionary
    """
    log_entry = {
        "timestamp": get_current_timestamp(),
        "activity": activity,
        "details": details or {}
    }
    
    print(f"[AGENT LOG] {json.dumps(log_entry, indent=2)}")


def validate_agent_config(config: Dict[str, Any]) -> bool:
    """
    Validate basic agent configuration.
    
    Args:
        config: Agent configuration dictionary
        
    Returns:
        True if configuration is valid, False otherwise
    """
    required_fields = ["name", "role", "capabilities"]
    
    for field in required_fields:
        if field not in config:
            print(f"Missing required field: {field}")
            return False
    
    if not isinstance(config["capabilities"], list):
        print("Capabilities must be a list")
        return False
    
    return True


def main():
    """Demonstrate the utility functions."""
    print("Agent Utilities Module")
    print("=" * 50)
    
    # Test timestamp function
    print(f"Current timestamp: {get_current_timestamp()}")
    
    # Test message formatting
    message = format_agent_message("Hello from the agent utilities!", "UtilityAgent")
    print(f"\nFormatted message:\n{json.dumps(message, indent=2)}")
    
    # Test logging
    log_agent_activity("File creation", {"file": "agent_utils.py", "status": "created"})
    
    # Test config validation
    valid_config = {
        "name": "TestAgent",
        "role": "Tester",
        "capabilities": ["testing", "validation"]
    }
    
    invalid_config = {
        "name": "BadAgent",
        "role": "Tester"
        # Missing capabilities
    }
    
    print(f"\nValid config test: {validate_agent_config(valid_config)}")
    print(f"Invalid config test: {validate_agent_config(invalid_config)}")


if __name__ == "__main__":
    main()
