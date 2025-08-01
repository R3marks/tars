import './App.css';
import { useState, useEffect, useRef } from 'react';
import InputBox from './InputBox/InputBox.jsx';
import ChatWindow from './ChatWindow/ChatWindow.jsx';

function App() {
  const [data, setData] = useState([]); // Store full chat history
  const ws = useRef(null);

  useEffect(() => {
    ws.current = new WebSocket('ws://localhost:3001/ws/agent');

    // Helper function to format message chunk
    function formatMessageChunk(type, message) {
      let prefix = "";
      let suffix = "\n\n";  // Always add newline for now

      switch (type) {
        case "ack":
          prefix = "[ACK] ";
          break;
        case "route_decision":
          prefix = "[ROUTER] ";
          break;
        case "final_response":
          prefix = "";
          suffix = "";  // Streaming chunks—no newline after each fragment
          break;
        case "error":
          prefix = "⚠️ ERROR: ";
          suffix = "\n";
          break;
        default:
          break;
      }

      return `${prefix}${message}${suffix}`;
    }

    ws.current.onmessage = (event) => {
      const dataObj = JSON.parse(event.data);
      console.log("Received:", dataObj);

      setData((prev) => {
        const updated = [...prev];

        if (updated.length === 0) {
          updated.push({ user: null, reply: "" });
        }

        const formattedChunk = formatMessageChunk(dataObj.type, dataObj.message);

        if (dataObj.type === "ack" || dataObj.type === "route_decision" || dataObj.type === "final_response") {
          // Always update last message
          updated[updated.length - 1] = {
            ...updated[updated.length - 1],
            reply: updated[updated.length - 1].reply + formattedChunk
          };
        } else if (dataObj.type === "error") {
          // Errors get a new message block
          updated.push({ user: null, reply: formattedChunk });
        }

        return updated;
      });
    };

    ws.current.onopen = () => {
      console.log("WebSocket Connected");
    };

    ws.current.onclose = () => {
      console.log("WebSocket Disconnected");
    };

    return () => {
      ws.current.close();
    };
  }, []);

  function sendMessageToTars(message) {
    console.log("Sending message to Tars (WS)");

    // Add user message instantly
    setData((prev) => [...prev, { user: message, reply: "...\n\n" }]);

    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      console.log("Sending message" + message)
      ws.current.send(JSON.stringify({
        type: "user_message",
        message: message,
        sessionId: 1  // future-proofing for multi-session support
      }));
    }
  }

  return (
    <div className="app">
      <h1 className="app-header">TARS</h1>
      <ChatWindow data={data} />
      <InputBox 
        askOllama={sendMessageToTars}
        showTars={() => {}}
      />
    </div>
  );
}

export default App;
