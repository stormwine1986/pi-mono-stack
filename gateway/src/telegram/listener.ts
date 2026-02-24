import { Telegraf } from 'telegraf';
import { Redis } from 'ioredis';
import { WorkerResponse } from '../types.js';
import { config } from '../config.js';
import { logger } from '../logger.js';
import { TelegramSender } from './sender.js';

const BLOCK_TIMEOUT_MS = 5000;       // Don't block forever; poll every 5s
const PENDING_CLAIM_INTERVAL = 30;   // Reclaim pending messages every N iterations
const PENDING_IDLE_MS = 60_000;      // Claim messages idle for > 60s

export async function startResultListener(
    bot: Telegraf,
    sender: TelegramSender,
    redisConsumer: Redis
) {
    const adminId = config.adminId;
    if (!adminId) {
        logger.error('TG_ADMIN_ID not configured, result listener disabled');
        return;
    }

    const stream = config.agent_out;
    const group = config.tgConsumerGroup;
    const consumer = config.tgConsumerName;

    logger.info(`Starting result listener on ${stream} (group: ${group}, consumer: ${consumer})...`);

    // Ensure consumer group exists
    try {
        await redisConsumer.xgroup('CREATE', stream, group, '$', 'MKSTREAM');
        logger.info(`Consumer group ${group} created`);
    } catch (err: any) {
        if (err.message.includes('BUSYGROUP')) {
            // Group already exists — expected on restart
        } else {
            logger.error('Error creating consumer group:', err);
        }
    }

    // Phase 1: Process any pending messages from previous runs
    await processPendingMessages(redisConsumer, bot, sender, adminId, stream, group, consumer);

    // Phase 2: Main loop — read new messages + periodic pending reclaim
    let iteration = 0;
    while (true) {
        try {
            // Periodically reclaim stale pending messages
            if (++iteration % PENDING_CLAIM_INTERVAL === 0) {
                await processPendingMessages(redisConsumer, bot, sender, adminId, stream, group, consumer);
            }

            const result = await (redisConsumer as any).xreadgroup(
                'GROUP', group, consumer,
                'COUNT', 10, 'BLOCK', BLOCK_TIMEOUT_MS, 'STREAMS', stream, '>'
            );

            if (result && result.length > 0) {
                const [, messages] = result[0];
                for (const [id, fields] of messages) {
                    await processMessage(id, fields, redisConsumer, bot, sender, adminId, stream, group);
                }
            }
        } catch (error) {
            logger.error('Error in result listener loop:', error);
            await new Promise(resolve => setTimeout(resolve, 2000));
        }
    }
}

/**
 * Process pending messages that were delivered but never ACK'd (e.g. after a crash/restart).
 * Uses XREADGROUP with id "0" to fetch pending messages for this consumer.
 */
async function processPendingMessages(
    redis: Redis, bot: Telegraf, sender: TelegramSender,
    adminId: number, stream: string, group: string, consumer: string
) {
    try {
        const result = await (redis as any).xreadgroup(
            'GROUP', group, consumer,
            'COUNT', 50, 'STREAMS', stream, '0'
        );

        if (!result || result.length === 0) return;

        const [, messages] = result[0];
        if (!messages || messages.length === 0) {
            logger.info('No pending messages to recover.');
            return;
        }

        logger.info(`Recovering ${messages.length} pending message(s)...`);
        for (const [id, fields] of messages) {
            await processMessage(id, fields, redis, bot, sender, adminId, stream, group);
        }
    } catch (err) {
        logger.error('Error processing pending messages:', err);
    }
}

/**
 * Race a promise against a timeout. Prevents Telegram API calls from hanging forever.
 */
function withTimeout<T>(promise: Promise<T>, ms: number, label: string): Promise<T> {
    return Promise.race([
        promise,
        new Promise<T>((_, reject) =>
            setTimeout(() => reject(new Error(`Timeout: ${label} exceeded ${ms}ms`)), ms)
        )
    ]);
}

const TG_API_TIMEOUT = 5_000; // 5s timeout for Telegram API calls

/**
 * Process a single message: ACK first (at-most-once), then dispatch to Telegram.
 * This prevents a failed Telegram API call from permanently blocking the consumer.
 */
async function processMessage(
    id: string, fields: string[],
    redis: Redis, bot: Telegraf, sender: TelegramSender,
    adminId: number, stream: string, group: string
) {
    // ACK immediately to prevent re-delivery blocking
    await redis.xack(stream, group, id);

    const dataIndex = fields.indexOf('payload');
    if (dataIndex === -1) return;

    const rawMessage = fields[dataIndex + 1];
    logger.info(`Processing message ${id}: ${rawMessage}`);

    try {
        const response = JSON.parse(rawMessage) as WorkerResponse;

        if (response.status === 'success' || response.status === 'error') {
            await withTimeout(
                sender.sendAdminMessage(adminId,
                    response.status === 'success' ? response.response : response.error
                ),
                TG_API_TIMEOUT, 'sendAdminMessage'
            );

            // Send attached images if present
            if (response.status === 'success' && response.images?.length) {
                for (const imagePath of response.images) {
                    await withTimeout(
                        sender.sendAdminPhoto(adminId, imagePath),
                        TG_API_TIMEOUT, 'sendAdminPhoto'
                    );
                }
            }
        } else if (response.status === 'progress') {
            if (response.event === 'send_media' && response.data?.path) {
                await withTimeout(
                    sender.sendAdminPhoto(adminId, response.data.path),
                    TG_API_TIMEOUT, 'sendAdminPhoto'
                );
            } else {
                // Fire-and-forget: typing indicator is non-critical, never block the loop
                bot.telegram.sendChatAction(adminId, 'typing').catch(() => { });
            }
        }
    } catch (err) {
        logger.error(`Failed to process message ${id}:`, err);
        // Message already ACK'd — log and move on, don't block the loop
    }
}
