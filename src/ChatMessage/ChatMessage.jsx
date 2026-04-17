import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { PrismLight as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism/index.js";
import "./ChatMessage.css";

function CodeRenderer({ node, className = "", children, ...props }) {
  const match = /language-(\w+)/.exec(className || "");
  const hasMultipleLines = node?.children?.[0]?.value?.includes("\n");
  const language = match ? match[1] : (hasMultipleLines ? "text" : undefined);

  if (match || hasMultipleLines) {
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

  return <code className="inline-code">{children}</code>;
}

function MarkdownBlock({ children, isFinal = true }) {
  return (
    <ReactMarkdown
      components={{ code: CodeRenderer }}
      remarkPlugins={isFinal ? [remarkGfm] : []}
    >
      {children ?? ""}
    </ReactMarkdown>
  );
}

function TimelineList({ timelineItems }) {
  if (timelineItems.length === 0) {
    return null;
  }

  return (
    <section className="assistant-section">
      <p className="section-title">Operator Log</p>
      <div className="timeline-list">
        {timelineItems.map((item, index) => (
          <div key={`${item.timestamp}-${item.kind}-${index}`} className={`timeline-item ${item.kind}`}>
            {item.kind === "progress" ? (
              <>
                <span className="timeline-bullet" />
                <div>
                  <p className="timeline-text">{item.text}</p>
                  {Object.keys(item.details || {}).length > 0 ? (
                    <pre className="structured-details">
                      {JSON.stringify(item.details, null, 2)}
                    </pre>
                  ) : null}
                </div>
              </>
            ) : (
              <div className="timeline-pill" title={item.detail || item.value}>
                <span className="timeline-pill-label">{item.label}</span>
                <span className="timeline-pill-value">{item.value}</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

function ResultList({ results }) {
  if (results.length === 0) {
    return null;
  }

  return (
    <section className="assistant-section">
      <p className="section-title">Results</p>
      <div className="card-list">
        {results.map((result, index) => (
          <article key={`${result.timestamp}-${index}`} className="structured-card">
            <p className="card-eyebrow">{result.result_type || "result"}</p>
            <pre className="structured-details">
              {JSON.stringify(result, null, 2)}
            </pre>
          </article>
        ))}
      </div>
    </section>
  );
}

function ArtifactList({ artifacts }) {
  if (artifacts.length === 0) {
    return null;
  }

  return (
    <section className="assistant-section">
      <p className="section-title">Artifacts</p>
      <div className="card-list">
        {artifacts.map((artifact, index) => (
          <article key={`${artifact.timestamp}-${index}`} className="structured-card">
            <p className="card-eyebrow">{artifact.artifact_type || "artifact"}</p>
            <p className="artifact-path">{artifact.path || ""}</p>
            {artifact.label ? <p className="artifact-label">{artifact.label}</p> : null}
            {artifact.status ? <p className="artifact-status">Status: {artifact.status}</p> : null}
          </article>
        ))}
      </div>
    </section>
  );
}

export default React.memo(function ChatMessage({ run }) {
  const shouldUseMarkdownFeatures = run.status === "completed";

  return (
    <article className="chat-message">
      <div className="message user">
        <div className="message-inner user-surface">
          <strong className="chat-label">YOU</strong>
          <MarkdownBlock isFinal>{run.userMessage}</MarkdownBlock>
        </div>
      </div>

      <div className="message tars">
        <div className="message-inner tars-surface">
          <div className="assistant-header">
            <strong className="chat-label">TARS</strong>
          </div>

          {run.acknowledgementText ? (
            <section className="assistant-section acknowledgement-strip">
              <p className="section-title">Acknowledgement</p>
              <p className="acknowledgement-copy">{run.acknowledgementText}</p>
            </section>
          ) : null}

          <TimelineList timelineItems={run.timelineItems || []} />
          <ResultList results={run.results} />
          <ArtifactList artifacts={run.artifacts} />

          {run.responseText ? (
            <section className="assistant-section assistant-response">
              <p className="section-title">Response</p>
              <MarkdownBlock isFinal={shouldUseMarkdownFeatures}>
                {run.responseText}
              </MarkdownBlock>
            </section>
          ) : null}

          {run.error ? (
            <section className="assistant-section error-state">
              <p className="section-title">Failure</p>
              <p className="error-message">{run.error.message}</p>
              {run.error.detail ? <p className="error-detail">{run.error.detail}</p> : null}
            </section>
          ) : null}
        </div>
      </div>
    </article>
  );
});
