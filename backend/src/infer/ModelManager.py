from abc import ABC, abstractmethod
from llama_cpp import Llama
from typing import Dict, Any

from src.message_structures.message import Message
from src.infer.InferInterface import InferInterface
from src.config.Model import Model

class ModelManager(ABC):

    loaded_models: Dict[str, Model]

    @abstractmethod
    def ask_model(
        query: str,
        model: Model,
        inference_provider: InferInterface,
    ):
        pass
    
    @abstractmethod
    async def ask_model_stream(
        model: Model, 
        messages: list[Message],
        inference_provider: InferInterface,
        system_prompt: str = None
    ):
        pass
