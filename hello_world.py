
#!/usr/bin/env python3
"""
Hello World script for the DOF repository.
This is a simple demonstration file.
"""

def greet(name: str = "World") -> str:
    """Return a greeting message."""
    return f"Hello, {name}!"

def main():
    """Main function to demonstrate the greeting."""
    print(greet())
    print(greet("DOF Agent"))
    
    # Demonstrate some Python features
    numbers = [1, 2, 3, 4, 5]
    squares = [n**2 for n in numbers]
    print(f"\nNumbers: {numbers}")
    print(f"Squares: {squares}")
    
    # Show Python version
    import sys
    print(f"\nPython version: {sys.version}")

if __name__ == "__main__":
    main()
