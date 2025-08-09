from ollama import chat
import hashlib
import asyncio
import json
from fastapi.responses import StreamingResponse

SLIDING_WINDOW_LENGTH = 25

def ask_model(
        model: str, 
    ):
    try: 
        response = chat(
            model = model, 
            messages = ["This is a message that intends to load the model into memory, reply as quickly as possible and don't worry about the output"],
            think = False,
            stream = False
        )

        print("Managed to get to here")
        print(response, flush=True)
        print(f"Seeding loaded in {response.load_duration * pow(10, -9):.2f}s", flush=True)
    except Exception as e:
        print(e)
    

async def ask_model_stream(
        query: str, 
        model: str, 
        system_prompt: str = None,
        retry=False  # Flag to detect if this is a retry
    ):
    print(query, flush=True)
    
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
            if len(sliding_window) > SLIDING_WINDOW_LENGTH:
                sliding_window.pop(0)

            # Check for repetition if window is full
            if len(sliding_window) == SLIDING_WINDOW_LENGTH:
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

        print(last_part, flush=True)
        print(full_reply[-100:], flush=True)
        print(f"Loaded full response in {last_part.load_duration * pow(10, -9):.2f}s", flush=True)

        print(f"⏱️  Processed prompt with {last_part.prompt_eval_count} tokens, outputted {last_part.eval_count} tokens in {last_part.total_duration * pow(10, -9):.2f}s at {tokens_per_second} tokens/s", flush=True)

    except Exception as e:
        yield {"type": "error", "content": f"[Error]: {str(e)}"}


