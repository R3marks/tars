import { useEffect, useRef } from 'react';
import './ChatWindow.css';
import ChatMessage from '../ChatMessage/ChatMessage.jsx'

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
        <ChatMessage key={index} user={item.user} reply={item.reply} />
      ))}
    </div>
  );
}
