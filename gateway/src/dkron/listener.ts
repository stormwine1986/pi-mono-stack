import { Redis } from 'ioredis';
import { nanoid } from 'nanoid';
import { WorkerTask } from 'pi-protocol';
import { config } from '../config.js';
import { logger } from '../logger.js';

export async function startDkronListener(
    redisProducer: Redis,
    redisDkronConsumer: Redis
) {
    logger.info(`Starting Dkron listener on ${config.dkron_out} (group: ${config.dkronConsumerGroup})...`);

    // Ensure consumer group exists
    try {
        await redisDkronConsumer.xgroup('CREATE', config.dkron_out, config.dkronConsumerGroup, '$', 'MKSTREAM');
        logger.info(`Dkron Consumer group ${config.dkronConsumerGroup} created`);
    } catch (err: any) {
        if (err.message.includes('BUSYGROUP')) {
            // Group already exists
        } else {
            logger.error('Error creating Dkron consumer group:', err);
        }
    }

    while (true) {
        try {
            const result = await (redisDkronConsumer as any).xreadgroup(
                'GROUP', config.dkronConsumerGroup, config.dkronConsumerName,
                'COUNT', 1, 'BLOCK', 0, 'STREAMS', config.dkron_out, '>'
            );

            if (result && result.length > 0) {
                const [streamName, messages] = result[0];
                for (const [id, fields] of messages) {
                    const dataIndex = fields.indexOf('data');
                    if (dataIndex === -1) continue;

                    const rawMessage = fields[dataIndex + 1];
                    logger.info(`Received Dkron message ${id} from ${streamName}: ${rawMessage}`);

                    try {
                        const dkronMsg = JSON.parse(rawMessage);

                        const taskId = nanoid();
                        const task: WorkerTask = {
                            id: taskId,
                            source: 'dkron',
                            prompt: `Received an event from the \`scheduler\`:\n\n${JSON.stringify(dkronMsg, null, 2)}\n\nIf this is a reminder for a Todo task, complete it as requested. If a background task has finished, analyze the output and provide a summary of the execution results.`,
                            metadata: { dkron: dkronMsg }
                        };

                        logger.info(`Forwarding Dkron event to ${config.agent_in}: ${(task.prompt || '').split('\n')[0]}`);
                        await redisProducer.xadd(config.agent_in, '*', 'payload', JSON.stringify(task));

                    } catch (parseErr) {
                        logger.error('Error parsing Dkron message:', parseErr);
                    }

                    // Acknowledge
                    await redisDkronConsumer.xack(config.dkron_out, config.dkronConsumerGroup, id);
                }
            }
        } catch (error) {
            logger.error('Error processing Dkron result:', error);
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
    }
}
