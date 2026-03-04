import { Express } from 'express';
import { Redis } from 'ioredis';
import { config } from '../config.js';
import { logger } from '../logger.js';

export function registerSSE(app: Express, redisConsumer: Redis) {
    app.get('/api/events', (req, res) => {
        res.setHeader('Content-Type', 'text/event-stream');
        res.setHeader('Cache-Control', 'no-cache');
        res.setHeader('Connection', 'keep-alive');
        res.flushHeaders();

        logger.info('[WebUI] New SSE client connected');

        const sendEvent = (data: any) => {
            res.write(`data: ${JSON.stringify(data)}\n\n`);
        };

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
}
