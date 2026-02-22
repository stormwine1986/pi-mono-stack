import { Telegraf } from 'telegraf';
import { Redis } from 'ioredis';
import { nanoid } from 'nanoid';
import { config } from './config.js';
import { WorkerTask, WorkerControlSignal } from './types.js';
import { TelegramSender } from './telegram/sender.js';
import { startResultListener } from './telegram/listener.js';
import { startDkronListener } from './dkron/listener.js';
import { logger } from './logger.js';

const bot = new Telegraf(config.telegramToken);
const sender = new TelegramSender(bot);
const redisProducer = new Redis(config.redisUrl);
const redisConsumer = new Redis(config.redisUrl);
const redisDkronConsumer = new Redis(config.redisUrl);

// Middleware for authorization
bot.use(async (ctx, next) => {
    const userId = ctx.from?.id;
    if (config.adminId && userId && userId !== config.adminId) {
        logger.warn(`Unauthorized access attempt from user ID: ${userId} (${ctx.from?.username})`);
        return;
    }
    return next();
});


// 1. Handle Commands (Control Channel -> WorkerControlSignal via Pub/Sub)
bot.command('stop', async (ctx) => {
    const signal: WorkerControlSignal = { command: 'stop' };
    logger.info(`Publishing control signal to ${config.agent_ctl}: stop`);
    await redisProducer.publish(config.agent_ctl, JSON.stringify(signal));
});

bot.command('new', async (ctx) => {
    const signal: WorkerControlSignal = { command: 'reset' };
    logger.info(`Publishing control signal to ${config.agent_ctl}: reset`);
    await redisProducer.publish(config.agent_ctl, JSON.stringify(signal));
    await ctx.reply('✅ 新会话开始');
});

bot.command('steer', async (ctx) => {
    const message = ctx.message.text.replace(/^\/steer\s*/, '');
    const signal: WorkerControlSignal = {
        command: "steer",
        message: message
    };

    logger.info(`Publishing steer signal to ${config.agent_ctl}: ${message}`);
    await redisProducer.publish(config.agent_ctl, JSON.stringify(signal));
});

// 2. Handle generic messages (Input Queue -> WorkerTask)
bot.on('message', async (ctx) => {
    if ('text' in ctx.message) {
        if (ctx.message.text.startsWith('/')) return;

        const taskId = nanoid();
        const task: WorkerTask = {
            id: taskId,
            source: 'telegram',
            prompt: ctx.message.text,
            metadata: { telegram: `${ctx.chat.id}:${ctx.message.message_id}` }
        };

        logger.info(`Pushing task ${taskId} to ${config.agent_in}: ${task.prompt}`);
        await redisProducer.xadd(config.agent_in, '*', 'payload', JSON.stringify(task));
    }
});


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

        bot.launch();
        logger.info('TG Bot launched successfully');

        startResultListener(bot, sender, redisConsumer);
        startDkronListener(redisProducer, redisDkronConsumer, sender);

        const stop = () => {
            bot.stop();
            redisProducer.disconnect();
            redisConsumer.disconnect();
            redisDkronConsumer.disconnect(); // <--- Disconnect
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
