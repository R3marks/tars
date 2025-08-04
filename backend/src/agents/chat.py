from ollama import chat
import hashlib
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

async def ask_model_stream(
        query: str, 
        model: str, 
        system_prompt: str = None,
        retry=False  # Flag to detect if this is a retry
    ):
    print(query)
    
    messages = [ { "role": "user", "content": query } ]

    if system_prompt:
        messages.insert(0, { "role": "system", "content": system_prompt })

    try: 
        response = chat(
            model = model, 
            messages = messages,
            think = False,
            stream = True
        )

        full_reply = ""
        parts = []
        sliding_window = []
        seen_sequences = {}

        for part in response:
            parts.append(part)
            content = part['message']['content']

            # Append current content to sliding window
            sliding_window.append(content)
            if len(sliding_window) > 10:
                sliding_window.pop(0)

            # Check for repetition if window is full
            if len(sliding_window) == 10:
                window_concat = ''.join(sliding_window)
                window_hash = hashlib.md5(window_concat.encode('utf-8')).hexdigest()

                count = seen_sequences.get(window_hash, 0) + 1
                seen_sequences[window_hash] = count

                if count >= 5:
                    print(f"Detected Loop on hash {window_hash} after {count} repeats")
                    print(sliding_window)
                    print(parts[-20:])

                    if not retry:
                        # Retry once with loop-breaking prompt
                        print("Retrying prompt with loop prevention instructions...")
                        recovery_prompt = query + "\n\nIMPORTANT: Do not repeat yourself. Be concise and finish your answer."
                        async for retry_chunk in ask_model_stream(recovery_prompt, model, system_prompt, retry=True):
                            yield retry_chunk
                    else:
                        # On second failure, return error
                        yield {"type": "error", "content": "Loop detected and retry failed."}
                    return  # Break out of stream loop after handling

            full_reply += content
            yield {"type": "chunk", "content": content}

        # Final Stats
        last_part = part
        tokens_per_second = (
            last_part.eval_count / last_part.eval_duration
        ) * pow(10, 9)
        print(last_part)
        print(full_reply[-100:])
        print(f"⏱️  Processed prompt with {last_part.prompt_eval_count} tokens, outputted {last_part.eval_count} tokens in {last_part.total_duration * pow(10, -9):.2f}s at {tokens_per_second} tokens/s")

    except Exception as e:
        yield {"type": "error", "content": f"[Error]: {str(e)}"}


