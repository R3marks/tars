from pydantic import BaseModel

class Message(BaseModel):
    role: str
    content: str

    def add_context(self, context: str):
        return self.model_copy(update={
            "content": self.content + "\n\n" + context
        })