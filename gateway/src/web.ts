import express from 'express';
import cors from 'cors';
import { Redis } from 'ioredis';
import { config } from './config.js';
import { logger } from './logger.js';
import { WorkerTask } from './types.js';
import { nanoid } from 'nanoid';
import { IncomingMessage, ServerResponse } from 'http';

export function startWebServer(redisProducer: Redis, redisConsumer: Redis) {
    const app = express();
    app.use(cors());
    app.use(express.json());

    // Serve a simple test UI
    app.get('/', (req, res) => {
        res.send(`
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agent Gateway Test UI</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f4f7f6; }
        .container { display: flex; flex-direction: column; height: 90vh; }
        #messages { flex-grow: 1; overflow-y: auto; border: 1px solid #ddd; padding: 10px; background: white; margin-bottom: 10px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        .message { margin-bottom: 10px; padding: 10px; border-radius: 6px; }
        .message.sent { background: #e3f2fd; align-self: flex-end; border-left: 4px solid #2196f3; }
        .message.received { background: #f5f5f5; border-left: 4px solid #4caf50; }
        .message.error { background: #ffebee; border-left: 4px solid #f44336; }
        .message.progress { background: #fffde7; font-size: 0.9em; color: #666; font-style: italic; }
        .input-area { display: flex; gap: 10px; }
        input { flex-grow: 1; padding: 12px; border: 1px solid #ddd; border-radius: 4px; font-size: 16px; }
        button { padding: 10px 20px; background: #2196f3; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }
        button:hover { background: #1976d2; }
        pre { white-space: pre-wrap; margin: 0; }
        .status-dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 5px; }
        .status-online { background: #4caf50; }
        .status-offline { background: #f44336; }
    </style>
</head>
<body>
    <div class="container">
        <h2><span id="status-dot" class="status-dot status-offline"></span>Agent Gateway Test UI</h2>
        <div id="messages"></div>
        <div class="input-area">
            <input type="text" id="prompt" placeholder="Type a message to agent_in..." onkeypress="if(event.key === 'Enter') send()">
            <button onclick="send()" id="send-btn">Send</button>
        </div>
    </div>

    <script>
        const messagesDiv = document.getElementById('messages');
        const promptInput = document.getElementById('prompt');
        const statusDot = document.getElementById('status-dot');

        function appendMessage(text, type, data = null) {
            const div = document.createElement('div');
            div.className = 'message ' + type;
            const content = document.createElement('pre');
            content.textContent = text;
            div.appendChild(content);
            
            if (data && data.images && data.images.length > 0) {
                data.images.forEach(img => {
                    const imgEl = document.createElement('img');
                    imgEl.src = img; // This might need a proxy or mapping if they are in workspace
                    imgEl.style.maxWidth = '200px';
                    imgEl.style.display = 'block';
                    imgEl.style.marginTop = '10px';
                    div.appendChild(imgEl);
                });
            }
            
            messagesDiv.appendChild(div);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        async function send() {
            const prompt = promptInput.value.trim();
            if (!prompt) return;

            appendMessage('To agent_in: ' + prompt, 'sent');
            promptInput.value = '';

            try {
                const res = await fetch('/api/send', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt, user_id: 'test-user' })
                });
                if (!res.ok) throw new Error('Failed to send');
            } catch (err) {
                appendMessage('Error: ' + err.message, 'error');
            }
        }

        function connect() {
            const eventSource = new EventSource('/api/events');
            
            eventSource.onopen = () => {
                statusDot.className = 'status-dot status-online';
                console.log('SSE Connected');
            };

            eventSource.onmessage = (event) => {
                const data = JSON.parse(event.data);
                console.log('Received:', data);
                
                if (data.status === 'success') {
                    appendMessage('From agent_out: ' + data.response, 'received', data);
                } else if (data.status === 'error') {
                    appendMessage('Error from agent_out: ' + data.error, 'error');
                } else if (data.status === 'progress') {
                    appendMessage('Progress: ' + data.event + (data.data ? ' ' + JSON.stringify(data.data) : ''), 'progress');
                }
            };

            eventSource.onerror = (err) => {
                statusDot.className = 'status-dot status-offline';
                console.error('SSE Error:', err);
                eventSource.close();
                setTimeout(connect, 3000);
            };
        }

        connect();
    </script>
</body>
</html>
        `);
    });

    // API: Send message to agent_in
    app.post('/api/send', async (req, res) => {
        const { prompt, user_id } = req.body;
        if (!prompt) {
            return res.status(400).json({ error: 'Prompt is required' });
        }

        const taskId = nanoid();
        const task: WorkerTask = {
            id: taskId,
            user_id: user_id || 'web-test-user',
            source: 'web',
            prompt: prompt,
            timestamp: Date.now()
        };

        try {
            await (redisProducer as any).xadd(config.agent_in, 'MAXLEN', '~', 1000, '*', 'payload', JSON.stringify(task));
            logger.info(`[WebUI] Pushed task ${taskId} to ${config.agent_in}`);
            res.json({ status: 'ok', taskId });
        } catch (err) {
            logger.error(`[WebUI] Failed to push task: ${err}`);
            res.status(500).json({ error: 'Failed to push to Redis' });
        }
    });

    // API: SSE for agent_out events
    app.get('/api/events', (req, res) => {
        res.setHeader('Content-Type', 'text/event-stream');
        res.setHeader('Cache-Control', 'no-cache');
        res.setHeader('Connection', 'keep-alive');
        res.flushHeaders();

        logger.info('[WebUI] New SSE client connected');

        const sendEvent = (data: any) => {
            res.write(`data: ${JSON.stringify(data)}\n\n`);
        };

        // We use a dedicated reader loop for this client or a shared one?
        // For a test UI, a dedicated reader starting from '$' (now) is easiest.
        let active = true;
        const reader = async () => {
            let lastId = '$';
            while (active) {
                try {
                    const results = await (redisConsumer as any).xread('BLOCK', 5000, 'COUNT', 10, 'STREAMS', config.agent_out, lastId);
                    if (results) {
                        for (const [stream, messages] of results) {
                            for (const [id, fields] of messages) {
                                lastId = id;
                                const dataIndex = fields.indexOf('payload');
                                if (dataIndex !== -1) {
                                    try {
                                        const payload = JSON.parse(fields[dataIndex + 1]);
                                        sendEvent(payload);
                                    } catch (e) {
                                        logger.error(`[WebUI] Failed to parse payload: ${e}`);
                                    }
                                }
                            }
                        }
                    }
                } catch (err) {
                    if (active) {
                        logger.error(`[WebUI] SSE reader error: ${err}`);
                        await new Promise(r => setTimeout(r, 1000));
                    }
                }
            }
        };

        reader();

        req.on('close', () => {
            active = false;
            logger.info('[WebUI] SSE client disconnected');
        });
    });

    const port = config.webPort;
    app.listen(port, () => {
        logger.info(`Web UI test server started on port ${port}`);
    });
}
