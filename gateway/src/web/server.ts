import path from 'path';
import { fileURLToPath } from 'url';
import express from 'express';
import cors from 'cors';
import { Redis } from 'ioredis';
import { config } from '../config.js';
import { logger } from '../logger.js';
import { registerRoutes } from './routes.js';
import { registerSSE } from './sse.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export function startWebServer(redisProducer: Redis, redisConsumer: Redis) {
    const app = express();
    app.use(cors());
    app.use(express.json());

    // Serve static frontend files (index.html, style.css, app.js)
    app.use(express.static(path.join(__dirname, 'public')));

    // Mount REST API routes
    registerRoutes(app, redisProducer);

    // Mount SSE endpoint
    registerSSE(app, redisConsumer);

    const port = config.webPort;
    app.listen(port, () => {
        logger.info(`Web UI test server started on port ${port}`);
    });
}
