from ollama import chat
import logging
from fastapi.responses import StreamingResponse
from difflib import SequenceMatcher
from src.infer.InferInterface import InferInterface
from src.message_structures.message import Message

logger = logging.getLogger("uvicorn.error")

def ask_model(
        query: str,
        model: str,
        inference_provider: InferInterface,
    ):

    return inference_provider.ask_model(
        query,
        model,
    )
    

async def ask_model_stream(
        model: str, 
        messages: list[Message],
        inference_provider: InferInterface,
        system_prompt: str = None
    ):

    async for chunk in inference_provider.ask_model_stream(
        model,
        messages,
        system_prompt
        ):
        yield chunk

