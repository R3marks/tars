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

    # Extract file paths from query
    file_paths = re.findall(r'`(T:\\[^`]+)`', query)
    logger.info(f"Extracted file paths: {file_paths}")

    messages = [
        # Message(role="system", content="""
        #     You are an assistant that processes file-related queries. For each file path in the user's query, generate a read_file tool call to read its contents. Do not respond until all files are read unless explicitly asked to summarize or answer without reading. Use the read_file tool for each file path provided.
        # """),
        Message(role="user", content=query)
    ]
    read_files = set()  # Track read files
    max_iterations = len(file_paths) + 1  # Allow one extra for final response

    iteration = 0
    while iteration < max_iterations:
        # --- Step 1️⃣: Ask the model what to do
        response = await asyncio.to_thread(
            model_manager.ask_model,
            tool_model,
            messages,
            system_prompt=None,  # Prompt is in messages
            tools=TOOLS,
            tool_choice="auto",
        )

        # Extract the actual message dict
        raw_message = response["choices"][0]["message"]
        content = raw_message.get("content", "") if isinstance(raw_message, dict) else str(raw_message)
        logger.error(content)

        # Try parsing tool calls
        tool_calls = parse_qwen4b_tool_call(content)

        if not tool_calls:
            if all(path in read_files for path in file_paths):
                logger.info("All files read, returning final response")
                return content
            logger.warning("⚠️ No tool calls detected, but not all files read")
            return content

        # --- Step 2️⃣: Execute each tool call
        aggregated_summary = ""
        for tool_call in tool_calls:
            tool_name = tool_call["function"]["name"]
            args_json = tool_call["function"].get("arguments", "{}")
            try:
                args = json.loads(args_json)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse tool arguments: {args_json} ({e})")
                continue

            logger.info(f"🧰 Executing tool: {tool_name} with args: {args}")
            if tool_name not in TOOL_MAP:
                logger.error(f"Unknown tool: {tool_name}")
                continue

            # Execute the tool
            tool_func = TOOL_MAP[tool_name]
            try:
                result = await asyncio.to_thread(tool_func, **args)
                read_files.add(args.get("path"))  # Track read file
                messages.append(Message(role="tool", content=result))
            except Exception as e:
                logger.exception(f"Tool execution failed: {e}")
                result = f"[Error executing {tool_name}: {e}]"
                messages.append(Message(role="tool", content=result))

            # Summarize the result (in chunks)
            if result and isinstance(result, str):
                summaries = await asyncio.to_thread(
                    model_manager.ask_model_in_chunks,
                    read_model,
                    [Message(role="user", content=result)],
                    user_goal=query
                )
                aggregated_summary += f"\n\n[Tool {tool_name} result summary]\n{summaries}"

        iteration += 1

    logger.error(f"Reached max iterations ({max_iterations}) without reading all files: {read_files}")
    return aggregated_summary.strip()