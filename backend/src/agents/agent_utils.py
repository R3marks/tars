# src/agents/agent_utils.py
import os
import logging
import json
from typing import Any, Dict, List

logger = logging.getLogger("uvicorn.error")


# -------------------------
# File tools
# -------------------------

def read_file(path: str) -> str:
    if not os.path.exists(path):
        return f"Error: File not found: {path}"

    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"


def write_file(path: str, content: str) -> str:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Wrote file: {path}"
    except Exception as e:
        return f"Error writing file: {e}"


# -------------------------
# Planner tool
# -------------------------

def plan_steps(steps: Any) -> str:
    """
    The planner is responsible for producing valid steps.
    This tool simply echoes them back.

    Expected shape:
    [
        { "step": "...", "prompt": "..." },
        ...
    ]
    """
    if isinstance(steps, str):
        return steps

    try:
        return json.dumps(steps, ensure_ascii=False)
    except Exception as e:
        logger.error(f"plan_steps failed: {e}")
        return "[]"


# -------------------------
# Tool registry
# -------------------------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file from disk.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": { "type": "string" }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write a file to disk.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": { "type": "string" },
                    "content": { "type": "string" }
                },
                "required": ["path", "content"]
            }
        }
    },
]
PLANNER_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "plan_steps",
            "description": "Return the minimal ordered steps required to satisfy a success outcome.",
            "parameters": {
                "type": "object",
                "properties": {
                    "steps": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "step": { 
                                    "type": "string",
                                    "description": "A concise description of what the step entails for logging purposes only."
                                    },
                                "prompt": { 
                                    "type": "string",
                                    "description": "The exact information that the executor model needs to satisfy the outcome."
                                    }
                            },
                            "required": ["step", "prompt"]
                        }
                    }
                }
            }
        }
    }
]

TOOL_MAP = {
    "read_file": read_file,
    "write_file": write_file,
    "plan_steps": plan_steps
}
