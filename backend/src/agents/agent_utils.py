# src/agents/agent_utils.py
import os
import logging
import json

from typing import Any

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
    
def plan_steps(steps: Any) -> str:
    """
    Tool handler for plan_steps. The LLM will typically call this tool
    by passing 'steps' as a JSON array (or a JSON string).
    This function normalizes the input and returns a JSON string of the steps.

    NOTE: The model is expected to generate the steps itself when it emits
    the tool call. This tool simply validates/echoes them back for the agent.
    """
    try:
        # If the model passed a JSON string, parse it
        if isinstance(steps, str):
            try:
                parsed = json.loads(steps)
            except Exception:
                # maybe steps is already a pretty-printed JSON; try unicode-unescape then parse
                parsed = json.loads(steps.encode("utf-8").decode("unicode_escape"))
        else:
            parsed = steps

        # Ensure it is list/dict structure we expect
        # If model included top-level {"steps": [...]}, normalize to that
        if isinstance(parsed, dict) and "steps" in parsed:
            steps_list = parsed["steps"]
        else:
            steps_list = parsed

        # Validate shape lightly (ensure list of dicts)
        if not isinstance(steps_list, list):
            return json.dumps({"error": "Expected 'steps' as a list", "raw": steps_list})

        # Optionally, we could further validate each step contains step/prompt
        cleaned = []
        for s in steps_list:
            if not isinstance(s, dict):
                # coerce simple strings to a step object
                cleaned.append({
                    "step": "unknown", 
                    "prompt": str(s),
                    "tool": ""
                    })
            else:
                step_name = s.get("step", s.get("action", "unknown"))
                prompt = s.get("prompt", s.get("instruction", ""))
                tool = s.get("tool", s.get("tool_call", ""))
                cleaned.append({
                    "step": step_name, 
                    "prompt": prompt,
                    "tool": tool
                    })
        # Return canonical JSON string
        return json.dumps({"steps": cleaned}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"plan_steps failed: {e}"})

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
                    "path": {
                        "type": "string", 
                        "description": "Full file path (e.g., 'T:/Docs/experience.txt')."
                        }
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
                    "path": {
                        "type": "string", 
                        "description": "Full file path (e.g., 'T:/Docs/generated_cv.html')."
                        },
                    "content": {
                        "type": "string", 
                        "description": "The content to write (e.g., HTML string)."
                        }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "plan_steps",
            "description": "Create a structured plan of ordered steps to achieve the user’s goal. Each step should have a human-readable purpose and any specific prompt text or tool to be called next.",
            "parameters": {
                "type": "object",
                "properties": {
                    "steps": {
                        "type": "array",
                        "description": "A list of ordered steps that the agent should perform.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "step": {
                                    "type": "string", 
                                    "description": "Name of the step (e.g. Read Document, Compare Findings)."
                                    },
                                "prompt": {
                                    "type": "string", 
                                    "description": "Instruction or prompt for what to do in this step."
                                    },
                                "tool": {
                                    "type": "string", 
                                    "description": "Optional tool name to be used for this step (e.g. read_file, write_file)."
                                    }
                            },
                            "required": ["step", "prompt"]
                        }
                    }
                },
                "required": ["steps"]
            }
        }
    }

]

TOOL_MAP = {
    "read_file": read_file,
    "write_file": write_file,
    "plan_steps": plan_steps
}

# System prompt addition for CV task (append to user's system prompt if needed)
CV_SYSTEM_PROMPT = """
You are a CV/cover letter generator. For a job description, read the user's experience (from file), current CV, and current cover letter. Cherry-pick relevant experience. Generate a personalized CV in HTML format (use <html><body> structure for creativity). Write the output to a file.
Use tools to read/write files as needed. If files are missing, ask for clarification.
"""