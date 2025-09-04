import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from src.message_structures.conversation_manager import ConversationManager
from src.message_structures.message import Message
from src.agents.router import handle_query
from src.agents.chat import ask_model_stream
from src.infer.OllamaInfer import OllamaInfer

api_router = APIRouter()

# Use manager to get conversation
conversation_manager = ConversationManager()

ollama = OllamaInfer()

# New WebSocket Endpoint
@api_router.websocket("/ws/agent")
async def agent_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Websocket connected")
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            query = payload.get('message')
            print(f"Query received in api {query}")

            query_message: Message = Message(
                role = "user", 
                content = query
            )

            conversation_history = conversation_manager.get_conversation_from_id(1)

            # Append the query to the conversation history
            conversation_history.append_message(query_message)

            # model = "hf.co/unsloth/gemma-3n-E4B-it-GGUF:Q2_K_L"
            model = "qwen3:1.7b"
            acknowledgement_prompt = """
            Simply acknowledge receipt of the query in the same way a person might say "Huh" or "let me have a think". DO NOT EXCEED MORE THAN ONE LINE IN YOUR RESPONSE. 
            """
            ack_message = ""
            async for stream in ask_model_stream(
                query, 
                model, 
                conversation_manager,
                ollama):
                ack_message += stream["content"]

            # Now send the full ACK in one message
            await websocket.send_json({
                "type": "ack",
                "message": ack_message.strip()
            })

            # TODO add this to metadata message history
            acknowledgement_response: Message = Message(
                role = "acknowledger",
                content = ack_message
            )

            # conversation_history.append_message(acknowledgement_response)

            # await asyncio.sleep(3)

            await handle_query(
                query, 
                websocket, 
                conversation_manager,
                ollama)
            
    except WebSocketDisconnect:
        print("Client disconnected")
