import { Telegraf } from 'telegraf';
import { Redis } from 'ioredis';
import { WorkerResponse } from '../types.js';
import { config } from '../config.js';
import { logger } from '../logger.js';
import { TelegramSender } from './sender.js';

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
            const result = await (redisConsumer as any).xreadgroup(
                'GROUP', config.tgConsumerGroup, config.tgConsumerName,
                'COUNT', 1, 'BLOCK', 0, 'STREAMS', config.agent_out, '>'
            );

            if (result && result.length > 0) {
                const [streamName, messages] = result[0];
                for (const [id, fields] of messages) {
                    const dataIndex = fields.indexOf('payload');
                    if (dataIndex === -1) continue;

                    const rawMessage = fields[dataIndex + 1];
                    logger.info(`Received message ${id} from ${streamName}: ${rawMessage}`);

                    const response = JSON.parse(rawMessage) as WorkerResponse;

                    if (response.status === 'success' || response.status === 'error') {
                        await sender.sendAdminMessage(adminId,
                            response.status === 'success' ? response.response : response.error
                        );
                    } else if (response.status === 'progress') {
                        await bot.telegram.sendChatAction(adminId, 'typing');
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
