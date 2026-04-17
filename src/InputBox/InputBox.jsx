import { useState } from 'react';
import './InputBox.css';

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
		</div>
	);
}
