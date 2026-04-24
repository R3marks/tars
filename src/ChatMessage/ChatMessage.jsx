import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { PrismLight as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism/index.js";
import { AppIcon } from "../ui/icons.jsx";
import {
  formatElapsedMs,
  getActivityLabel,
  getReadableModelName,
  getTelemetryItems,
} from "../telemetryDisplay.js";
import "./ChatMessage.css";

function SectionTitle({ icon, children }) {
  return (
    <p className="section-title">
      <span className="section-title-icon" aria-hidden="true">
        <AppIcon name={icon} />
      </span>
      <span>{children}</span>
    </p>
  );
}

function humanizeLabel(value = "") {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function getPathFilename(path = "") {
  if (!path) {
    return "";
  }

  const parts = path.split(/[\\/]/);
  return parts[parts.length - 1] || path;
}

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

function KeyValueList({ items }) {
  const populatedItems = items.filter((item) => item.value);

  if (populatedItems.length === 0) {
    return null;
  }

  return (
    <dl className="meta-list">
      {populatedItems.map((item) => (
        <div key={item.label} className="meta-row">
          <dt>{item.label}</dt>
          <dd>{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}

function StringList({ title, items, tone = "default" }) {
  if (!items?.length) {
    return null;
  }

  return (
    <div className={`detail-group tone-${tone}`}>
      <p className="detail-group-title">{title}</p>
      <ul className="detail-list">
        {items.map((item, index) => (
          <li key={`${title}-${index}`}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function PathList({ title, paths }) {
  if (!paths?.length) {
    return null;
  }

  return (
    <div className="detail-group">
      <p className="detail-group-title">{title}</p>
      <div className="path-list">
        {paths.map((path, index) => (
          <div key={`${path}-${index}`} className="path-chip" title={path}>
            <span className="path-chip-name">{getPathFilename(path)}</span>
            <span className="path-chip-value">{path}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function normalizeArtifactStatus(status = "", path = "") {
  if (!path) {
    return status || "";
  }

  if (status === "completed" || status === "needs_review") {
    return "generated";
  }

  return status || "generated";
}

function TelemetryMeta({ telemetry, includeTokensPerSecond = false, includeOutputTokens = false }) {
  const items = getTelemetryItems(telemetry, {
    includeTokensPerSecond,
    includeOutputTokens,
  });

  if (items.length === 0) {
    return null;
  }

  return (
    <dl className="telemetry-meta">
      {items.map((item) => (
        <div key={`${item.label}-${item.value}`} className="telemetry-meta-item">
          <dt>{item.label}</dt>
          <dd>{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}

function getTelemetryReasoningContent(telemetry) {
  return telemetry?.invocation?.reasoning_content || "";
}

function ReasoningPanel({ title = "Reasoning", content = "" }) {
  const trimmedContent = (content || "").trim();

  if (!trimmedContent) {
    return null;
  }

  return (
    <details className="reasoning-panel">
      <summary className="reasoning-summary">{title}</summary>
      <div className="reasoning-content">
        <pre className="reasoning-pre">{trimmedContent}</pre>
      </div>
    </details>
  );
}

function RunSummary({ run }) {
  const summaryTelemetry = run.completionTelemetry || run.latestTelemetry;
  const terminalRun = run.status === "completed"
    || run.status === "failed"
    || run.status === "blocked"
    || run.status === "needs_review";

  if (!summaryTelemetry || !terminalRun) {
    return null;
  }

  const summaryItems = [];
  const elapsedLabel = formatElapsedMs(summaryTelemetry?.run?.elapsed_ms || summaryTelemetry?.timing?.elapsed_ms);
  const modelName = getReadableModelName(summaryTelemetry);
  const activityLabel = getActivityLabel(summaryTelemetry);
  const resultsCount = summaryTelemetry?.counts?.results || 0;
  const artifactsCount = summaryTelemetry?.counts?.artifacts || 0;
  const invocationCount = summaryTelemetry?.counts?.model_invocations || 0;

  if (elapsedLabel && elapsedLabel !== "0 ms") {
    summaryItems.push({ label: "Run", value: elapsedLabel });
  }

  if (modelName) {
    summaryItems.push({ label: "Model", value: modelName });
  }

  if (invocationCount > 0) {
    summaryItems.push({ label: "Calls", value: String(invocationCount) });
  }

  if (resultsCount > 0) {
    summaryItems.push({ label: "Results", value: String(resultsCount) });
  }

  if (artifactsCount > 0) {
    summaryItems.push({ label: "Artifacts", value: String(artifactsCount) });
  }

  if (summaryItems.length === 0 && !activityLabel) {
    return null;
  }

  return (
    <section className="assistant-section assistant-section-shell telemetry-shell">
      <SectionTitle icon="operator">Run Summary</SectionTitle>
      <div className="run-summary">
        {activityLabel ? <p className="run-summary-activity">{activityLabel}</p> : null}
        {summaryItems.length > 0 ? (
          <div className="summary-chip-list">
            {summaryItems.map((item) => (
              <div key={`${item.label}-${item.value}`} className="summary-chip">
                <span className="summary-chip-label">{item.label}</span>
                <span className="summary-chip-value">{item.value}</span>
              </div>
            ))}
          </div>
        ) : null}
      </div>
    </section>
  );
}

function TimelineList({ timelineItems }) {
  const operatorItems = timelineItems.filter((item) => item.kind !== "progress");

  if (operatorItems.length === 0) {
    return null;
  }

  return (
    <section className="assistant-section assistant-section-shell operator-log-shell">
      <SectionTitle icon="operator">Operator Log</SectionTitle>
      <div className="timeline-list">
        {operatorItems.map((item, index) => (
          <div key={`${item.timestamp}-${item.kind}-${index}`} className={`timeline-item ${item.kind}`}>
            <div
              className={`timeline-pill timeline-pill-${item.kind}`}
              title={item.detail || item.value}
            >
              <span className="timeline-pill-label">{item.label}</span>
              <span className="timeline-pill-value">{item.value}</span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function TaskAgentSelectionCard({ result }) {
  return (
    <article className="structured-card result-card result-card-wide result-card-agent">
      <div className="agent-card-layout">
        <div className="agent-card-icon-wrap" aria-hidden="true">
          <AppIcon name="agent" className="agent-card-icon" />
        </div>
        <div className="agent-card-body">
          <div className="card-topline">
            <p className="card-eyebrow">Task Agent</p>
            <span className="status-chip status-info">Selected</span>
          </div>
          <p className="card-title">{humanizeLabel(result.agent_name || "unknown_agent")}</p>
          {result.reason ? <p className="card-copy">{result.reason}</p> : null}
        </div>
      </div>
    </article>
  );
}

function SkillResultCard({ result }) {
  const statusToneByStatus = {
    completed: "success",
    needs_review: "warning",
    blocked: "danger",
  };

  return (
    <article className="structured-card result-card result-card-wide">
      <div className="card-topline">
        <div className="card-eyebrow-wrap">
          <AppIcon name="skill" className="card-eyebrow-icon" />
          <p className="card-eyebrow">Skill Result</p>
        </div>
        <span className={`status-chip status-${statusToneByStatus[result.status] || "neutral"}`}>
          {humanizeLabel(result.status || "unknown")}
        </span>
      </div>
      <p className="card-title">{humanizeLabel(result.artifact_type || "artifact")}</p>
      {result.summary ? <p className="card-copy">{result.summary}</p> : null}
      <StringList title="Changes" items={result.change_summary} tone="success" />
      <StringList title="Needs Input" items={result.missing_inputs} tone="danger" />
      <StringList title="Review Notes" items={result.review_notes} tone="warning" />
      <ReasoningPanel content={getTelemetryReasoningContent(result.telemetry)} />
      <TelemetryMeta telemetry={result.telemetry} />
    </article>
  );
}

function WorkflowSummaryCard({ result }) {
  return (
    <article className="structured-card result-card result-card-wide">
      <div className="card-topline">
        <div className="card-eyebrow-wrap">
          <AppIcon name="workflow" className="card-eyebrow-icon" />
          <p className="card-eyebrow">Workflow Summary</p>
        </div>
        <span className="status-chip status-info">Overview</span>
      </div>
      {result.summary ? <p className="card-copy">{result.summary}</p> : null}
      <StringList title="Changed" items={result.changed} tone="success" />
      <StringList title="Blocked" items={result.blocked} tone="danger" />
      <StringList title="Needs Review" items={result.needs_review} tone="warning" />
      <PathList title="Output Paths" paths={result.output_paths} />
      <ReasoningPanel content={getTelemetryReasoningContent(result.telemetry)} />
      <TelemetryMeta telemetry={result.telemetry} />
    </article>
  );
}

function PartialResultCard({ result }) {
  return (
    <article className="structured-card result-card">
      <div className="card-topline">
        <p className="card-eyebrow">Partial Result</p>
        <span className="status-chip status-danger">{humanizeLabel(result.status || "blocked")}</span>
      </div>
      <p className="card-copy">
        {result.expected_outcome
          ? `Could not fully satisfy: ${result.expected_outcome}`
          : "This run could not fully satisfy one of its expected outcomes."}
      </p>
    </article>
  );
}

function ToolResultCard({ result }) {
  const statusToneByStatus = {
    completed: "success",
    failed: "danger",
  };
  const resultText = String(result.result || "").trim();
  const preview = resultText.length > 700
    ? `${resultText.slice(0, 700).trim()}...`
    : resultText;

  return (
    <article className="structured-card result-card result-card-wide">
      <div className="card-topline">
        <div className="card-eyebrow-wrap">
          <AppIcon name="tool" className="card-eyebrow-icon" />
          <p className="card-eyebrow">Tool Result</p>
        </div>
        <span className={`status-chip status-${statusToneByStatus[result.status] || "neutral"}`}>
          {humanizeLabel(result.status || "unknown")}
        </span>
      </div>
      <p className="card-title">{result.tool_name || "tool"}</p>
      {result.arguments ? (
        <p className="card-copy">
          <code className="inline-code">{result.arguments}</code>
        </p>
      ) : null}
      {preview ? <pre className="structured-details compact">{preview}</pre> : null}
      <TelemetryMeta telemetry={result.telemetry} />
    </article>
  );
}

function UnknownResultCard({ result }) {
  return (
    <article className="structured-card result-card">
      <p className="card-eyebrow">{result.result_type || "result"}</p>
      <pre className="structured-details">
        {JSON.stringify(result, null, 2)}
      </pre>
    </article>
  );
}

function renderResultCard(result, index) {
  const key = `${result.timestamp}-${result.result_type || "result"}-${index}`;

  if (result.result_type === "task_agent_selection") {
    return <TaskAgentSelectionCard key={key} result={result} />;
  }

  if (result.result_type === "skill_result") {
    return <SkillResultCard key={key} result={result} />;
  }

  if (result.result_type === "workflow_summary") {
    return <WorkflowSummaryCard key={key} result={result} />;
  }

  if (result.result_type === "partial_result") {
    return <PartialResultCard key={key} result={result} />;
  }

  if (result.result_type === "tool_result") {
    return <ToolResultCard key={key} result={result} />;
  }

  return <UnknownResultCard key={key} result={result} />;
}

function ResultList({ results }) {
  if (results.length === 0) {
    return null;
  }

  return (
    <section className="assistant-section assistant-section-shell results-shell">
      <SectionTitle icon="results">Results</SectionTitle>
      <div className="card-list">
        {results.map((result, index) => renderResultCard(result, index))}
      </div>
    </section>
  );
}

function ArtifactCard({ artifact }) {
  const displayStatus = normalizeArtifactStatus(artifact.status, artifact.path);
  const statusToneByStatus = {
    completed: "success",
    generated: "success",
    needs_review: "warning",
    blocked: "danger",
  };

  return (
    <article className="structured-card result-card">
      <div className="card-topline">
        <div className="card-eyebrow-wrap">
          <AppIcon name="artifact" className="card-eyebrow-icon" />
          <p className="card-eyebrow">Artifact</p>
        </div>
        {displayStatus ? (
          <span className={`status-chip status-${statusToneByStatus[displayStatus] || "neutral"}`}>
            {humanizeLabel(displayStatus)}
          </span>
        ) : null}
      </div>
      <p className="card-title">{humanizeLabel(artifact.label || artifact.artifact_type || "artifact")}</p>
      {artifact.path ? (
        <div className="artifact-path-block" title={artifact.path}>
          <p className="artifact-path-name">{getPathFilename(artifact.path)}</p>
          <p className="artifact-path">{artifact.path}</p>
        </div>
      ) : null}
      <ReasoningPanel content={getTelemetryReasoningContent(artifact.telemetry)} />
      <TelemetryMeta telemetry={artifact.telemetry} />
    </article>
  );
}

function ArtifactList({ artifacts }) {
  if (artifacts.length === 0) {
    return null;
  }

  return (
    <section className="assistant-section assistant-section-shell artifacts-shell">
      <SectionTitle icon="artifacts">Artifacts</SectionTitle>
      <div className="card-list">
        {artifacts.map((artifact, index) => (
          <ArtifactCard key={`${artifact.timestamp}-${artifact.path}-${index}`} artifact={artifact} />
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
            <section className="assistant-section acknowledgement-strip assistant-section-shell acknowledgement-shell">
              <SectionTitle icon="acknowledgement">Acknowledgement</SectionTitle>
              <p className="acknowledgement-copy">{run.acknowledgementText}</p>
              <ReasoningPanel content={getTelemetryReasoningContent(run.acknowledgementTelemetry)} />
              <TelemetryMeta
                telemetry={run.acknowledgementTelemetry}
                includeTokensPerSecond
                includeOutputTokens
              />
            </section>
          ) : null}

          <TimelineList timelineItems={run.timelineItems || []} />
          <ResultList results={run.results} />
          <ArtifactList artifacts={run.artifacts} />

          {run.responseText ? (
            <section className="assistant-section assistant-response assistant-section-shell response-shell">
              <SectionTitle icon="response">Response</SectionTitle>
              <MarkdownBlock isFinal={shouldUseMarkdownFeatures}>
                {run.responseText}
              </MarkdownBlock>
              <ReasoningPanel
                content={
                  run.responseReasoningText
                  || getTelemetryReasoningContent(run.completionTelemetry || run.responseTelemetry)
                }
              />
              <TelemetryMeta
                telemetry={run.completionTelemetry || run.responseTelemetry}
                includeTokensPerSecond
                includeOutputTokens
              />
            </section>
          ) : null}

          <RunSummary run={run} />

          {run.error ? (
            <section className="assistant-section error-state assistant-section-shell failure-shell">
              <SectionTitle icon="failure">Failure</SectionTitle>
              <p className="error-message">{run.error.message}</p>
              {run.error.detail ? <p className="error-detail">{run.error.detail}</p> : null}
            </section>
          ) : null}
        </div>
      </div>
    </article>
  );
});
