import './App.css';
import { useState, useEffect, useRef } from 'react';
import InputBox from './InputBox/InputBox.jsx';
import ChatWindow from './ChatWindow/ChatWindow.jsx';

function App() {
  const [data, setData] = useState([]); // Store full chat history
  const ws = useRef(null);

  useEffect(() => {
    ws.current = new WebSocket('ws://localhost:3001/ws/agent');

    function formatMessageChunk(type, message) {
      let prefix = "";
      let suffix = "";
      let newLine = "\n\n";

      console.log(type);

      switch (type) {
        case "ack":
          prefix = "[ACK] ";
          suffix = " [/ACK]";
          break;
        case "route_decision":
          prefix = "[ROUTER] ";
          suffix = " [/ROUTER]";
          break;
        case "status":
          prefix = "[STATUS] ";
          suffix = " [/STATUS]";
          break;
        case "partial_result":
          prefix = "[PARTIAL RESULT] ";
          suffix = " [/PARTIAL RESULT]";
          break;
        case "final_response":
          prefix = "";
          suffix = "";
          newLine = "";
          break;
        case "error":
          prefix = "ERROR: ";
          newLine = "\n";
          break;
        default:
          break;
      }

      return `${prefix}${message}${suffix}${newLine}`;
    }

    ws.current.onmessage = (event) => {
      const dataObj = JSON.parse(event.data);

      setData((prev) => {
        const updated = [...prev];

        if (updated.length === 0) {
          updated.push({ user: null, reply: "" });
        }

        const formattedChunk = formatMessageChunk(dataObj.type, dataObj.message);

        if (dataObj.type === "ack") {
          updated[updated.length - 1].reply = formattedChunk;
        }

        if (dataObj.type === "status" || dataObj.type === "result") {
          updated[updated.length - 1] = {
            ...updated[updated.length - 1],
            reply: updated[updated.length - 1].reply + formattedChunk
          };
        }

        if (
          dataObj.type === "route_decision"
          || dataObj.type === "final"
          || dataObj.type === "final_response"
        ) {
          if (dataObj.message === "[DONE]") {
            updated[updated.length - 1].done = true;
            return updated;
          }

          updated[updated.length - 1] = {
            ...updated[updated.length - 1],
            reply: updated[updated.length - 1].reply + formattedChunk
          };
        }

        if (dataObj.type === "error") {
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

    setData((prev) => [...prev, { user: message, reply: "...\n\n", done: false }]);

    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      console.log("Sending message " + message);
      ws.current.send(JSON.stringify({
        type: "user_message",
        message: message,
        sessionId: 1
      }));
    }
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
