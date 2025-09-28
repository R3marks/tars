# src/agents/agent_utils.py
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
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote to '{path}'."
    except Exception as e:
        return f"Error writing to '{path}': {str(e)}"

# Native tool specs for llama_cpp_python (list of dicts)
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file. Use for loading experience, CV, cover letter, or job description. Provide full path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Full file path (e.g., 'T:/Docs/experience.txt')."}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file (e.g., generated CV in HTML). Provide full path and content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Full file path (e.g., 'T:/Docs/generated_cv.html')."},
                    "content": {"type": "string", "description": "The content to write (e.g., HTML string)."}
                },
                "required": ["path", "content"]
            }
        }
    }
]

TOOL_MAP = {
    "read_file": read_file,
    "write_file": write_file
}

# System prompt addition for CV task (append to user's system prompt if needed)
CV_SYSTEM_PROMPT = """
You are a CV/cover letter generator. For a job description, read the user's experience (from file), current CV, and current cover letter. Cherry-pick relevant experience. Generate a personalized CV in HTML format (use <html><body> structure for creativity). Write the output to a file.
Use tools to read/write files as needed. If files are missing, ask for clarification.
"""