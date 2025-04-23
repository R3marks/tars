import './App.css';
import { useState, useEffect } from 'react';
import InputBox from './InputBox/InputBox.js';
import ChatWindow from './ChatWindow/ChatWindow.js';

function App() {
  const [messages, setMessages] = useState("");
  const [data, setData] = useState([]); // Store full chat history

  useEffect(() => {
    if (messages === "") {
      return;
    }

    const body = {
      query: messages,
      sessionId: 1
    };
    const request = new Request("http://localhost:3001/api/ask-query", {
      method: "POST",
      body: JSON.stringify(body),
      headers: {
        "Content-Type": "application/json",
      },
    });

    // Fetch data from the backend
    fetch(request)
      .then((response) => {
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        return response.json();
      })
      .then((data) => {
        // Append new conversation to the history
        setData((prevData) => [...prevData, { user: messages, reply: data.reply }]);
      })
      .catch((error) => {
        console.error('Error fetching data:', error);
      });
  }, [messages]);

  return (
    <div className="app">
      <h1 className="app-header">TARS</h1>
      <ChatWindow data={data} />
      <InputBox askOllama={setMessages} />
    </div>
  );
}

export default App;
