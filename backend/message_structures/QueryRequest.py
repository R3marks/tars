from pydantic import BaseModel

class QueryRequest(BaseModel):
    query: str
    sessionId: int