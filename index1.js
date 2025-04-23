import React, { useState } from 'react';

function App() {
    const [input, setInput] = useState('');
    const [messages, setMessages] = useState([]);

    const handleInputChange = (e) => {
        setInput(e.target.value);
    };

    const handleSubmit = async () => {
        if (!input.trim()) return;

        setMessages([...messages, { role: 'user', content: input }]);
        
        try {
            const response = await fetch('/chat-stream', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message: input })
            });

            const chatResponse = await response.json();
            setMessages([...messages, { role: 'assistant', content: chatResponse.message }]);
        } catch (error) {
            console.error('Error fetching chat response:', error);
        }

        setInput('');
    };

    return (
        <div>
            <h1>Chat App</h1>
            <input
                type="text"
                value={input}
                onChange={handleInputChange}
                placeholder="Type your message..."
            />
            <button onClick={handleSubmit}>Send</button>

            <ul>
                {messages.map((message, index) => (
                    <li key={index}>
                        {message.role === 'user' ? 'You: ' : 'Assistant: '}
                        {message.content}
                    </li>
                ))}
            </ul>
        </div>
    );
}

export default App;
