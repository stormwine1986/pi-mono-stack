import { Redis } from 'ioredis';
import { config } from '../config.js';
import { logger } from '../logger.js';
import { TelegramSender } from '../telegram/sender.js';

export async function startReminderListener(
    redisProducer: Redis,
    redisReminderConsumer: Redis,
    sender: TelegramSender
) {
    logger.info(`Starting Reminder listener on ${config.reminder_out} (group: ${config.dkronConsumerGroup})...`);

    // Ensure consumer group exists
    try {
        await redisReminderConsumer.xgroup('CREATE', config.reminder_out, config.dkronConsumerGroup, '$', 'MKSTREAM');
        logger.info(`Reminder Consumer group ${config.dkronConsumerGroup} created`);
    } catch (err: any) {
        if (err.message.includes('BUSYGROUP')) {
            // Group already exists
        } else {
            logger.error('Error creating Reminder consumer group:', err);
        }
    }

    while (true) {
        try {
            const result = await (redisReminderConsumer as any).xreadgroup(
                'GROUP', config.dkronConsumerGroup, config.dkronConsumerName,
                'COUNT', 1, 'BLOCK', 0, 'STREAMS', config.reminder_out, '>'
            );

            if (result && result.length > 0) {
                const [streamName, messages] = result[0];
                for (const [id, fields] of messages) {
                    const payloadIndex = fields.indexOf('payload');
                    if (payloadIndex === -1) continue;

                    const rawMessage = fields[payloadIndex + 1];
                    logger.info(`Received Reminder message ${id} from ${streamName}: ${rawMessage}`);

                    try {
                        const msg = JSON.parse(rawMessage);

                        // Notify user via Telegram
                        if (config.adminId) {
                            const message = msg.message || '闹钟响了';
                            const notification = `🔔 **提醒**\n\n${message}`;
                            await sender.sendAdminMessage(config.adminId, notification);
                        }

                    } catch (parseErr) {
                        logger.error('Error parsing Reminder message:', parseErr);
                    }

                    // Acknowledge
                    await redisReminderConsumer.xack(config.reminder_out, config.dkronConsumerGroup, id);
                }
            }
        } catch (error) {
            logger.error('Error processing Reminder result:', error);
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
    }
}
