from abc import ABC, abstractmethod

from src.message_structures.message import Message

class InferInterface(ABC):

    @abstractmethod
    def ask_model(
        self, 
        query: str,
        llm
        ) -> str:
        pass

    @abstractmethod
    async def ask_model_stream(
        self, 
        llm,
        messages: list[Message],
        system_prompt: str = None,
        ):
        pass
