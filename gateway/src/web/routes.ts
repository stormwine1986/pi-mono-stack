import { Express } from 'express';
import { Redis } from 'ioredis';
import { config } from '../config.js';
import { logger } from '../logger.js';
import { WorkerTask } from '../types.js';
import { nanoid } from 'nanoid';

export function registerRoutes(app: Express, redisProducer: Redis) {
    // Send message to agent_in
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

    // Get Telegram Enable Status
    app.get('/api/tg-status', async (req, res) => {
        try {
            const val = await redisProducer.get(config.tgEnabledKey);
            res.json({ enabled: val !== '0' && val !== 'false' });
        } catch (err) {
            res.status(500).json({ error: 'Redis error' });
        }
    });

    // Toggle Telegram Enable Status
    app.post('/api/tg-toggle', async (req, res) => {
        const { enabled } = req.body;
        try {
            await redisProducer.set(config.tgEnabledKey, enabled ? '1' : '0');
            logger.info(`[WebUI] Telegram Bot ${enabled ? 'ENABLED' : 'DISABLED'} via WebUI`);
            res.json({ status: 'ok' });
        } catch (err) {
            res.status(500).json({ error: 'Redis error' });
        }
    });

    // Get Dkron Jobs (proxy to Dkron API)
    app.get('/api/jobs', async (req, res) => {
        try {
            const response = await fetch(`${config.dkronUrl}/jobs`);
            if (!response.ok) throw new Error(`Dkron error: ${response.status}`);
            const data = await response.json();
            res.json(data);
        } catch (err) {
            logger.error(`[WebUI] Failed to fetch jobs from Dkron: ${err}`);
            res.status(500).json({ error: 'Failed to fetch from Dkron' });
        }
    });

    // Reset session via agent_ctl
    app.post('/api/reset', async (req, res) => {
        const { user_id } = req.body;
        const taskId = nanoid();
        const signal = {
            id: taskId,
            user_id: user_id || 'web-test-user',
            source: 'web',
            command: 'reset'
        };

        try {
            await redisProducer.publish(config.agent_ctl, JSON.stringify(signal));
            logger.info(`[WebUI] Published reset signal ${taskId} for user ${user_id} to ${config.agent_ctl}`);
            res.json({ status: 'ok' });
        } catch (err) {
            logger.error(`[WebUI] Failed to push reset signal: ${err}`);
            res.status(500).json({ error: 'Failed to push to Redis' });
        }
    });

    // Get Summary History
    app.get('/api/summaries', async (req, res) => {
        try {
            // Get last 20 messages from summary_out
            const results = await redisProducer.xrevrange(config.summary_out, '+', '-', 'COUNT', 20);
            const summaries = results.map(([id, fields]) => {
                const payloadIndex = fields.indexOf('payload');
                if (payloadIndex !== -1) {
                    try {
                        return { id, ...JSON.parse(fields[payloadIndex + 1]) };
                    } catch (e) {
                        return null;
                    }
                }
                return null;
            }).filter(s => s !== null);
            res.json(summaries);
        } catch (err) {
            logger.error(`[WebUI] Failed to fetch summaries: ${err}`);
            res.status(500).json({ error: 'Failed to fetch from Redis' });
        }
    });
}
