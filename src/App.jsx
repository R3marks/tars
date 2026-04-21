import "./App.css";
import { useEffect, useMemo, useReducer, useRef, useState } from "react";
import InputBox from "./InputBox/InputBox.jsx";
import ChatWindow from "./ChatWindow/ChatWindow.jsx";
import TarsSpinner from "./TarsSpinner/TarsSpinner.jsx";
import { chatRunsReducer, hasActiveRun } from "./runState.js";

const WEBSOCKET_URL = "ws://localhost:3001/ws/agent";
const SESSION_ID = 1;

function getSignalState(connectionState, activeRunExists) {
  if (connectionState === "disconnected") {
    return {
      tone: "offline",
      label: "Disconnected",
      detail: "No backend link",
    };
  }

  if (connectionState === "error") {
    return {
      tone: "warning",
      label: "Error",
      detail: "Transport fault",
    };
  }

  if (connectionState === "connected" && activeRunExists) {
    return {
      tone: "processing",
      label: "Processing",
      detail: "Live stream active",
    };
  }

  if (connectionState === "connected") {
    return {
      tone: "online",
      label: "Connected",
      detail: "Standing by",
    };
  }

  return {
    tone: "booting",
    label: "Connecting",
    detail: "Establishing link",
  };
}

function findActiveRun(runs) {
  for (let index = runs.length - 1; index >= 0; index -= 1) {
    const run = runs[index];

    if (run.status === "queued" || run.status === "accepted" || run.status === "running") {
      return run;
    }
  }

  return null;
}

function actionRunsSilently(action) {
  return action?.action_type === "job.save"
    || action?.action_type === "job.select_for_draft";
}

function buildActionToast(rawEvent) {
  if (rawEvent?.event_kind !== "run.result") {
    return null;
  }

  const payload = rawEvent.payload || {};
  if (payload.result_type !== "saved_job_state") {
    return null;
  }

  const state = String(payload.state || "").trim();
  if (state !== "saved" && state !== "selected_for_draft") {
    return null;
  }

  const jobRecord = payload.job_record || {};
  const jobTitle = jobRecord.title || payload.job_slug || "Job";
  const company = jobRecord.company ? ` at ${jobRecord.company}` : "";
  const message = state === "saved"
    ? `${jobTitle}${company} saved.`
    : `${jobTitle}${company} selected for draft.`;

  return {
    id: `${rawEvent.run_id || "run"}-${payload.job_slug || state}-${Date.now()}`,
    message,
    tone: state === "saved" ? "success" : "selected",
  };
}

function App() {
  const [runs, dispatch] = useReducer(chatRunsReducer, []);
  const [connectionState, setConnectionState] = useState("connecting");
  const [toasts, setToasts] = useState([]);
  const websocketRef = useRef(null);

  useEffect(() => {
    const websocket = new WebSocket(WEBSOCKET_URL);
    websocketRef.current = websocket;

    websocket.onmessage = (event) => {
      const rawEvent = JSON.parse(event.data);
      const actionToast = buildActionToast(rawEvent);

      dispatch({
        type: "event.received",
        rawEvent,
      });

      if (actionToast) {
        setToasts((currentToasts) => [...currentToasts, actionToast]);
        window.setTimeout(() => {
          setToasts((currentToasts) => currentToasts.filter((toast) => toast.id !== actionToast.id));
        }, 2600);
      }
    };

    websocket.onopen = () => {
      setConnectionState("connected");
    };

    websocket.onclose = () => {
      setConnectionState("disconnected");
    };

    websocket.onerror = () => {
      setConnectionState("error");
    };

    return () => {
      websocket.close();
    };
  }, []);

  function sendMessageToTars(messageText) {
    const userMessage = messageText.trim();

    if (!userMessage) {
      return;
    }

    const createdAt = new Date().toISOString();
    const localId = `local-${createdAt}`;

    dispatch({
      type: "run.queued",
      localId,
      sessionId: SESSION_ID,
      userMessage,
      createdAt,
    });

    if (!websocketRef.current || websocketRef.current.readyState !== WebSocket.OPEN) {
      return;
    }

    websocketRef.current.send(JSON.stringify({
      event_kind: "run.create",
      session_id: SESSION_ID,
      payload: {
        message: userMessage,
      },
    }));
  }

  function sendRunAction(actionContext) {
    const { action, run } = actionContext || {};

    if (!action || !run) {
      return;
    }

    if (action.action_type === "job.open_source") {
      const sourceUrl = action.source_url || action.url || "";
      if (sourceUrl) {
        window.open(sourceUrl, "_blank", "noopener,noreferrer");
      }
      return;
    }

    const createdAt = new Date().toISOString();
    const silentAction = actionRunsSilently(action);
    const runId = silentAction ? (run.runId || "") : "";
    const actionPayload = {
      action_type: action.action_type,
      job_slug: action.job_slug || undefined,
      job_slugs: action.job_slugs?.length ? action.job_slugs : undefined,
      target_status: action.target_status || undefined,
      artifact_types: action.artifact_types?.length ? action.artifact_types : undefined,
      label: action.label || undefined,
      display_mode: silentAction ? "silent" : "visible",
      source: "frontend",
    };

    dispatch({
      type: "action.sent",
      runId,
      runLocalId: run.localId,
      payload: actionPayload,
      createdAt,
    });

    if (!websocketRef.current || websocketRef.current.readyState !== WebSocket.OPEN) {
      return;
    }

    websocketRef.current.send(JSON.stringify({
      event_kind: "run.action",
      session_id: SESSION_ID,
      run_id: runId || undefined,
      payload: actionPayload,
    }));
  }

  const activeRunExists = hasActiveRun(runs);
  const signalState = getSignalState(connectionState, activeRunExists);
  const activeRun = useMemo(() => findActiveRun(runs), [runs]);

  return (
    <div className="app-shell">
      <div className="console-shell">
        <header className="console-header">
          <div className="console-signal-group">
            <div className={`signal-lamp ${signalState.tone}`}>
              {signalState.tone === "processing" ? (
                <TarsSpinner size="compact" tone="signal" />
              ) : (
                <span className="signal-core" />
              )}
            </div>
            <div className="signal-copy">
              <p className="signal-label">{signalState.label}</p>
              <p className="signal-detail">{signalState.detail}</p>
            </div>
          </div>

          <div className="console-brand">
            <p className="console-brand-caption">CASE / TARS</p>
            <div className="console-brand-row">
              <p className="console-brand-mark">T A R S</p>
              <p className="console-brand-cn">{"\u5854\u65af"}</p>
            </div>
          </div>

          <div className="console-heading">
            <p className="console-kicker">Interface</p>
            <p className="console-title">Terminal Session</p>
          </div>
        </header>

        <main className="app-main">
          <ChatWindow
            runs={runs}
            activeRun={activeRun}
            activeRunExists={activeRunExists}
            onRunAction={sendRunAction}
          />
        </main>

        <footer className="app-footer">
          <InputBox
            askOllama={sendMessageToTars}
            disabled={connectionState !== "connected"}
            canSend={connectionState === "connected" && !activeRunExists}
            connectionState={connectionState}
            hasActiveRun={activeRunExists}
          />
        </footer>

        {toasts.length > 0 ? (
          <div className="toast-stack" aria-live="polite" aria-atomic="true">
            {toasts.map((toast) => (
              <div className={`toast-message ${toast.tone}`} key={toast.id}>
                <span className="toast-light" />
                <span>{toast.message}</span>
              </div>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}

export default App;
