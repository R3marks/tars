from abc import ABC, abstractmethod
from llama_cpp import Llama
from typing import Dict, Any

from src.message_structures.message import Message
from src.config.ModelConfig import ModelConfig
from src.infer.InferInterface import InferInterface
from src.config.Model import Model

class ModelManager(ABC):

    config: ModelConfig
    inference_engine: InferInterface
    loaded_models: Dict[str, Model]

    def __init__(
            self, 
            config: ModelConfig,
            inference_engine: InferInterface
            ):
        self.config = config
        self.inference_engine = inference_engine

    @abstractmethod
    def ask_model(
        self,
        model: Model,
        messages: list[Message],
        tools = None,
        system_prompt: str = None
    ):
        pass
    
    @abstractmethod
    async def ask_model_stream(
        self,
        model: Model, 
        messages: list[Message],
        system_prompt: str = None
    ):
        pass
