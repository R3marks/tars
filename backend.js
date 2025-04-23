const http = require('http');
const fs = require('fs');

let model = 'qwen2.5-coder:3b';
let messages = [{'role': 'user', 'content': ''}];

const chatStream = (req, res) => {
    req.on('data', (chunk) => {
        const data = JSON.parse(chunk);
        messages.push(data.message);
        
        const stream = chat({
            model,
            messages,
            stream: true
        });

        stream.on('message', (msg) => {
            console.log(msg.content); // Simulate logging to the console for demonstration purposes

            res.write(JSON.stringify({ message: msg.content }));
        });

        stream.on('end', () => {
            res.end();
        });
    });
};

http.createServer((req, res) => {
    if (req.url === '/chat-stream') {
        chatStream(req, res);
    } else {
        fs.readFile('./index.html', 'utf-8', (err, data) => {
            if (err) throw err;
            res.writeHead(200, { 'Content-Type': 'text/html' });
            res.end(data);
        });
    }
}).listen(3000, () => {
    console.log('Server is running on http://localhost:3000');
});
