from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from ollama import chat
import logging

from message_structures.QueryRequest import QueryRequest
from message_structures.conversation import Conversation
from message_structures.message import Message

from prompts.tars_system_prompt import TARS_PROMPT
from prompts.router_prompt import ROUTER_RESPONSE

from embed.vector_store import VectorStore


logger = logging.getLogger(__name__)

app = FastAPI()

origins = [
    "http://localhost:3000",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialise a conversation
conversation = Conversation(1)

# Create and append the system prompt
router_system_prompt: Message = Message(
    role = "system", 
    content = ""
)
conversation.append_message(router_system_prompt)

# Persistent vector store connection
vector_db = VectorStore()

@app.post("/api/debug")
async def debug_endpoint(request: Request):
    logger.info("DEBUG endpoint hit.")
    try:
        json_data = await request.json()
        logger.info(f"Received raw JSON: {json_data}")
        return {"received": json_data}
    except Exception as e:
        logger.error(f"Failed to parse JSON: {str(e)}")
        return {"error": str(e)}


@app.post("/api/ask-query")
async def ask_query(req: QueryRequest):
    # Retrieve the session ID and query from the request
    session_id = req.sessionId
    query = req.query

    # Load the relevant conversation 
    if conversation.get_conversation_id() != session_id:
        print(f"Haven't initiliased session for id {session_id} for given ids {conversation.conversation_id}")

    # RAG Query - Step 1: Search vector DB
    results = vector_db.query(query, n_results=5)
    print(results)

    # Step 2: Format retrieved docs as system context
    retrieved_docs = "\n\n".join(results['documents'][0])  # results is a dict with 'documents' key
    print("##################")
    print(retrieved_docs)

    context_message = Message(
        role="system",
        content=f"Relevant context from documentation:\n\n{retrieved_docs}"
    )

    # Step 3: Prepare the final message list
    messages = conversation.append_message(context_message)

    # Formulate the request into a query object
    query_message: Message = Message(
        role = "user", 
        content = query
    )

    # Append the query to the conversation history
    conversation.append_message(query_message)

    # Prepare message history for LLM
    messages = conversation.return_message_history()

    # Choose the appropriate model
    model = "gemma3:4b"

    if "think" in query:
        model = "qwen3:0.6b"

    try:
        response = chat(
            model = model,
            messages = messages
        )

        reply = response.message.content 
        reply_message: Message = Message(
            role = "assistant", 
            content = reply
        )

        conversation.append_message(reply_message)

        return { "reply": reply }

    except Exception as e:
        return { "error": str(e) }
