import { Redis } from 'ioredis';
import { TelegramSender } from './telegram/sender.js';
import { config } from './config.js';
import { logger } from './logger.js';

const SUMMARY_GROUP = 'background-summary-group';
const SUMMARY_CONSUMER = 'summary-agent';
const LITELLM_MODEL = 'gemini-3-flash-preview';

export async function startSummaryListener(
    redisSummaryConsumer: Redis,
    sender: TelegramSender
) {
    const stream = config.background_out;
    const adminId = config.adminId;

    if (!adminId) {
        logger.error('TG_ADMIN_ID not set, summary listener disabled');
        return;
    }

    logger.info(`Starting Summary listener on ${stream} (group: ${SUMMARY_GROUP})...`);

    // Ensure consumer group exists
    try {
        await redisSummaryConsumer.xgroup('CREATE', stream, SUMMARY_GROUP, '$', 'MKSTREAM');
        logger.info(`Summary Consumer group ${SUMMARY_GROUP} created`);
    } catch (err: any) {
        if (!err.message.includes('BUSYGROUP')) {
            logger.error('Error creating Summary consumer group:', err);
        }
    }

    while (true) {
        try {
            const result = await (redisSummaryConsumer as any).xreadgroup(
                'GROUP', SUMMARY_GROUP, SUMMARY_CONSUMER,
                'COUNT', 1, 'BLOCK', 0, 'STREAMS', stream, '>'
            );

            if (result && result.length > 0) {
                const [, messages] = result[0];
                for (const [id, fields] of messages) {
                    await handleMessage(id, fields, redisSummaryConsumer, sender, adminId, stream);
                }
            }
        } catch (error) {
            logger.error('Error in Summary listener loop:', error);
            await new Promise(resolve => setTimeout(resolve, 5000));
        }
    }
}

async function handleMessage(
    id: string,
    fields: string[],
    redis: Redis,
    sender: TelegramSender,
    adminId: number,
    stream: string
) {
    try {
        const payloadIndex = fields.indexOf('payload');
        if (payloadIndex === -1) {
            await redis.xack(stream, SUMMARY_GROUP, id);
            return;
        }

        const rawPayload = fields[payloadIndex + 1];
        const msg = JSON.parse(rawPayload);
        const jobName = msg.job;

        if (!jobName) {
            await redis.xack(stream, SUMMARY_GROUP, id);
            return;
        }

        // Skip internal/boring jobs to avoid noise
        const silentJobs = ['gateway-recovery', 'gateway-temp-cleanup', 'browser-use-temp-cleanup'];
        if (silentJobs.includes(jobName)) {
            await redis.xack(stream, SUMMARY_GROUP, id);
            return;
        }

        logger.info(`Summarizing job ${jobName} (id: ${id})...`);

        // 1. Fetch latest execution logs from Dkron
        const logs = await fetchJobLogs(jobName);
        if (!logs) {
            logger.warn(`No logs found for job ${jobName}, skipping summary.`);
            await redis.xack(stream, SUMMARY_GROUP, id);
            return;
        }

        // 2. Generate summary using LiteLLM
        const summary = await generateSummary(jobName, logs);

        // 3. Push to TG
        if (summary) {
            const finalMessage = `📊 *任务执行摘要: ${jobName}*\n\n${summary}`;
            await sender.sendAdminMessage(adminId, finalMessage);
        }

    } catch (err) {
        logger.error('Error handling summary message:', err);
    } finally {
        await redis.xack(stream, SUMMARY_GROUP, id);
    }
}

async function fetchJobLogs(jobName: string): Promise<string | null> {
    const maxRetries = 5;
    const retryDelay = 2000; // 2 seconds

    for (let i = 0; i < maxRetries; i++) {
        try {
            const response = await fetch(`${config.dkronUrl}/jobs/${jobName}/executions`);
            if (!response.ok) {
                logger.error(`Failed to fetch logs from Dkron (attempt ${i + 1}): ${response.statusText}`);
            } else {
                const executions = await response.json() as any[];
                if (executions && executions.length > 0) {
                    const latest = executions[0];
                    // Check if the execution is finished and has output
                    if (latest.finished_at && latest.output && latest.output.trim().length > 0) {
                        return latest.output;
                    }
                    logger.info(`Job ${jobName} execution found but not finished or empty output, retrying...`);
                } else {
                    logger.info(`No executions found for job ${jobName}, retrying...`);
                }
            }
        } catch (err) {
            logger.error(`Error fetching logs for ${jobName} (attempt ${i + 1}):`, err);
        }
        await new Promise(resolve => setTimeout(resolve, retryDelay));
    }

    logger.warn(`Failed to fetch finalized logs for ${jobName} after ${maxRetries} attempts.`);
    return null;
}

async function generateSummary(jobName: string, logs: string): Promise<string | null> {
    try {
        const prompt = `你是一个自动化运维助手。请根据以下后台任务的日志进行简明扼要的摘要（中文）。
任务名称: ${jobName}
执行摘要（仅供参考）:
${logs.slice(0, 5000)}

要求：
1. 重点说明任务是否成功执行。
2. 提取关键的输出结果或变动（例如拉取了哪个镜像，清理了多少文件等）。
3. 如果有错误，清晰指出报错原因。
4. **不要在摘要中包含原始日志内容或其片段**。
5. **字数严格控制在 100 字以内**。
6. 语言精炼，使用 Markdown 格式。`;

        const response = await fetch(`${config.llamaServerUrl}/chat/completions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                model: 'local-model',
                messages: [{ role: 'user', content: prompt }],
                temperature: 0.1,
                max_tokens: 200
            })
        });

        if (!response.ok) {
            const errBody = await response.text();
            logger.error(`Llama Server Error: ${response.status} - ${errBody}`);
            return null;
        }

        const data = await response.json() as any;
        return data.choices?.[0]?.message?.content || null;

    } catch (err) {
        logger.error(`Error generating summary for ${jobName}:`, err);
    }
    return null;
}
