import { useEffect, useRef } from 'react';
import './ChatWindow.css';
import ChatMessage from '../ChatMessage/ChatMessage.jsx';

export default function ChatWindow({ data }) {
  const chatWindowRef = useRef(null);
  const prevDataLengthRef = useRef(data.length);

  useEffect(() => {
    const lastItem = data[data.length - 1];
    const prevLength = prevDataLengthRef.current;

    // Only scroll when a new user message is added
    if (data.length > prevLength && lastItem.user) {
      if (chatWindowRef.current) {
        chatWindowRef.current.scrollTop = chatWindowRef.current.scrollHeight;
      }
    }

    prevDataLengthRef.current = data.length;
  }, [data]);

  return (
    <div className="chat-window" ref={chatWindowRef}>
      {data.map((item, index) => (
        <ChatMessage
          key={index}
          user={item.user}
          reply={item.reply}
          done={item.done}
        />
      ))}
    </div>
  );
}
