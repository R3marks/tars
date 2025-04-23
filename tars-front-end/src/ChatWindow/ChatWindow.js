import { useEffect, useRef } from 'react';
import './ChatWindow.css';

export default function ChatWindow({ data }) {
  const chatWindowRef = useRef(null);

  // Scroll to the latest message
  useEffect(() => {
    if (chatWindowRef.current) {
      chatWindowRef.current.scrollTop = chatWindowRef.current.scrollHeight;
    }
  }, [data]);

  return (
    <div className="chat-window" ref={chatWindowRef}>
      {data.map((item, index) => (
        <div key={index} className="chat-message">
          <p className="chat-window-input">User: {item.user}</p>
          <p className="chat-window-output">LLM: {item.reply}</p>
        </div>
      ))}
    </div>
  );
}
