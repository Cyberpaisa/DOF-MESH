
#!/usr/bin/env python3
"""
Test script to verify core modules are working.
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # Test importing core modules
    from core.providers import ProviderManager
    print("✓ Successfully imported ProviderManager")
    
    from core.checkpointing import CheckpointManager
    print("✓ Successfully imported CheckpointManager")
    
    from core.memory_manager import MemoryManager
    print("✓ Successfully imported MemoryManager")
    
    from core.metrics import MetricsLogger
    print("✓ Successfully imported MetricsLogger")
    
    from core.governance import ConstitutionEnforcer
    print("✓ Successfully imported ConstitutionEnforcer")
    
    print("\n✅ All core modules imported successfully!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    sys.exit(1)
