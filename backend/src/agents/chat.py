from ollama import chat
import hashlib
import asyncio
import json
import re
from fastapi.responses import StreamingResponse
from difflib import SequenceMatcher
from src.message_structures.conversation_manager import ConversationManager

SLIDING_WINDOW_LENGTH = 12
REPEAT_THRESHOLD = 3  # number of similar repeats before triggering loop
SIMILARITY_THRESHOLD = 0.9

def ask_model(
        model: str, 
    ):
    try: 
        response = chat(
            model = model, 
            messages = [{
                "role" : "user", 
                "content": "Reply 'yes'"
                }],
            think = False,
            stream = False
        )

        print(response["message"]["content"], flush=True)
        print(f"Seeding loaded in {response.load_duration * pow(10, -9):.2f}s", flush=True)
    except Exception as e:
        print(e)
    

async def ask_model_stream(
        query: str, 
        model: str, 
        conversation_manager: ConversationManager,
        system_prompt: str = None,
        retry=False  # Flag to detect if this is a retry
    ):
    print(query, flush=True)
    
    conversation_history = conversation_manager.get_conversation_from_id(1)
    messages = conversation_history.return_message_history()

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
        seen_windows = []

        for part in response:
            parts.append(part)
            content = part['message']['content']

            # # Append current content to sliding window
            # sliding_window.append(content)
            # if len(sliding_window) > SLIDING_WINDOW_LENGTH:
            #     sliding_window.pop(0)

            # # Loop detection only after window is full
            # if len(sliding_window) == SLIDING_WINDOW_LENGTH:
            #     current_window = normalize("".join(sliding_window))
            #     repeats = sum(
            #         1 for prev in seen_windows
            #         if SequenceMatcher(None, current_window, prev).ratio() > SIMILARITY_THRESHOLD
            #     )
            #     seen_windows.append(current_window)

            #     if repeats >= REPEAT_THRESHOLD:
            #         print(sliding_window)
            #         yield {"type": "error", "content": "Loop detected — stopping stream."}
            #         return

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

# def normalize(text):
#     return re.sub(r"\s+", " ", text.strip().lower())


