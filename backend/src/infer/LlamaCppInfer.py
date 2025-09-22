from llama_cpp import ChatCompletionStreamResponseChoice, ChatCompletionStreamResponseDelta, CreateChatCompletionStreamResponse, Llama, CreateChatCompletionResponse,ChatCompletionResponseChoice, ChatCompletionResponseMessage, ChatCompletionRequestUserMessage
import gc
import torch
import time
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
            query: str,
            llm: Llama
            ) -> str: 

        try:
            request: ChatCompletionRequestUserMessage = {
                "role": "user",
                "content": query
            }

            response: CreateChatCompletionResponse = llm.create_chat_completion(
                messages=[request],
                stream=False,
                temperature=0.3
            )

            choice: ChatCompletionResponseChoice = response["choices"]
            message: ChatCompletionResponseMessage = choice[0]["message"]

            return message
        except Exception as e:
            logger.error(f"Error asking model {self.loaded_model_name}: {e}")

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