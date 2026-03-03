import dns from 'node:dns';
import { Agent } from 'node:https';
import { Telegraf } from 'telegraf';

// Force DNS resolution to prioritize IPv4 (fixes issues where IPv6 is broken or slow)
dns.setDefaultResultOrder('ipv4first');

import { Redis } from 'ioredis';
import { config } from './config.js';
import { TelegramSender } from './telegram/sender.js';
import { startResultListener } from './telegram/listener.js';
import { startReminderListener } from './dkron/reminder.js';
import { startSummaryListener } from './summary.js';
import { setupAllJobs } from './dkron/setup.js';
import { registerHandlers } from './telegram/handlers.js';
import { logger } from './logger.js';

const bot = new Telegraf(config.telegramToken, {
    telegram: {
        agent: new Agent({ family: 4 })
    }
});
const sender = new TelegramSender(bot);
const redisProducer = new Redis(config.redisUrl);
const redisConsumer = new Redis(config.redisUrl);
const redisReminderConsumer = new Redis(config.redisUrl);
const redisSummaryConsumer = new Redis(config.redisUrl);

// Register Event Handlers
registerHandlers(bot, redisProducer);



// Start everything
async function main() {
    if (!config.telegramToken) {
        logger.error('TELEGRAM_TOKEN is not set in environment variables');
        process.exit(1);
    }

    try {
        // Register commands with Telegram
        await bot.telegram.setMyCommands([
            { command: 'new', description: '新建会话' },
            { command: 'stop', description: '终止任务' },
            { command: 'steer', description: '提供指引' },
        ]);
        logger.info('TG Bot commands registered');

        bot.launch({
            allowedUpdates: ['message', 'callback_query', 'photo'] as any,
            dropPendingUpdates: false
        });
        logger.info('TG Bot launched successfully');

        startResultListener(bot, sender, redisConsumer);
        startReminderListener(redisProducer, redisReminderConsumer, sender);
        startSummaryListener(redisSummaryConsumer, sender);

        // Setup Dkron jobs
        setupAllJobs();

        const stop = () => {
            bot.stop();
            redisProducer.disconnect();
            redisConsumer.disconnect();
            redisReminderConsumer.disconnect();
            redisSummaryConsumer.disconnect();
            process.exit(0);
        };
        process.once('SIGINT', stop);
        process.once('SIGTERM', stop);
    } catch (err) {
        logger.error('Failed to start gateway bot:', err);
        process.exit(1);
    }
}

main();
