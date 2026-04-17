import { useEffect, useMemo, useRef } from "react";
import "./ChatWindow.css";
import ChatMessage from "../ChatMessage/ChatMessage.jsx";
import TarsSpinner from "../TarsSpinner/TarsSpinner.jsx";

function buildActiveRunSummary(activeRun) {
  if (!activeRun) {
    return "";
  }

  const latestTimelineItem = [...(activeRun.timelineItems || [])].reverse()[0];

  if (latestTimelineItem?.kind === "progress" && latestTimelineItem.text) {
    return latestTimelineItem.text;
  }

  if (latestTimelineItem?.kind === "phase" && latestTimelineItem.value) {
    return `Phase: ${latestTimelineItem.value}`;
  }

  if (latestTimelineItem?.kind === "route" && latestTimelineItem.value) {
    return `Route selected: ${latestTimelineItem.value}`;
  }

  return activeRun.userMessage || "Working.";
}

export default function ChatWindow({ runs, activeRun, activeRunExists }) {
  const chatWindowRef = useRef(null);
  const activeRunSummary = useMemo(() => buildActiveRunSummary(activeRun), [activeRun]);

  useEffect(() => {
    if (!chatWindowRef.current) {
      return;
    }

    chatWindowRef.current.scrollTop = chatWindowRef.current.scrollHeight;
  }, [runs]);

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
      {runs.map((run) => (
        <ChatMessage key={run.runId || run.localId} run={run} />
      ))}

      {activeRunExists ? (
        <div className="terminal-activity">
          <span className="terminal-activity-light" />
          <TarsSpinner size="medium" tone="signal" />
          <p className="terminal-activity-copy">
            Working on: {activeRunSummary}
          </p>
        </div>
      ) : null}
    </section>
  );
}
