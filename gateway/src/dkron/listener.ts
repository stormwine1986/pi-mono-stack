import { Redis } from 'ioredis';
import { config } from '../config.js';
import { logger } from '../logger.js';
import { TelegramSender } from '../telegram/sender.js';

export async function startDkronListener(
    redisProducer: Redis,
    redisDkronConsumer: Redis,
    sender: TelegramSender
) {
    logger.info(`Starting Background listener on ${config.background_out} (group: ${config.dkronConsumerGroup})...`);

    // Ensure consumer group exists
    try {
        await redisDkronConsumer.xgroup('CREATE', config.background_out, config.dkronConsumerGroup, '$', 'MKSTREAM');
        logger.info(`Background Consumer group ${config.dkronConsumerGroup} created`);
    } catch (err: any) {
        if (err.message.includes('BUSYGROUP')) {
            // Group already exists
        } else {
            logger.error('Error creating Background consumer group:', err);
        }
    }

    while (true) {
        try {
            const result = await (redisDkronConsumer as any).xreadgroup(
                'GROUP', config.dkronConsumerGroup, config.dkronConsumerName,
                'COUNT', 1, 'BLOCK', 0, 'STREAMS', config.background_out, '>'
            );

            if (result && result.length > 0) {
                const [streamName, messages] = result[0];
                for (const [id, fields] of messages) {
                    const payloadIndex = fields.indexOf('payload');
                    if (payloadIndex === -1) continue;

                    const rawMessage = fields[payloadIndex + 1];
                    logger.info(`Received Background message ${id} from ${streamName}: ${rawMessage}`);

                    try {
                        const msg = JSON.parse(rawMessage);

                        // Notify user via Telegram
                        if (config.adminId) {
                            const jobName = msg.job || 'Unknown';
                            const exitCode = msg.exit_code;
                            const status = exitCode === 0 ? '✅ 成功' : `❌ 失败 (exit_code=${exitCode})`;
                            const notification = `后台任务 \`${jobName}\` ${status}`;
                            await sender.sendAdminMessage(config.adminId, notification);
                        }

                    } catch (parseErr) {
                        logger.error('Error parsing Background message:', parseErr);
                    }

                    // Acknowledge
                    await redisDkronConsumer.xack(config.background_out, config.dkronConsumerGroup, id);
                }
            }
        } catch (error) {
            logger.error('Error processing Background result:', error);
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
    }
}
