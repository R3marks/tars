from ollama import chat
import hashlib
import asyncio
import json
import re
from fastapi.responses import StreamingResponse
from difflib import SequenceMatcher
from src.infer.InferInterface import InferInterface
from src.message_structures.conversation_manager import ConversationManager

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
        query: str, 
        model: str, 
        conversation_manager: ConversationManager,
        inference_provider: InferInterface,
        system_prompt: str = None
    ):

    async for chunk in inference_provider.ask_model_stream(
        query,
        model,
        conversation_manager,
        system_prompt
        ):
        yield chunk

