from ollama import chat

def main():
    model = "hf.co/unsloth/gemma-3n-E4B-it-GGUF:Q2_K_L" # 'deepseek-r1:8b'
    messages = [{'role': 'user', 'content': ''}]

    while True:
        user_input = input("You: ")
        messages = [{'role': 'user', 'content': user_input}]
        
        stream = chat(
            model=model,
            messages=messages,
            stream=True,
            think=False
        )

        for chunk in stream:
            print(chunk['message']['content'], end='', flush=True)

            if not chunk.done:
                continue

            tokens_per_second = (chunk.eval_count / chunk.eval_duration) * pow(10, 9)

            print(f"⏱️  LLM reponse time processed prompt with {chunk.prompt_eval_count} tokens, outputted {chunk.eval_count} tokens in {chunk.total_duration * pow(10, -9):.2f}s at {tokens_per_second} tokens/s")

if __name__ == "__main__":
    main()
