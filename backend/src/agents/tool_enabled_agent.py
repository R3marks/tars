# src/agents/tool_enabled_agent.py
import logging
from typing import List, Any
from llama_cpp import Llama
from src.infer.ModelManager import ModelManager
from src.infer.InferInterface import InferInterface
from src.config.ModelConfig import ModelConfig
from src.message_structures.message import Message
from src.agents.agent_utils import TOOLS, CV_SYSTEM_PROMPT

logger = logging.getLogger("uvicorn.error")

async def tool_enabled_agent(
        llm: Llama, 
        messages: List[Message], 
        model_manager: ModelManager,
        system_prompt: str = None
) -> str:
    # Add CV instructions + tool descriptions to system prompt
    if system_prompt:
        system_prompt = f"{system_prompt}\n{CV_SYSTEM_PROMPT}"
    else:
        system_prompt = CV_SYSTEM_PROMPT
    
    # Ensure system prompt is first message
    if not messages or messages[0].role != "system":
        messages.insert(0, Message(role="system", content=system_prompt))

    while True:
        # Convert Pydantic messages to dicts for llama_cpp_python
        messages_dict = [{"role": m.role, "content": m.content} for m in messages]
        logger.error(type(model_config))
        # Call model with native tools
        response = model_config.manager.ask_model(
            messages=messages_dict,
            llm=llm,
            tools=TOOLS
        )

        logger.info(f"Model response: {response[:50]}...")

        # Check for tool_calls in response (dict, not str)
        if isinstance(response, dict) and "tool_calls" in response:
            tool_calls = response["tool_calls"]
            messages.append(Message(role="assistant", content=str(response)))  # Log tool call
            
            for tool_call in tool_calls:
                func_name = tool_call["function"]["name"]
                try:
                    args = json.loads(tool_call["function"]["arguments"])
                except json.JSONDecodeError:
                    args = {}
                    logger.error(f"Invalid tool args: {tool_call['function']['arguments']}")

                if func_name in [t["function"]["name"] for t in TOOLS]:
                    logger.info(f"Executing tool: {func_name} with args {args}")
                    try:
                        result = eval(f"{func_name}(**args)")  # Execute tool
                        messages.append(Message(role="tool", content=result))
                    except Exception as e:
                        messages.append(Message(role="tool", content=f"Tool error: {str(e)}"))
                else:
                    messages.append(Message(role="tool", content=f"Unknown tool: {func_name}"))
        else:
            # Final response (content is str)
            return response if isinstance(response, str) else response.get("content", "Error: No content")