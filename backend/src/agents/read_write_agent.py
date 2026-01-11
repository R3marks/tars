# src/agents/read_write_agent.py
import logging
import asyncio
import json
import re

from typing import List, Dict
from src.config.Model import Model
from src.infer.ModelManager import ModelManager
from src.message_structures.message import Message
from src.agents.agent_utils import TOOLS, TOOL_MAP
from src.tool_parsers.qwen3_4b_instruct_2507 import parse_qwen4b_tool_call
from src.tool_parsers.granite_4 import parse_granite_tool_call

logger = logging.getLogger("uvicorn.error")

async def read_write(
        query: str, 
        model_manager: ModelManager, 
        tool_model: Model,
        read_model: Model) -> str:
    """
    Agent that performs tool-based file reading and summarisation.
    Returns only the aggregated summaries for router orchestration.
    """
    logger.info("🧠 Starting read_write with tool-based reasoning...")

    messages = [
        Message(role="user", content=query)
    ]

    # --- Step 1️⃣: Ask the model what to do
    agent_response = await asyncio.to_thread(
        model_manager.ask_model,
        tool_model,
        messages,
        system_prompt=None,  # Prompt is in messages
        tools=TOOLS,
        tool_choice="auto",
    )

    tool_calls = []
    for action in agent_response:
        if "type" in action.keys() and action["type"] == "function":
            tool_calls.append(action)

    if len(tool_calls) == 0:
        logger.warning(f"⚠️ No tool calls detected, but not all files read")
        return agent_response

    # --- Step 2️⃣: Execute each tool call
    for tool_call in tool_calls:
        function_name = tool_call["function"]["name"]
        function_arguments = tool_call["function"]["arguments"]
        try:
            args = json.loads(function_arguments)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse tool arguments: {function_arguments} ({e})")
            continue

        logger.info(f"🧰 Executing tool: {function_name} with args: {args}")
        if function_name not in TOOL_MAP:
            logger.error(f"Unknown tool: {function_name}")
            continue

        # Execute the tool
        tool_func = TOOL_MAP[function_name]
        try:
            result = await asyncio.to_thread(tool_func, **args)
            messages.append(Message(
                role="tool", 
                content=result
                ))
        except Exception as e:
            logger.exception(f"Tool execution failed: {e}")
            result = f"[Error executing {function_name}: {e}]"
            messages.append(Message(
                role="tool", 
                content=result
                ))
            
        if function_name == "write_file":
            return result

        # Assume for now that read_file needs to be read in chunks
        summaries = await asyncio.to_thread(
            model_manager.ask_model_in_chunks,
            read_model,
            [Message(role="user", content=result)],
            user_goal=query
        )
        return summaries