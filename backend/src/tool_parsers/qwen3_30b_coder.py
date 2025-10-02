# src/tool_parsers/qwen3_30b_coder.py
import re
import json
import logging

logger = logging.getLogger("uvicorn.error")

def parse_qwen_tool_call(content: str) -> list[dict]:
    """
    Parse Qwen3-30B's XML-like tool call string into a list of tool call dicts.
    Preserves internal newlines and converts escaped \\n sequences to real newlines.
    """
    content = content.strip()
    tool_calls = []

    # Match each <tool_call> block
    tool_call_matches = re.finditer(r"<tool_call>(.*?)</tool_call>", content, re.DOTALL)
    for tc_match in tool_call_matches:
        tool_content = tc_match.group(1).strip()

        # Extract function name and params block
        func_match = re.search(r"<function=([^>]+)>(.*?)</function>", tool_content, re.DOTALL)
        if not func_match:
            logger.error(f"Failed to parse function in: {tool_content}")
            continue

        func_name = func_match.group(1).strip()
        params_content = func_match.group(2) or ""
        args = {}

        # Extract parameters but preserve internal newlines
        param_matches = re.finditer(r"<parameter=([^>]+)>(.*?)</parameter>", params_content, re.DOTALL)
        for param_match in param_matches:
            param_name = param_match.group(1).strip()
            raw_value = param_match.group(2)

            # Normalize line endings and unescape escaped newline sequences
            raw_value = raw_value.replace("\r\n", "\n").replace("\r", "\n")
            raw_value = raw_value.replace("\\n", "\n")  # Convert literal backslash-n to actual newlines

            # Trim leading/trailing newlines and whitespace, but do NOT collapse internal whitespace
            raw_value = raw_value.strip("\n")
            raw_value = raw_value.strip()

            logger.info(f"For {func_name}, extracted param: {param_name} : '{raw_value[:200]}'")
            args[param_name] = raw_value

        # put args into a JSON string because your existing code expects JSON in "arguments"
        tool_calls.append({
            "function": {
                "name": func_name,
                "arguments": json.dumps(args)
            }
        })

    if not tool_calls:
        logger.debug(f"No valid tool calls parsed from: {content}")
    else:
        logger.debug(f"Parsed tool calls: {tool_calls}")

    return tool_calls
