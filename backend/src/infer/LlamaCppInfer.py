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

    def load_model(self, model: str) -> Llama:
        logger.info(f"Loading model from {model}")
        start_time = time.time()
        try:
            llm = Llama(
                model_path=model,
                n_gpu_layers=-1,
                n_batch=1024,
                n_ctx=4096,
                verbose=False
            )
            logger.info(f"Loaded model from {model} in {time.time() - start_time:.2f} seconds")
            return llm
        except Exception as e:
            logger.error(f"Failed to load model from {model}: {str(e)}")
            raise

    def unload_model(self):
        if self.loaded_model is None:
            return
        
        logger.info(f"Unloading model {self.loaded_model_name}")
        try:
            del self.loaded_model
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                logger.info(f"CUDA memory cleared. VRAM free: {torch.cuda.memory_available()/1024**2:.2f} MiB")
        except Exception as e:
            logger.error(f"Error unloading model {self.loaded_model_name}: {str(e)}")

    def ready_model(self, model: str) -> Llama:
        model_name: str = model.split("/")[-1]

        if model_name != self.loaded_model_name:
            self.unload_model()

            self.loaded_model = self.load_model(model)
            self.loaded_model_name = model_name

        return self.loaded_model

    def ask_model(
            self, 
            query: str,
            model: str
            ) -> str: 
        
        llm: Llama = self.ready_model(model)

        try:
            request: ChatCompletionRequestUserMessage = {
                "role": "user",
                "content": query
            }

            response: CreateChatCompletionResponse = llm.create_chat_completion(
                messages=[request],
                stream=False,
                temperature=0.9
            )

            choice: ChatCompletionResponseChoice = response["choices"]
            message: ChatCompletionResponseMessage = choice[0]["message"]

            return message
        except Exception as e:
            logger.error(f"Error asking model {self.loaded_model_name}: {e}")

    async def ask_model_stream(
        self, 
        model: str,
        messages: list[Message],
        system_prompt: str = None,
        ):

        # Ready model
        llm: Llama = self.ready_model(model)

        if system_prompt:
            messages.insert(
                0, { 
                "role": "system", 
                "content": system_prompt 
                })

        # Ask LLM 
        try:
            stream: CreateChatCompletionStreamResponse = llm.create_chat_completion(
                messages=messages,
                stream=True,
                temperature=0.9
            )

            full_response = ""
            for chunk in stream:
                choice: ChatCompletionStreamResponseChoice = chunk["choices"]
                delta: ChatCompletionStreamResponseDelta = choice[0]["delta"]
                if "content" in delta:
                    content = delta["content"]
                    full_response += content
                    # print(content, end="", flush=True)

                    yield {"type": "chunk", "content": content}

        except Exception as e:
            logger.error(f"Error streaming from model {self.loaded_model_name}: {e}")