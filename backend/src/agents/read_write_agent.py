import logging
import json 

from typing import List, Any
from llama_cpp import Llama
from src.config.Model import Model
from src.config.Role import Role
from src.infer.ModelManager import ModelManager
from src.infer.InferInterface import InferInterface
from src.config.ModelConfig import ModelConfig
from src.message_structures.message import Message
from src.agents.agent_utils import TOOLS, TOOL_MAP, CV_SYSTEM_PROMPT
from src.tool_parsers.qwen3_30b_coder import  parse_qwen_tool_call

logger = logging.getLogger("uvicorn.error")

def read_write(
        query: str,
        model_manager: ModelManager,
        ) -> str:
    
    models = model_manager.config.models_by_role.get(Role.CODER, [])

    logger.error(models)

    model: Model = models[-1]

    SYSTEM_PROMPT = """
    You are a file processing assistant. For tasks involving reading files, read the content using the read_file tool. Process the content as requested (e.g., extract the first line or command). Use the write_file tool to save results to the specified file. Return a clear response confirming task completion after all tools are executed. Avoid repeating tool calls unnecessarily.
    """

    messages = [
        # Message(
        #     role="system", 
        #     content=SYSTEM_PROMPT),
        Message(
            role="user", 
            content=query)
        ]

    counter = 0
    while True:
        if counter > 3:
            logger.error(f"Got stuck in a loop with {messages}")
            break
        response: str = model_manager.ask_model(
            messages,
            model,
            tools=TOOLS
        )
        counter += 1 

        tool_calls: str = parse_qwen_tool_call(response)

        if tool_calls:
            for tool_call in tool_calls:
                func_name = tool_call["function"]["name"]
                try:
                    args = json.loads(tool_call["function"]["arguments"])
                except json.JSONDecodeError:
                    args = {}
                    logger.error(f"Invalid tool args: {tool_call['function']['arguments']}")

                if func_name in TOOL_MAP:
                    logger.info(f"Executing tool: {func_name} with args {args}")
                    try:
                        result = TOOL_MAP[func_name](**args)
                        logger.warning(result)
                        messages.append(Message(
                            role = "assistant", 
                            content = result))
                        messages.append(Message(
                            role = "user",
                            content = "write the first command to this file `T:\Code\Apps\Tars\commands_one.txt`"
                        ))
                    except Exception as e:
                        logger.error(f"Error running function {func_name} with parameters {args}: {e}")
                        messages.append(Message(
                            role = "tool", 
                            content = f"Tool error: {str(e)}"))
                else:
                    messages.append(Message(
                            role = "tool", 
                            content =  f"Unknown tool: {func_name}"))
        else:
            return response


