# src/tool_parsers/qwen3_4b_instruct.py
import re
import json
import logging

logger = logging.getLogger("uvicorn.error")

def parse_qwen4b_tool_call(content: str) -> list[dict]:
    """
    Parse Qwen3-4B-Instruct's <tool_call> JSON blocks into a list of tool call dicts.
    Handles:
      - raw JSON
      - JSON wrapped in quotes/escaped with backslashes
      - leading/trailing newlines
    """
    content = content.strip()
    tool_calls = []

    # Match <tool_call> blocks (allow optional newlines/spaces)
    tool_call_matches = re.finditer(r"<tool_call>\s*(.*?)\s*</tool_call>", content, re.DOTALL)
    for match in tool_call_matches:
        block = match.group(1).strip()

        # Normalize endings and strip raw \n
        block = block.replace("\r\n", "\n").replace("\r", "\n").strip()

        logger.debug(f"Raw block (first 120 chars): {block[:120]}")

        try:
            # First attempt: direct JSON
            parsed = json.loads(block)
        except json.JSONDecodeError:
            try:
                # If it’s escaped JSON like {\"name\":...}, clean and decode again
                parsed = json.loads(block.encode("utf-8").decode("unicode_escape"))
                if isinstance(parsed, str):  # e.g. extra layer of quotes
                    parsed = json.loads(parsed)
            except Exception as e2:
                logger.error(f"Failed to parse JSON tool call after unescaping: {block} ({e2})")
                continue

        if not isinstance(parsed, dict):
            logger.error(f"Parsed tool call is not a dict: {parsed}")
            continue

        func_name = parsed.get("name")
        args = parsed.get("arguments", {})

        logger.info(f"Parsed tool call: {func_name}({args})")

        tool_calls.append({
            "function": {
                "name": func_name,
                "arguments": json.dumps(args)  # keep arguments as JSON string
            }
        })

    if not tool_calls:
        logger.debug(f"No valid tool calls parsed from: {content}")

    return tool_calls
