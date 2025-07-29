import './App.css';
import { useState, useEffect } from 'react';
import InputBox from './InputBox/InputBox.jsx';
import ChatWindow from './ChatWindow/ChatWindow.jsx';

function App() {
  const [messages, setMessages] = useState("");
  const [data, setData] = useState([]); // Store full chat history

  function sendMessageToTars(message) {
    console.log("Sending message to Tars")
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
      // .then((response) => response.json())
      .then((response) => {
        // Replace the placeholder reply
        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        function read() {
          reader.read().then(({ done, value }) => {
            if (done) return;

            const chunk = decoder.decode(value, { stream: true });
            // Append chunk to last message's reply
            setData((prev) => {
              const updated = [...prev];
              updated[updated.length - 1] = { 
                ...updated[updated.length - 1],
                reply: updated[updated.length - 1].reply + chunk
              };
              return updated;
            });

            read(); // Continue reading next chunk
          });
        }

        read();
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

  function askTarsToSee() {
    // Add user message instantly
    const tempMessage = { user: "SENDING SCREENSHOT", reply: "..." }; // Placeholder
    setData((prev) => [...prev, tempMessage]);

    console.log("Trying to ask Tars to see!")
    fetch("http://localhost:3001/api/screenshot", {
      method: "POST",
    })
      .then((response) => response.json())
      .then((res) => {
        console.log("Screenshot result:", res);
        // You can update the UI to show response
        setData((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = { 
            user: "SCREENSHOT", 
            reply: res.reply
          };
          return updated;
        });
      })
      .catch((err) => {
        console.error("Screenshot failed", err);
      });
  }

  return (
    <div className="app">
      <h1 className="app-header">TARS</h1>
      <ChatWindow data={data} />
      <InputBox 
      askOllama = {sendMessageToTars}
      showTars = {askTarsToSee}
      />
    </div>
  );
}

export default App;
