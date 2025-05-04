from .message import Message

class Conversation():
    conversation_id: int
    messages: list[Message]

    def __init__(self, id: int):
        self.conversation_id = id
        self.messages = []

    def get_conversation_id(self):
        return self.conversation_id

    def append_message(self, message: Message):
        self.messages.append(message)

    def return_message_history(self):
        return self.messages