from src.agents.chat import handle_chat_query, handle_chat_query_ws

async def handle_query(query: str):
    return await handle_chat_query(query)

async def handle_query_ws(query: str, websocket):
    await handle_chat_query_ws(query, websocket)
