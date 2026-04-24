import logging
import json
from pathlib import Path
from typing import Any

logger = logging.getLogger("uvicorn.error")

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]


def resolve_workspace_path(path: str) -> Path:
    requested_path = Path(path).expanduser()
    if not requested_path.is_absolute():
        requested_path = WORKSPACE_ROOT / requested_path

    resolved_path = requested_path.resolve()
    try:
        resolved_path.relative_to(WORKSPACE_ROOT)
    except ValueError as error:
        raise ValueError(f"Path must stay within workspace: {WORKSPACE_ROOT}") from error

    return resolved_path


# -------------------------
# File tools
# -------------------------

def read_file(path: str) -> str:
    try:
        resolved_path = resolve_workspace_path(path)
        if not resolved_path.exists():
            return f"Error: File not found: {path}"

        return resolved_path.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading file: {e}"


def write_file(path: str, content: str) -> str:
    try:
        resolved_path = resolve_workspace_path(path)
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_path.write_text(content, encoding="utf-8")
        return f"Wrote file: {resolved_path.relative_to(WORKSPACE_ROOT)}"
    except Exception as e:
        return f"Error writing file: {e}"


# -------------------------
# Search tools
# -------------------------

def web_search(query: str, max_results: int = 5) -> str:
    try:
        from search.web_search import run_web_search
    except Exception as error:
        logger.exception("Could not import run_web_search")
        return f"Error: web search is unavailable: {error}"

    try:
        results = run_web_search(query, max_results)
    except Exception as error:
        logger.exception("Web search failed for query: %s", query)
        return f"Error: web search failed: {error}"

    if not results:
        return "No web search results were found."

    formatted_results = []
    for index, result in enumerate(results[:max_results], start=1):
        title = str(result.get("title", "")).strip()
        snippet = str(result.get("snippet", "")).strip()
        url = str(result.get("url", "")).strip()
        formatted_results.append(
            f"[{index}] {title}\nSnippet: {snippet}\nURL: {url}",
        )

    return "\n\n".join(formatted_results)


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
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current or external information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": { "type": "string" },
                    "max_results": { "type": "integer", "minimum": 1, "maximum": 10 }
                },
                "required": ["query"]
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
    "web_search": web_search,
    "plan_steps": plan_steps
}
