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
        p: ({ node, children }) => {
          const isOnlyInline = node.children?.every(
            child => child.type === 'text' || (child.tagName === 'code' && child.properties?.className?.includes('inline-code'))
          );

          if (isOnlyInline) {
            return <p className="chat-window-output">{children}</p>;
          }

          return <>{children}</>; // Avoid wrapping if it contains block elements
        },
        code({ inline, className = "", children, ...props }) {
          const match = /language-(\w+)/.exec(className || "");
          const language = match?.[1];

          // Always render inline code spans if inline is true
          if (inline) {
            return <code className="inline-code">{children}</code>;
          }

          // If NOT inline but no language is specified → inline code in block context (e.g., lists)
          if (!language) {
            return <code className="inline-code">{children}</code>;
          }

          // This is a fenced code block → render SyntaxHighlighter
          return (
            <SyntaxHighlighter
              style={oneDark}
              language={language}
              PreTag="div"
              className="code-block"
              {...props}
            >
              {String(children).replace(/\n$/, '')}
            </SyntaxHighlighter>
          );
        }
      }}
    >
      {user}
    </ReactMarkdown>

    <strong className="chat-window-output">TARS:</strong>
    <ReactMarkdown
      components={{
        p: ({ node, children }) => {
          const isCodeBlock = node.children?.some(child => child.tagName === 'code');
          if (isCodeBlock) {
            return <>{children}</>;  // No <p> wrapper
          }
          return <p className="chat-window-output">{children}</p>;
        },

        code({ node, inline, className = "", children, ...props }) {
          const match = /language-(\w+)/.exec(className || "");
          const language = match?.[1];

          if (inline || node?.parent?.type === 'paragraph') {
            return <code className="inline-code">{children}</code>;
          }

          return (
            <SyntaxHighlighter
              style={oneDark}
              language={language || "text"}
              PreTag="div"
              className="code-block"
              {...props}
            >
              {String(children).replace(/\n$/, '')}
            </SyntaxHighlighter>
          );
        }
      }}
    >
      {reply}
    </ReactMarkdown>
  </div>
));
