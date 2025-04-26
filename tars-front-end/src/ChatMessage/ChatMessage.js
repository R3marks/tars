import React from 'react';
import ReactMarkdown from 'react-markdown';
import { PrismLight as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism/index.js";
import './ChatMessage.css';

export default React.memo(({ user, reply }) => (
  <div className="chat-message">
    <strong className="chat-window-input">User:</strong>
    <ReactMarkdown
      components={{
        p: ({ children }) => <p className="chat-window-input">{children}</p>,
        code({ node, inline, className, children, ...props }) {
          return inline ? (
            <code className="inline-code">{children}</code>
          ) : (
            <SyntaxHighlighter
              style={oneDark}
              language="javascript"
              PreTag="div"
              className="code-block"
              {...props}
            >
              {String(children).replace(/\n$/, '')}
            </SyntaxHighlighter>
          );
        },
      }}
    >
      {user}
    </ReactMarkdown>

    <strong className="chat-window-output">TARS:</strong>
    <ReactMarkdown
      components={{
        p: ({ children }) => <p className="chat-window-output">{children}</p>,
        code({ node, inline, className, children, ...props }) {
          return inline ? (
            <code className="inline-code">{children}</code>
          ) : (
            <SyntaxHighlighter
              style={oneDark}
              language="javascript"
              PreTag="div"
              className="code-block"
              {...props}
            >
              {String(children).replace(/\n$/, '')}
            </SyntaxHighlighter>
          );
        },
      }}
    >
      {reply}
    </ReactMarkdown>
  </div>
));
