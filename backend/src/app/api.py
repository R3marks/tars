import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from message_structures.QueryRequest import QueryRequest
from src.agents.router import handle_query, handle_query_ws

api_router = APIRouter()

@api_router.post("/api/query")
async def process_query(request: QueryRequest):
    print(request)
    query = request.query
    return await handle_query(query)

# New WebSocket Endpoint
@api_router.websocket("/ws/agent")
async def agent_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            query = payload.get('message')
            await handle_query_ws(query, websocket)
    except WebSocketDisconnect:
        print("Client disconnected")
