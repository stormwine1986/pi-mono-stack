import { Redis } from 'ioredis';
import { nanoid } from 'nanoid';
import { WorkerTask } from '../types.js';
import { config } from '../config.js';
import { logger } from '../logger.js';
import { TelegramSender } from '../telegram/sender.js';

export async function startDkronListener(
    redisProducer: Redis,
    redisDkronConsumer: Redis,
    sender: TelegramSender
) {
    logger.info(`Starting Process listener on ${config.process_out} (group: ${config.dkronConsumerGroup})...`);

    // Ensure consumer group exists
    try {
        await redisDkronConsumer.xgroup('CREATE', config.process_out, config.dkronConsumerGroup, '$', 'MKSTREAM');
        logger.info(`Process Consumer group ${config.dkronConsumerGroup} created`);
    } catch (err: any) {
        if (err.message.includes('BUSYGROUP')) {
            // Group already exists
        } else {
            logger.error('Error creating Process consumer group:', err);
        }
    }

    while (true) {
        try {
            const result = await (redisDkronConsumer as any).xreadgroup(
                'GROUP', config.dkronConsumerGroup, config.dkronConsumerName,
                'COUNT', 1, 'BLOCK', 0, 'STREAMS', config.process_out, '>'
            );

            if (result && result.length > 0) {
                const [streamName, messages] = result[0];
                for (const [id, fields] of messages) {
                    const dataIndex = fields.indexOf('data');
                    if (dataIndex === -1) continue;

                    const rawMessage = fields[dataIndex + 1];
                    logger.info(`Received Process message ${id} from ${streamName}: ${rawMessage}`);

                    try {
                        const dkronMsg = JSON.parse(rawMessage);

                        // Notify user via Telegram
                        if (config.adminId) {
                            const jobName = dkronMsg.job || 'Unknown';
                            const description = dkronMsg.description || 'No description';
                            const exitCode = dkronMsg.exit_code;
                            const notification = `任务 \`${jobName}\` - \`${description}\` 已经完成，exit_code = ${exitCode}`;
                            await sender.sendAdminMessage(config.adminId, notification);
                        }

                    } catch (parseErr) {
                        logger.error('Error parsing Process message:', parseErr);
                    }

                    // Acknowledge
                    await redisDkronConsumer.xack(config.process_out, config.dkronConsumerGroup, id);
                }
            }
        } catch (error) {
            logger.error('Error processing Process result:', error);
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
    }
}
