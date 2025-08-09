import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from message_structures.QueryRequest import QueryRequest
from src.agents.router import handle_query
from src.agents.chat import ask_model_stream

api_router = APIRouter()

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

            # model = "hf.co/unsloth/gemma-3n-E4B-it-GGUF:Q2_K_L"
            model = "qwen3:1.7b"
            acknowledgement_prompt = """
            Simply acknowledge receipt of the query in the same way a person might say "Huh" or "let me have a think". DO NOT EXCEED MORE THAN ONE LINE IN YOUR RESPONSE. 
            """
            ack_message = ""
            async for stream in ask_model_stream(query, model, acknowledgement_prompt):
                ack_message += stream["content"]

            # Now send the full ACK in one message
            await websocket.send_json({
                "type": "ack",
                "message": ack_message.strip()
            })

            # await asyncio.sleep(3)

            await handle_query(query, websocket)
    except WebSocketDisconnect:
        print("Client disconnected")
