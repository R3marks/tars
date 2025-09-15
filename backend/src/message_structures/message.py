from pydantic import BaseModel

class Message(BaseModel):
    role: str
    content: str

    def update(self, query: str):
        return self.model_copy(
            update={
                "content": query
            }
        )

    def add_context(self, context: str):
        return self.model_copy(update={
            "content": self.content + "\n\n" + context
        })
    