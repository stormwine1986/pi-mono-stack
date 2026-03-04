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
        * { box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; max-width: 1600px; margin: 0 auto; padding: 15px; background: #f4f7f6; height: 100vh; overflow: hidden; }
        
        .container { display: flex; flex-direction: column; height: 100%; }
        h2 { margin: 0 0 15px 0; display: flex; align-items: center; flex-shrink: 0; }
        
        .layout { display: grid; grid-template-columns: 1fr 350px; gap: 20px; flex-grow: 1; min-height: 0; }
        
        .chat-column { display: flex; flex-direction: column; min-height: 0; flex-grow: 1; }
        
        #messages { flex-grow: 1; overflow-y: auto; border: 1px solid #ddd; padding: 15px; background: white; margin-bottom: 15px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        
        /* Custom Scrollbar */
        #messages::-webkit-scrollbar, #memory-events::-webkit-scrollbar { width: 8px; }
        #messages::-webkit-scrollbar-track, #memory-events::-webkit-scrollbar-track { background: #f1f1f1; border-radius: 4px; }
        #messages::-webkit-scrollbar-thumb, #memory-events::-webkit-scrollbar-thumb { background: #ccc; border-radius: 4px; }
        #messages::-webkit-scrollbar-thumb:hover, #memory-events::-webkit-scrollbar-thumb:hover { background: #bbb; }

        .message { margin-bottom: 12px; padding: 12px; border-radius: 8px; max-width: 85%; width: fit-content; }
        .message.sent { background: #e3f2fd; border-right: 4px solid #2196f3; margin-left: auto; }
        .message.received { background: #f5f5f5; border-left: 4px solid #4caf50; }
        .message.error { background: #ffebee; border-left: 4px solid #f44336; }
        .message.progress { background: #fffde7; font-size: 0.9em; color: #666; font-style: italic; width: 100%; max-width: 100%; }
        
        .input-area { display: flex; gap: 10px; flex-shrink: 0; padding-bottom: 5px; }
        input { padding: 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 16px; outline: none; transition: border-color 0.2s; }
        #prompt { flex-grow: 1; }
        #user-id { width: 150px; flex-shrink: 0; }
        input:focus { border-color: #2196f3; }
        button { padding: 10px 24px; background: #2196f3; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; transition: background 0.2s; flex-shrink: 0; }
        button:hover { background: #1976d2; }
        pre { white-space: pre-wrap; margin: 0; font-family: inherit; font-size: 15px; line-height: 1.5; word-break: break-all; }
        
        .status-dot { display: inline-block; width: 12px; height: 12px; border-radius: 50%; margin-right: 10px; }
        .status-online { background: #4caf50; box-shadow: 0 0 8px #4caf50; }
        .status-offline { background: #f44336; }
        
        /* Memory Events Sidebar */
        #memory-sidebar { display: flex; flex-direction: column; min-height: 0; }
        #memory-events { flex-grow: 1; border: 1px solid #ddd; padding: 12px; background: #fff; border-radius: 8px; overflow-y: auto; font-size: 0.85em; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        .mem-event { padding: 10px; border-bottom: 1px solid #eee; margin-bottom: 8px; border-left: 4px solid #673ab7; background: #f3e5f5; border-radius: 6px; }
        .mem-event.ADD { border-left-color: #4caf50; background: #e8f5e9; }
        .mem-event.DELETE { border-left-color: #f44336; background: #ffebee; }
        .mem-event.UPDATE { border-left-color: #ff9800; background: #fff3e0; }
        .mem-time { font-size: 0.8em; color: #888; display: block; margin-bottom: 4px; }
        .mem-fact { font-weight: 500; display: block; margin-top: 3px; color: #333; line-height: 1.4; }
        .mem-user { font-weight: bold; color: #673ab7; }
        h3 { margin-top: 0; border-bottom: 2px solid #eee; padding-bottom: 10px; color: #333; font-size: 1.1em; flex-shrink: 0; }
    </style>
</head>
<body>
    <div class="container">
        <h2><span id="status-dot" class="status-dot status-offline"></span>Agent Gateway Test UI</h2>
        
        <div class="layout">
            <div class="chat-column">
                <div id="messages"></div>
                <div class="input-area">
                    <input type="text" id="user-id" placeholder="User ID" onchange="localStorage.setItem('gate_user_id', this.value)">
                    <input type="text" id="prompt" placeholder="Type a message to agent_in..." onkeypress="if(event.key === 'Enter') send()">
                    <button onclick="send()" id="send-btn">Send</button>
                </div>
            </div>
            
            <div id="memory-sidebar">
                <h3>Latest Memory Events</h3>
                <div id="memory-events"></div>
            </div>
        </div>
    </div>

    <script>
        const messagesDiv = document.getElementById('messages');
        const memoryDiv = document.getElementById('memory-events');
        const promptInput = document.getElementById('prompt');
        const userIdInput = document.getElementById('user-id');
        const statusDot = document.getElementById('status-dot');

        // Load persisted User ID
        userIdInput.value = localStorage.getItem('gate_user_id') || 'test-user';

        function appendMemoryEvent(event) {
            const div = document.createElement('div');
            div.className = 'mem-event ' + event.event;
            
            const time = new Date(event.timestamp).toLocaleTimeString();
            div.innerHTML = \`
                <span class="mem-time">\${time} · <span class="mem-user">\${event.user_id}</span></span>
                <span class="mem-fact">\${event.fact}</span>
                <small style="color: #666; font-size: 0.8em">\${event.event} | ID: \${event.memory_id.substring(0,8)}</small>
            \`;
            
            memoryDiv.insertBefore(div, memoryDiv.firstChild);
            
            // Keep only latest 10
            while (memoryDiv.children.length > 10) {
                memoryDiv.removeChild(memoryDiv.lastChild);
            }
        }

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
            const user_id = userIdInput.value.trim() || 'test-user';
            if (!prompt) return;

            appendMessage('[' + user_id + '] To agent_in: ' + prompt, 'sent');
            promptInput.value = '';

            try {
                const res = await fetch('/api/send', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt, user_id })
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
                } else if (data.event && ['ADD', 'UPDATE', 'DELETE'].includes(data.event)) {
                    appendMemoryEvent(data);
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
            let lastIdAgent = '$';
            let lastIdMem = '$';
            while (active) {
                try {
                    const results = await (redisConsumer as any).xread(
                        'BLOCK', 5000,
                        'COUNT', 10,
                        'STREAMS', config.agent_out, config.memory_audit,
                        lastIdAgent, lastIdMem
                    );
                    if (results) {
                        for (const [stream, messages] of results) {
                            for (const [id, fields] of messages) {
                                if (stream === config.agent_out) lastIdAgent = id;
                                if (stream === config.memory_audit) lastIdMem = id;

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
