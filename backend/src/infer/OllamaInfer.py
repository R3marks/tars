from ollama import chat

from src.infer.InferInterface import InferInterface
from src.message_structures.conversation_manager import ConversationManager

class OllamaInfer(InferInterface):

    def ask_model(
            self, 
            query: str,
            model: str
            ) -> str:
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
            self, 
            query: str,
            model: str,
            conversation_manager: ConversationManager,
            system_prompt: str = None,
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

            for part in response:
                content = part['message']['content']

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
