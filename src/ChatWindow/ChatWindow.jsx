import { useEffect, useMemo, useRef, useState } from "react";
import "./ChatWindow.css";
import ChatMessage from "../ChatMessage/ChatMessage.jsx";
import TarsSpinner from "../TarsSpinner/TarsSpinner.jsx";
import {
  formatElapsedMs,
  getActivityLabel,
  getLiveElapsedMs,
  getReadableModelName,
} from "../telemetryDisplay.js";

function buildActiveReasoning(activeRun) {
  if (!activeRun) {
    return "";
  }

  if (activeRun.responseReasoningText) {
    return activeRun.responseReasoningText.trim();
  }

  return activeRun.latestTelemetry?.invocation?.reasoning_content || "";
}

function buildActiveRunSummary(activeRun) {
  if (!activeRun) {
    return "";
  }

  const activityLabel = getActivityLabel(activeRun.latestTelemetry);

  if (activityLabel) {
    return activityLabel;
  }

  const latestProgressItem = [...(activeRun.progressItems || [])].reverse()[0];

  if (latestProgressItem?.status) {
    return latestProgressItem.status;
  }

  const latestTimelineItem = [...(activeRun.timelineItems || [])].reverse()[0];

  if (latestTimelineItem?.kind === "phase" && latestTimelineItem.value) {
    return `Phase: ${latestTimelineItem.value}`;
  }

  if (latestTimelineItem?.kind === "route" && latestTimelineItem.value) {
    return `Route selected: ${latestTimelineItem.value}`;
  }

  return activeRun.userMessage || "Working.";
}

function buildActiveRunMeta(activeRun, nowMs) {
  if (!activeRun?.latestTelemetry) {
    return [];
  }

  const items = [];
  const modelName = getReadableModelName(activeRun.latestTelemetry);
  const liveElapsedMs = getLiveElapsedMs(activeRun.latestTelemetry, activeRun.createdAt, nowMs);
  const elapsedLabel = formatElapsedMs(liveElapsedMs || activeRun.latestTelemetry?.timing?.elapsed_ms);

  if (modelName) {
    items.push(modelName);
  }

  if (elapsedLabel && elapsedLabel !== "0 ms") {
    items.push(elapsedLabel);
  }

  return items;
}

export default function ChatWindow({ runs, activeRun, activeRunExists, onRunAction }) {
  const chatWindowRef = useRef(null);
  const activeReasoningRef = useRef(null);
  const previousRunCountRef = useRef(runs.length);
  const [currentTimeMs, setCurrentTimeMs] = useState(() => Date.now());
  const activeRunSummary = useMemo(() => buildActiveRunSummary(activeRun), [activeRun]);
  const activeReasoning = useMemo(() => buildActiveReasoning(activeRun), [activeRun]);
  const activeRunMeta = useMemo(
    () => buildActiveRunMeta(activeRun, currentTimeMs),
    [activeRun, currentTimeMs],
  );

  useEffect(() => {
    if (!chatWindowRef.current) {
      previousRunCountRef.current = runs.length;
      return;
    }

    const runCountChanged = previousRunCountRef.current !== runs.length;

    if (runCountChanged || activeRunExists) {
      chatWindowRef.current.scrollTop = chatWindowRef.current.scrollHeight;
    }

    previousRunCountRef.current = runs.length;
  }, [runs, activeRunExists]);

  useEffect(() => {
    if (!activeReasoningRef.current) {
      return;
    }

    activeReasoningRef.current.scrollTop = activeReasoningRef.current.scrollHeight;
  }, [activeReasoning]);

  useEffect(() => {
    if (!activeRunExists) {
      return undefined;
    }

    setCurrentTimeMs(Date.now());
    const intervalId = window.setInterval(() => {
      setCurrentTimeMs(Date.now());
    }, 1000);

    return () => window.clearInterval(intervalId);
  }, [activeRunExists]);

  if (runs.length === 0) {
    return (
      <section className="chat-window empty" ref={chatWindowRef}>
        <div className="empty-state">
          <p className="empty-state-title">Console idle.</p>
          <p className="empty-state-copy">
            Send a prompt to bring the terminal online. TARS will acknowledge,
            route, think, and answer inside the same run without flattening the
            whole process into one blob.
          </p>
        </div>
      </section>
    );
  }

  return (
    <section className="chat-window" ref={chatWindowRef}>
      <div className="chat-content">
        {runs.map((run) => (
          <ChatMessage key={run.runId || run.localId} run={run} onRunAction={onRunAction} />
        ))}

        {activeRunExists ? (
          <div className="terminal-activity">
            <span className="terminal-activity-light" />
            <TarsSpinner size="medium" tone="signal" />
            <div className="terminal-activity-copy">
              <p className="terminal-activity-title">Working on: {activeRunSummary}</p>
              {activeRunMeta.length > 0 ? (
                <p className="terminal-activity-meta">{activeRunMeta.join(" | ")}</p>
              ) : null}
              {activeReasoning ? (
                <details className="terminal-reasoning">
                  <summary className="terminal-reasoning-summary">Live reasoning</summary>
                  <div className="terminal-reasoning-content" ref={activeReasoningRef}>
                    <pre className="terminal-reasoning-pre">{activeReasoning}</pre>
                  </div>
                </details>
              ) : null}
            </div>
          </div>
        ) : null}
      </div>
    </section>
  );
}

