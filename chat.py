from ollama import chat
import threading

class ChatApp:
    def __init__(self, model):
        self.model = model
        self.messages = [{'role': 'user', 'content': ''}]
        self.chat_stream = None
        self.user_input = ''

    def run(self):
        while True:
            user_input = input("You: ")
            if not user_input.strip():
                continue

            self.messages.append({'role': 'user', 'content': user_input})
            
            try:
                # Attempt to unpack the return values from chat function
                stream_response = chat(
                    model=self.model,
                    messages=self.messages,
                    stream=True
                )
                assert isinstance(stream_response, tuple) and len(stream_response) == 2, "Expected a tuple with two values"

                self.chat_stream, response_stream = stream_response

                # Process chat responses in a separate thread to improve responsiveness
                response_thread = threading.Thread(target=self.process_responses, args=(response_stream,))
                response_thread.start()
                response_thread.join()  # Wait for the response processing to complete

            except AssertionError as e:
                print(f"AssertionError: {e}")
            except Exception as e:
                print(f"An error occurred: {e}")

    def process_responses(self, response_stream):
        try:
            for chunk in response_stream:
                if 'message' in chunk and 'content' in chunk['message']:
                    print(chunk['message']['content'], end='', flush=True)
                    # Update the user input to make it easier to respond
                    self.user_input = chunk['message']['content']
                else:
                    print("Received an unexpected response format.")
        except Exception as e:
            print(f"Error processing response: {e}")

def main():
    model = 'llama3.2:3b'
    app = ChatApp(model)

    try:
        app.run()
    except KeyboardInterrupt:
        print("Shutting down chat app...")

if __name__ == "__main__":
    main()
