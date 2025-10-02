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
from src.tool_parsers.qwen3_4b_instruct_2507 import parse_qwen4b_tool_call

logger = logging.getLogger("uvicorn.error")

def read_write(
        query: str,
        model_manager: ModelManager,
        ) -> str:
    
    models = model_manager.config.models_by_role.get(Role.GENERAL, [])

    logger.error(models)

    model: Model = models[-1]

    SYSTEM_PROMPT = """
    You are a CV generator. You have access to three resources:
    - experience.txt (user’s raw experience list)
    - cv_template.html (user’s current CV structure)
    - job_description.txt (the job description)

    Use read_file to load them. 
    Then produce a new CV as HTML.
    Use write_file to save it to generated_cv.html.
    Always use cv_template.html as the base structure. For tasks involving reading files, use the read_file tool first.
    After the read_file result is returned, you may call write_file or return a final response. Please call only one tool per response and wait for the tool result before calling the next tool.
    """

    messages = [
        # Message(role="system", content=SYSTEM_PROMPT),
        Message(role="user", content=query)
    ]

    counter = 0
    while True:
        if counter > 3:
            logger.error(f"Got stuck in a loop with {messages}")
            break
        response: str = model_manager.ask_model(
            model,
            messages,
            tools=TOOLS
        )
        counter += 1 

        # tool_calls: str = parse_qwen_tool_call(response)

        logger.info("Parsing query to extract tool calls")
        tool_calls: str = parse_qwen4b_tool_call(response)

        logger.info(f"Found {len(tool_calls)} tool calls")

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
                        logger.warning(result[:20])
                        # messages.append(Message(
                        #     role = "tool", 
                        #     content = result))
                        # messages.append(Message(
                        #     role = "assistant",
                        #     content = f"I executed {func_name}({args}) and retrieved the result {result}"
                        # ))
                        messages.append(Message(
                            role="assistant",
                            content=f"<tool_result name={func_name}>{result}</tool_result>"
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


