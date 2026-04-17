import { useRef, useState } from "react";
import "./InputBox.css";

export default function InputBox({
  askOllama,
  disabled = false,
  canSend = true,
  connectionState = "connecting",
  hasActiveRun = false,
}) {
  const [value, setValue] = useState("");
  const textareaRef = useRef(null);

  function submitValue() {
    const trimmedValue = value.trim();

    if (!trimmedValue || disabled || !canSend) {
      textareaRef.current?.focus();
      return;
    }

    askOllama(trimmedValue);
    setValue("");
    requestAnimationFrame(() => {
      textareaRef.current?.focus();
    });
  }

  function handleKeyPress(event) {
    if (event.key !== "Enter" || event.shiftKey) {
      return;
    }

    event.preventDefault();
    submitValue();
  }

  let placeholder = "Ask TARS";

  if (connectionState !== "connected") {
    placeholder = "Waiting for the backend connection.";
  } else if (hasActiveRun) {
    placeholder = "Ask TARS";
  }

  return (
    <div className="input-shell">
      <div className="input-container">
        <textarea
          ref={textareaRef}
          className="input-textarea"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={handleKeyPress}
          placeholder={placeholder}
          disabled={disabled}
        />
        <button
          className="input-button"
          type="button"
          onClick={submitValue}
          disabled={disabled || !canSend}
        >
          Send
        </button>
      </div>
    </div>
  );
}
