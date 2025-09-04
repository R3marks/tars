from abc import ABC, abstractmethod

from src.message_structures.conversation_manager import ConversationManager

class InferInterface(ABC):

    @abstractmethod
    def load_model(self, model: str):
        pass

    @abstractmethod
    def ask_model(
        self, 
        query: str,
        model: str
        ) -> str:
        pass

    @abstractmethod
    async def ask_model_stream(
        self, 
        query: str,
        model: str,
        conversation_manager: ConversationManager,
        system_prompt: str = None,
        ):
        pass
