from src.agents.chat import ask_model, ask_model_stream

async def handle_query(query: str, websocket):
    model = "hf.co/unsloth/gemma-3n-E4B-it-GGUF:Q2_K_L"

    print("Seeding full query model first", flush=True)
    ask_model(query)

    print("handling full query now", flush=True)
    async for stream in ask_model_stream(
        query, 
        model):

        await websocket.send_json({
            "type": "final_response", 
            "message": stream["content"]
            })
