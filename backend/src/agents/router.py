from src.agents.chat import handle_chat_query, ask_model_stream

async def handle_query(query: str):
    return await handle_chat_query(query)

async def handle_query_ws(query: str, websocket):
    model = "hf.co/unsloth/gemma-3n-E4B-it-GGUF:Q2_K_L"
    print("handling full query now")
    async for stream in ask_model_stream(
        query, 
        model):

        await websocket.send_json({
            "type": "final_response", 
            "message": stream["content"]
            })
