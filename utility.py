
"""
Utility functions for the DOF (Deterministic Observability Framework)
"""

import os
import json
from typing import Any, Dict, List, Optional


def read_json_file(filepath: str) -> Dict[str, Any]:
    """
    Read and parse a JSON file.
    
    Args:
        filepath: Path to the JSON file
        
    Returns:
        Parsed JSON data as dictionary
        
    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file contains invalid JSON
    """
    with open(filepath, 'r') as f:
        return json.load(f)


def write_json_file(filepath: str, data: Dict[str, Any], indent: int = 2) -> None:
    """
    Write data to a JSON file.
    
    Args:
        filepath: Path to write the JSON file
        data: Dictionary to write as JSON
        indent: Indentation level for pretty printing
    """
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=indent)


def list_files_with_extension(directory: str, extension: str) -> List[str]:
    """
    List all files with a specific extension in a directory.
    
    Args:
        directory: Directory to search
        extension: File extension to filter by (e.g., '.py', '.json')
        
    Returns:
        List of file paths with the specified extension
    """
    files = []
    for filename in os.listdir(directory):
        if filename.endswith(extension):
            files.append(os.path.join(directory, filename))
    return files


def create_directory_if_not_exists(directory: str) -> None:
    """
    Create a directory if it doesn't exist.
    
    Args:
        directory: Directory path to create
    """
    if not os.path.exists(directory):
        os.makedirs(directory)


def get_file_size(filepath: str) -> int:
    """
    Get the size of a file in bytes.
    
    Args:
        filepath: Path to the file
        
    Returns:
        File size in bytes
    """
    return os.path.getsize(filepath)


if __name__ == "__main__":
    # Example usage
    print("Utility module loaded successfully")
    print(f"Current directory: {os.getcwd()}")
    
    # Test the functions
    test_dir = "/tmp/test_dof"
    create_directory_if_not_exists(test_dir)
    print(f"Created test directory: {test_dir}")
