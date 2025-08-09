import React from "react";
import ReactMarkdown from "react-markdown";
import { PrismLight as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism/index.js";
import "./ChatMessage.css";

export default React.memo(({ user, reply }) => {
  const CodeRenderer = ({ node, className = "", children, ...props }) => {
    const match = /language-(\w+)/.exec(className || "");

    // Check if it's a multi-line single backtick code based on content
    const isMultiLineSingleBacktick = !match && node?.children?.[0]?.value?.includes('\n');

    // Determine the language: if match exists use it, otherwise if it's a multi-line single backtick, use 'text', otherwise no language (inline).
    const language = match ? match[1] : (isMultiLineSingleBacktick ? 'text' : undefined);

    if (match || isMultiLineSingleBacktick) {
      // fenced code block with language
      return (
        <SyntaxHighlighter
          style={oneDark}
          language={language}
          PreTag="div"
          className="code-block"
          {...props}
        >
          {String(children).replace(/\n$/, "")}
        </SyntaxHighlighter>
      );
    }
    
    // inline code (or code with no language)
    return <code className="inline-code">{children}</code>;
  };

  return (
    <div className="chat-message">
      {/* USER (left) */}
      <div className="message user">
        <div className="message-inner">
          <strong className="chat-label">User:</strong>
          <ReactMarkdown components={{ code: CodeRenderer }}>
            {user ?? ""}
          </ReactMarkdown>
        </div>
      </div>

      {/* TARS (right) */}
      <div className="message tars">
        <div className="message-inner">
          <strong className="chat-label">TARS:</strong>
          <ReactMarkdown components={{ code: CodeRenderer }}>
            {reply ?? ""}
          </ReactMarkdown>
        </div>
      </div>
    </div>
  );
});
