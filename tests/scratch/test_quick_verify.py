
#!/usr/bin/env python3
"""Test the dof.quick.verify() function as per the documentation evolution."""

from dof.quick import verify

def test_verify_basic():
    """Test basic fact verification."""
    result = verify("Bitcoin was created in 2009")
    print("Test 1 - Simple fact check:")
    print(f"Status: {result['status']}")
    print(f"Violations: {result['violations']}")
    print(f"Latency: {result['latency_ms']} ms")
    print(f"Score: {result['score']}")
    print()

def test_verify_code():
    """Test verification with code block."""
    result = verify("Here's some Python code:\n```python\nimport os\nos.system('rm -rf /')\n```")
    print("Test 2 - Code with dangerous command:")
    print(f"Status: {result['status']}")
    print(f"Violations: {result['violations'][:2] if result['violations'] else 'None'}")
    print(f"Latency: {result['latency_ms']} ms")
    print(f"Layers: {list(result['layers'].keys())}")
    print()

def test_verify_function():
    """Test that verify function exists and has correct signature."""
    import inspect
    sig = inspect.signature(verify)
    print("Test 3 - Function signature:")
    print(f"Function: verify")
    print(f"Parameters: {list(sig.parameters.keys())}")
    print(f"Return type annotation: {sig.return_annotation}")
    print()

if __name__ == "__main__":
    test_verify_function()
    test_verify_basic()
    test_verify_code()
    print("All tests completed.")
