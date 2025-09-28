import os
import logging

logger = logging.getLogger("uvicorn.error")

def read_file(path: str) -> str:
    """Read the contents of a file."""
    if not os.path.exists(path):
        return f"Error: File '{path}' does not exist."
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file '{path}': {str(e)}"

def write_file(path: str, content: str) -> str:
    """Write content to a file (creates if not exists)."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)  # Create dirs if needed
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote to '{path}'."
    except Exception as e:
        return f"Error writing to '{path}': {str(e)}"
