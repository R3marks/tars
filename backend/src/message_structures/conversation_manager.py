from src.message_structures.conversation import Conversation

class ConversationManager:
    def __init__(self):
        self._conversations = {}

    def get_conversation_from_id(
            self, 
            conversation_id: int
            ) -> Conversation:
        
        if conversation_id not in self._conversations:
            self._conversations[conversation_id] = Conversation(conversation_id)
            
        return self._conversations[conversation_id]
