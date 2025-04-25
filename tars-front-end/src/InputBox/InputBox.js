import { useState } from 'react';
import './InputBox.css';

export default function InputBox(props) {
	const [value, setValue] = useState('');

	function handleKeyPress(e) {
		if (e.key === "Enter" && !e.shiftKey) {
			e.preventDefault();
			props.askOllama(value);
			setValue(""); // Clear the input *after* sending
		}
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
