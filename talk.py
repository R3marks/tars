from ollama import chat

def main():
    model = 'qwen2.5-coder:3b'
    messages = [{'role': 'user', 'content': ''}]

    while True:
        user_input = input("You: ")
        messages = [{'role': 'user', 'content': user_input}]
        
        stream = chat(
            model=model,
            messages=messages,
            stream=True
        )

        for chunk in stream:
            print(chunk['message']['content'], end='', flush=True)
        
        print()

if __name__ == "__main__":
    main()
