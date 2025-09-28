from llama_cpp import ChatCompletionStreamResponseChoice, ChatCompletionStreamResponseDelta, CreateChatCompletionStreamResponse, Llama, CreateChatCompletionResponse,ChatCompletionResponseChoice, ChatCompletionResponseMessage, ChatCompletionRequestUserMessage
import gc
import torch
import time
import json
import logging

from src.infer.InferInterface import InferInterface
from src.message_structures.message import Message
from src.message_structures.conversation import Conversation
from src.message_structures.conversation_manager import ConversationManager

logger = logging.getLogger("uvicorn.error")

class LlamaCppInfer(InferInterface):

    loaded_model: Llama = None
    loaded_model_name: str = None

    def ask_model(
            self,
            llm: Llama,
            messages: list[Message],
            system_prompt: str = None,
            tools: list = None,  # Optional tools param
            tools_choice: str = "auto"
            ) -> str:
        
        if system_prompt:
            messages.insert(
                0, { 
                "role": "system", 
                "content": system_prompt 
                })

        try:
            logger.info(f"Asking model with messages: {messages[-1].content[:20]}...")
            logger.error(type(llm))
            response: CreateChatCompletionResponse = llm.create_chat_completion(
                messages=messages,
                tools=tools if tools else None,  # Pass tools
                tool_choice=tools_choice,
                stream=False,
                temperature=0.3
            )

            choice: ChatCompletionResponseChoice = response["choices"][0]
            message: ChatCompletionResponseMessage = choice["message"]

            # Return content or JSON stringified tool_calls
            return json.dumps(message.get("tool_calls", message.get("content", "")))

        except Exception as e:
            logger.error(f"Error asking model: {e}")
            return "Error during inference."

    async def ask_model_stream(
        self, 
        llm: Llama,
        messages: list[Message],
        system_prompt: str = None,
        ):

        if system_prompt:
            messages.insert(
                0, { 
                "role": "system", 
                "content": system_prompt 
                })

        try:
            stream: CreateChatCompletionStreamResponse = llm.create_chat_completion(
                messages=messages,
                stream=True,
                temperature=0.3
            )

            full_response = ""
            tokens = 0
            start_time = time.time()
            for chunk in stream:
                choice: ChatCompletionStreamResponseChoice = chunk["choices"]
                delta: ChatCompletionStreamResponseDelta = choice[0]["delta"]
                tokens += 1
                if "content" in delta:
                    content = delta["content"]
                    full_response += content
                    # print(content, end="", flush=True)

                    yield {"type": "chunk", "content": content}
            logger.info(f"Processed query in {tokens/(time.time() - start_time):.2f} tokens/s")

        except Exception as e:
            logger.error(f"Error streaming from model {llm}: {e}")