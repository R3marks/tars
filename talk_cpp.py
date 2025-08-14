from llama_cpp import ChatCompletionStreamResponseChoice, ChatCompletionStreamResponseDelta, CreateChatCompletionStreamResponse, List, Llama
import pprint

def main():
    # llm = Llama.from_pretrained(
    #     repo_id="unsloth/gemma-3n-E4B-it-GGUF",
    #     filename="gemma-3n-E4B-it-F16.gguf",
    #     n_gpu_layers=35,
    #     n_batch=512,
    #     n_ctx=4096,
    # )

    llm = Llama(
        model_path = "T:/Models/gemma-3n-E4B-it-Q2_K.gguf",
        n_gpu_layers=-1,
        n_batch=1024
    )

    messages = []

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue

        # llm.reset()

        if len(messages) > 3:
            messages = messages[2:]

        messages.append({
            "role": "user", 
            "content": user_input
            })

        # Each call resets cache automatically
        stream: CreateChatCompletionStreamResponse = llm.create_chat_completion(
            messages=messages,
            stream=True,
            temperature=0.9
        )

        full_response = ""
        for chunk in stream:
            # pprint.pprint(chunk)
            choice: ChatCompletionStreamResponseChoice = chunk["choices"]
            delta: ChatCompletionStreamResponseDelta = choice[0]["delta"]
            if "content" in delta:
                content = delta["content"]
                full_response += content
                print(content, end="", flush=True)

        messages.append({
            "role": "assistant", 
            "content": full_response
        })
        print("\n")

if __name__ == "__main__":
    main()
