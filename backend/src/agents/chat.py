from ollama import chat
import asyncio
import json
from fastapi.responses import StreamingResponse

async def handle_chat_query(query: str):
    print(query)
    print(type(query))
    messages = [
        {
            "role": "user", 
            "content": query
        }
    ]

    model="hf.co/unsloth/gemma-3n-E4B-it-GGUF:Q2_K_L"

    async def response_stream():
        try:
            response = chat(
                model=model,
                messages=messages,
                stream=True
            )

            full_reply = ""
            last_part = None  # To store the final part for eval_count etc.

            for part in response:
                content = part['message']['content']
                full_reply += content
                yield content  # Stream this chunk to client immediately
                last_part = part  # Keep overwriting until the last part

            tokens_per_second = (
                last_part.eval_count / last_part.eval_duration
                ) * pow(10, 9)
            
            print(f"⏱️  Tars LLM response time processed prompt with {last_part.prompt_eval_count} tokens, outputted {last_part.eval_count} tokens in {last_part.total_duration * pow(10, -9):.2f}s at {tokens_per_second} tokens/s")

            # reply = response.message.content 
            # reply_message: Message = Message(
            #     role = "assistant", 
            #     content = full_reply
            # )

            # conversation.append_message(reply_message)

            # return { "reply": reply }

        except Exception as e:
            yield f"[Error]: {str(e)}"

    return StreamingResponse(response_stream(), media_type="text/plain")

async def handle_chat_query_ws(query: str, websocket):
    print(f"[WS] Query: {query}")

    # Phase 1: Immediate Acknowledgment
    await websocket.send_json({"type": "ack", "message": "Uhhhh, let's have a look..."})
    await asyncio.sleep(1)

    # Phase 2: Routing Decision
    await websocket.send_json({"type": "route_decision", "message": "Let's see what TARS has to say..."})
    await asyncio.sleep(1)

    # Phase 3: Stream Final Response
    messages = [
        {
            "role": "user", 
            "content": query
        }
    ]

    model = "hf.co/unsloth/gemma-3n-E4B-it-GGUF:Q2_K_L"

    try:
        response = chat(
            model=model, 
            messages=messages, 
            stream=True
            )
        
        full_reply = ""

        for part in response:
            content = part['message']['content']
            full_reply += content
            await websocket.send_json({"type": "final_response", "message": content})

        # Final Stats (optional)
        last_part = part  # Last response part for eval count, duration, etc.
        tokens_per_second = (
            last_part.eval_count / last_part.eval_duration
        ) * pow(10, 9)
        print(full_reply)
        print(f"⏱️  Processed prompt with {last_part.prompt_eval_count} tokens, outputted {last_part.eval_count} tokens in {last_part.total_duration * pow(10, -9):.2f}s at {tokens_per_second} tokens/s")

    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})
