import { Telegraf } from 'telegraf';
import { Redis } from 'ioredis';
import { config } from './config.js';
import { TelegramSender } from './telegram/sender.js';
import { startResultListener } from './telegram/listener.js';
import { startDkronListener } from './dkron/listener.js';
import { startReminderListener } from './dkron/reminder.js';
import { setupRecoveryJob } from './dkron/setup.js';
import { registerHandlers } from './telegram/handlers.js';
import { logger } from './logger.js';

const bot = new Telegraf(config.telegramToken);
const sender = new TelegramSender(bot);
const redisProducer = new Redis(config.redisUrl);
const redisConsumer = new Redis(config.redisUrl);
const redisDkronConsumer = new Redis(config.redisUrl);
const redisReminderConsumer = new Redis(config.redisUrl);

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
            dropPendingUpdates: true
        });
        logger.info('TG Bot launched successfully');

        startResultListener(bot, sender, redisConsumer);
        startDkronListener(redisProducer, redisDkronConsumer, sender);
        startReminderListener(redisProducer, redisReminderConsumer, sender);

        // Setup Dkron jobs
        setupRecoveryJob();

        const stop = () => {
            bot.stop();
            redisProducer.disconnect();
            redisConsumer.disconnect();
            redisDkronConsumer.disconnect();
            redisReminderConsumer.disconnect();
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
