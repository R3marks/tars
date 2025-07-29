import { core } from '@tauri-apps/api';
import { useState, useEffect, useCallback } from 'react';
import './InputBox.css';
import { debounce } from 'lodash'; // Install lodash if not yet

export default function InputBox(props) {
	const [value, setValue] = useState('');

	function handleChange(e) {
		setValue(e.target.value);
	}

	function handleKeyPress(e) {
		if (e.key === "Enter" && !e.shiftKey) {
			e.preventDefault();
			props.askOllama(value);
			setValue("");
		}
	}

	function takeScreenshot() {
		print(core)
		// core.invoke('capture_screenshot')
		core.invoke("screenshot")
			.then((path) => {
				console.log("Screenshot saved to: ", path);
				// Optionally, trigger an API call with this image path.
			})
			.catch((err) => {
				console.error("Screenshot failed", err);
			});
	}

	return (
		<div className="input-container">
			<textarea
				className="input-textarea"
				value={value}
				onChange={handleChange}
				onKeyDown={(e) => handleKeyPress(e)}
				placeholder="Chat"
			/>
			<button
				className="input-button"
				type="submit"
				onClick={() => props.askOllama(value)}>
				Submit
			</button>
			<button 
				className="screenshot-button" 
				onClick={() => props.showTars(value)}>📸 Screenshot
			</button>
		</div>
	);
}
