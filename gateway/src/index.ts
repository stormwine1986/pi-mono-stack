import { Telegraf } from 'telegraf';
import { Redis } from 'ioredis';
import { config } from './config.js';
import { WorkerTask, WorkerControlSignal, WorkerResponse } from './types.js';

const bot = new Telegraf(config.telegramToken);
const redisProducer = new Redis(config.redisUrl);
const redisConsumer = new Redis(config.redisUrl);

function getTimestamp() {
    const now = new Date();
    const pad = (n: number, l = 2) => n.toString().padStart(l, '0');
    return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ` +
        `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}.${pad(now.getMilliseconds(), 3)}`;
}

const logger = {
    info: (msg: string, ...args: any[]) => console.log(`[${getTimestamp()}] [INFO] ${msg}`, ...args),
    warn: (msg: string, ...args: any[]) => console.warn(`[${getTimestamp()}] [WARN] ${msg}`, ...args),
    error: (msg: string, ...args: any[]) => console.error(`[${getTimestamp()}] [ERROR] ${msg}`, ...args),
};

// Middleware for authorization
bot.use(async (ctx, next) => {
    const userId = ctx.from?.id;
    if (config.allowedUserIds.length > 0 && userId && !config.allowedUserIds.includes(userId)) {
        logger.warn(`Unauthorized access attempt from user ID: ${userId} (${ctx.from?.username})`);
        return;
    }
    return next();
});

// Map TG chat_id + message_id to Worker Task ID to handle responses correctly
// For a simple stateless gateway, we can encode TG info into the ID
function generateTaskId(chatId: number, messageId: number): string {
    return `${chatId}:${messageId}`;
}

function parseTaskId(taskId: string): { chatId: number, messageId: number } | null {
    const parts = taskId.split(':');
    if (parts.length === 2) {
        return {
            chatId: parseInt(parts[0] || '0'),
            messageId: parseInt(parts[1] || '0')
        };
    }
    return null;
}

// 1. Handle Commands (Control Channel -> WorkerControlSignal via Pub/Sub)
bot.command('stop', async (ctx) => {
    const taskId = generateTaskId(ctx.chat.id, ctx.message.message_id);
    const signal: WorkerControlSignal = { id: taskId, command: 'stop' };
    logger.info(`Publishing control signal to ${config.agent_ctl}: stop (id: ${taskId})`);
    await redisProducer.publish(config.agent_ctl, JSON.stringify(signal));
});

bot.command('new', async (ctx) => {
    const taskId = generateTaskId(ctx.chat.id, ctx.message.message_id);
    const signal: WorkerControlSignal = { id: taskId, command: 'reset' };
    logger.info(`Publishing control signal to ${config.agent_ctl}: reset (from /new, id: ${taskId})`);
    await redisProducer.publish(config.agent_ctl, JSON.stringify(signal));
    await ctx.reply('✅ 新会话开始');
});

bot.command('steer', async (ctx) => {
    const taskId = generateTaskId(ctx.chat.id, ctx.message.message_id);
    const message = ctx.message.text.replace(/^\/steer\s*/, '');
    const signal: WorkerControlSignal = {
        id: taskId,
        command: "steer",
        message: message
    };

    logger.info(`Publishing steer signal to ${config.agent_ctl}: ${message} (id: ${taskId})`);
    await redisProducer.publish(config.agent_ctl, JSON.stringify(signal));
});

// 2. Handle generic messages (Input Queue -> WorkerTask)
bot.on('message', async (ctx) => {
    if ('text' in ctx.message) {
        if (ctx.message.text.startsWith('/')) return;

        const taskId = generateTaskId(ctx.chat.id, ctx.message.message_id);
        const task: WorkerTask = {
            id: taskId,
            source: 'telegram',
            prompt: ctx.message.text
        };

        logger.info(`Pushing task to ${config.agent_in}: ${task.prompt}`);
        // Use XADD for Redis Stream
        await redisProducer.xadd(config.agent_in, '*', 'payload', JSON.stringify(task));
    }
});

// 3. Listen to Redis results queue (Output Queue -> WorkerResponse)
async function startResultListener() {
    logger.info(`Starting result listener on ${config.agent_out} (group: ${config.tgConsumerGroup}, consumer: ${config.tgConsumerName})...`);

    // Ensure consumer group exists
    try {
        await redisConsumer.xgroup('CREATE', config.agent_out, config.tgConsumerGroup, '$', 'MKSTREAM');
        logger.info(`Consumer group ${config.tgConsumerGroup} created`);
    } catch (err: any) {
        if (err.message.includes('BUSYGROUP')) {
            // Group already exists
        } else {
            logger.error('Error creating consumer group:', err);
        }
    }

    while (true) {
        try {
            // Use XREADGROUP for Redis Stream
            // ioredis xreadgroup returns: [ [streamName, [ [id, [field, value, ...]] ]] ]
            const result = await (redisConsumer as any).xreadgroup(
                'GROUP', config.tgConsumerGroup, config.tgConsumerName,
                'COUNT', 1, 'BLOCK', 0, 'STREAMS', config.agent_out, '>'
            );

            if (result && result.length > 0) {
                const [streamName, messages] = result[0];
                for (const [id, fields] of messages) {
                    // fields is [ 'payload', '{"id":...}' ]
                    const dataIndex = fields.indexOf('payload');
                    if (dataIndex === -1) continue;

                    const rawMessage = fields[dataIndex + 1];
                    logger.info(`Received message ${id} from ${streamName}: ${rawMessage}`);

                    const response = JSON.parse(rawMessage) as WorkerResponse;

                    if (response.id) {
                        const tgInfo = parseTaskId(response.id);
                        if (tgInfo) {
                            if (response.status === 'success') {
                                await bot.telegram.sendMessage(tgInfo.chatId, response.response, {
                                    reply_parameters: { message_id: tgInfo.messageId },
                                });
                            } else if (response.status === 'error') {
                                await bot.telegram.sendMessage(tgInfo.chatId, `❌ Error: ${response.error}`, {
                                    reply_parameters: { message_id: tgInfo.messageId },
                                });
                            } else if (response.status === 'progress') {
                                await bot.telegram.sendChatAction(tgInfo.chatId, 'typing');
                                logger.info(`Progress: ${response.event} for taskId ${response.id}`);
                            }
                        }
                    }

                    // Acknowledge the message
                    await redisConsumer.xack(config.agent_out, config.tgConsumerGroup, id);
                }
            }
        } catch (error) {
            logger.error('Error processing result:', error);
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
    }
}

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

        startResultListener();

        const stop = () => {
            bot.stop();
            redisProducer.disconnect();
            redisConsumer.disconnect();
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
