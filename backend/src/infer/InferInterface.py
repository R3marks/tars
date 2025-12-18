from abc import ABC, abstractmethod

from src.message_structures.message import Message

class InferInterface(ABC):

    @abstractmethod
    def ask_model(
        self,
        model,
        llm,
        messages: list[Message],
        system_prompt: str = None,
        tools = None,
        tool_choice: str = "auto"
        ) -> str:
        pass

    @abstractmethod
    def ask_model_in_chunks(
        self,
        model,
        llm,
        messages: list[Message],
        user_goal: str = None,
        system_prompt: str = None,
        tools: list = None,
        tool_choice: str = "auto"
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
