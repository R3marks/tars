import './App.css';
import { useState, useEffect } from 'react';
import InputBox from './InputBox/InputBox.jsx';
import ChatWindow from './ChatWindow/ChatWindow.jsx';

function App() {
  const [messages, setMessages] = useState("");
  const [data, setData] = useState([]); // Store full chat history

  function sendMessageToTars(message) {
    // Add user message instantly
    const tempMessage = { user: message, reply: "..." }; // Placeholder
    setData((prev) => [...prev, tempMessage]);
  
    const body = {
      query: message,
      sessionId: 1
    };
  
    fetch("http://localhost:3001/api/ask-query", {
      method: "POST",
      body: JSON.stringify(body),
      headers: {
        "Content-Type": "application/json",
      },
    })
      .then((response) => response.json())
      .then((res) => {
        // Replace the placeholder reply
        setData((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = { user: message, reply: res.reply };
          return updated;
        });
      })
      .catch((err) => {
        console.error(err);
        setData((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = { user: message, reply: "⚠️ Error" };
          return updated;
        });
      });
  }

  return (
    <div className="app">
      <h1 className="app-header">TARS</h1>
      <ChatWindow data={data} />
      <InputBox askOllama={sendMessageToTars} />
    </div>
  );
}

export default App;
