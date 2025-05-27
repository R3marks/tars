from ollama import chat

def main():
    model = 'deepseek-r1:8b'
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
        
        print()

if __name__ == "__main__":
    main()
