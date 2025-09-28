# src/tool_parsers/qwen3_30b_coder.py
import re
import json
import logging

logger = logging.getLogger("uvicorn.error")

def parse_qwen_tool_call(content: str) -> list[dict]:
    """
    Parse Qwen3-30B's XML-like tool call string into a list of tool call dicts.
    Example input:
        <tool_call>\n<function=read_file>\n<parameter=path>\nT:\\Code\\Apps\\Tars\\talk_cpp.py\n</parameter>\n</function>\n</tool_call>
    Output:
        [{"function": {"name": "read_file", "arguments": "{\"path\": \"T:\\\\Code\\\\Apps\\\\Tars\\\\talk_cpp.py\"}"}}]
    """
    content = content.strip()
    tool_calls = []

    # Match each <tool_call> block
    tool_call_matches = re.finditer(r"<tool_call>(.*?)</tool_call>", content, re.DOTALL)
    for tool_call_match in tool_call_matches:
        tool_content = tool_call_match.group(1).strip()
        
        # Extract function name
        func_match = re.search(r"<function=([^>]+)>(.*?)</function>", tool_content, re.DOTALL)
        if not func_match:
            logger.error(f"Failed to parse function in: {tool_content}")
            continue
        func_name = func_match.group(1).strip()
        params_content = func_match.group(2).strip()

        # Extract parameters
        args = {}
        param_matches = re.finditer(r"<parameter=([^>]+)>(.*?)</parameter>", params_content, re.DOTALL)
        for param_match in param_matches:
            param_name = param_match.group(1).strip()
            # Remove all newlines and extra whitespace, then strip
            param_value = re.sub(r'[\n\r]+|\s+', ' ', param_match.group(2)).strip()
            param_value = param_value.replace("\\n", "")
            
            logger.warning(f"Extracted param: {param_name} : '{param_value}'")
            args[param_name] = param_value

        # Build tool call dict
        tool_calls.append({
            "function": {
                "name": func_name,
                "arguments": json.dumps(args)  # JSON string as expected by llama_cpp_python
            }
        })

    if not tool_calls:
        logger.error(f"No valid tool calls parsed from: {content}")
    else:
        logger.info(f"Parsed tool calls: {tool_calls}")
    return tool_calls