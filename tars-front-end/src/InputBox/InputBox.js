import { useState } from 'react';
import './InputBox.css';

export default function InputBox(props) {
  const [value, setValue] = useState('');

  function handleKeyPress(e) {
    if (e.key === "Enter") {
      console.log(e);
      setValue("");
      e.preventDefault();
      props.askOllama(value);
    }
    // console.log(e);
    // e.target.style.height = 'inherit';
    // Get the computed styles for the element
    // const computed = window.getComputedStyle(e.target);

    // Calculate the height
    // const height = e.target.scrollHeight

    // e.target.style.height = `${height}px`;
  }

  return (
    <div className="input-container">
      <textarea
        className="input-textarea"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => handleKeyPress(e)}
        placeholder="Chat"
        // role="textbox"
      />
      <button
      className="input-button"
      type="submit" 
      onClick={() => props.askOllama(value)}>
        Submit
      </button>
    </div>
  );
}
