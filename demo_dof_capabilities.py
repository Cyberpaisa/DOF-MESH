
#!/usr/bin/env python3
"""
Demonstration of DOF (Deterministic Observability Framework) capabilities.
This script shows basic mesh operations and framework features.
"""

import os
import sys
import json
import time
from pathlib import Path

def demonstrate_basic_structure():
    """Show the basic structure of the DOF framework."""
    print("=" * 60)
    print("DOF Framework Demonstration")
    print("=" * 60)
    
    # Show core modules count
    core_path = Path("core")
    if core_path.exists():
        core_files = list(core_path.glob("*.py"))
        print(f"✓ Core modules: {len(core_files)} Python files")
    
    # Show test count
    tests_path = Path("tests")
    if tests_path.exists():
        test_files = list(tests_path.glob("test_*.py"))
        print(f"✓ Test files: {len(test_files)}")
    
    # Show agents directory
    agents_path = Path("agents")
    if agents_path.exists():
        agent_dirs = [d for d in agents_path.iterdir() if d.is_dir()]
        print(f"✓ Agent directories: {len(agent_dirs)}")
    
    print()

def demonstrate_mesh_concept():
    """Explain the mesh architecture concept."""
    print("Mesh Architecture Concept:")
    print("-" * 40)
    print("""
    The DOF mesh is a decentralized network of AI nodes that:
    1. Communicate via filesystem inboxes (JSON files)
    2. Route tasks intelligently across providers
    3. Enforce deterministic governance
    4. Scale autonomously based on load
    
    Key components:
    • NodeMesh: Filesystem-based message bus
    • MeshOrchestrator: Central nervous system
    • MeshRouterV2: O(√n) intelligent routing
    • MeshGuardian: Security enforcement
    """)
    print()

def demonstrate_providers():
    """Show supported AI providers."""
    print("Supported AI Providers:")
    print("-" * 40)
    providers = [
        ("Cerebras Llama", "868 tok/s", "High performance"),
        ("DeepSeek Coder", "$0.27/M tok", "Cost-effective coding"),
        ("Gemini Flash", "Free/web", "General purpose"),
        ("Local Qwen", "Free/local", "Privacy-focused"),
        ("SambaNova", "Enterprise", "Large models"),
        ("NVIDIA", "GPU-optimized", "Inference speed"),
        ("GLM-5", "Chinese models", "Multilingual"),
        ("Groq", "LPU-based", "Ultra-fast inference"),
    ]
    
    for name, spec, desc in providers:
        print(f"• {name:20} {spec:20} - {desc}")
    print()

def demonstrate_security_layers():
    """Show the 7-layer security architecture."""
    print("7-Layer Security Architecture:")
    print("-" * 40)
    layers = [
        "1. MeshGuardian: Perimeter defense & anomaly detection",
        "2. Icarus: Behavioral analysis & intent classification",
        "3. Cerberus: Multi-head guardrail enforcement",
        "4. SecurityHierarchy: Role-based access control",
        "5. Governance: Constitutional AI principles",
        "6. AST Verifier: Code safety analysis",
        "7. Z3 Prover: Formal verification (8/8 proofs)",
    ]
    
    for layer in layers:
        print(layer)
    print()

def create_sample_task():
    """Create a sample task file to demonstrate mesh operation."""
    logs_dir = Path("logs")
    mesh_dir = logs_dir / "mesh"
    inbox_dir = mesh_dir / "inbox"
    
    # Create directories if they don't exist
    inbox_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a sample task
    sample_task = {
        "task_id": "demo_task_001",
        "created_at": time.time(),
        "type": "analysis",
        "payload": {
            "query": "Analyze the DOF framework architecture",
            "requirements": ["technical", "concise", "actionable"],
            "priority": "medium"
        },
        "metadata": {
            "source": "demo_script",
            "framework_version": "0.5.0"
        }
    }
    
    task_file = inbox_dir / "demo_task.json"
    with open(task_file, "w") as f:
        json.dump(sample_task, f, indent=2)
    
    print(f"✓ Created sample task at: {task_file}")
    print(f"  Task ID: {sample_task['task_id']}")
    print(f"  Type: {sample_task['type']}")
    print()

def demonstrate_autonomous_features():
    """Show autonomous capabilities."""
    print("Autonomous Features:")
    print("-" * 40)
    features = [
        "• Self-scaling: Hysteresis-based scale up/down",
        "• Self-healing: Automatic node recovery",
        "• Self-optimizing: Cost-aware provider selection",
        "• Self-governing: Constitutional AI enforcement",
        "• Self-documenting: Automatic audit logging",
        "• Self-testing: Continuous validation",
        "• Self-securing: Proactive threat detection",
    ]
    
    for feature in features:
        print(feature)
    print()

def main():
    """Main demonstration function."""
    print("\n" + "=" * 60)
    print("DOF (Deterministic Observability Framework) v0.5.0")
    print("=" * 60 + "\n")
    
    demonstrate_basic_structure()
    demonstrate_mesh_concept()
    demonstrate_providers()
    demonstrate_security_layers()
    demonstrate_autonomous_features()
    create_sample_task()
    
    print("=" * 60)
    print("Demonstration Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Run the mesh: python3 core/api_node_runner.py --nodes local-qwen")
    print("2. Check health: python3 scripts/mesh_health_dashboard.py")
    print("3. View docs: open docs/index.html")
    print("4. Run tests: python3 -m pytest tests/ -v")

if __name__ == "__main__":
    main()
