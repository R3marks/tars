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

function App() {
  const [runs, dispatch] = useReducer(chatRunsReducer, []);
  const [connectionState, setConnectionState] = useState("connecting");
  const websocketRef = useRef(null);

  useEffect(() => {
    const websocket = new WebSocket(WEBSOCKET_URL);
    websocketRef.current = websocket;

    websocket.onmessage = (event) => {
      const rawEvent = JSON.parse(event.data);

      dispatch({
        type: "event.received",
        rawEvent,
      });
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
      </div>
    </div>
  );
}

export default App;
