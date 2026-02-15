export const config = {
    telegramToken: process.env.TELEGRAM_TOKEN || '',
    redisUrl: process.env.REDIS_URL || 'redis://localhost:6379',
    agent_in: 'agent_in',
    agent_out: 'agent_out',
    agent_ctl: 'agent_ctl',
    tgConsumerGroup: 'tg-bot',
    tgConsumerName: 'bot-1',
    allowedUserIds: process.env.ALLOWED_USER_IDS
        ? process.env.ALLOWED_USER_IDS.toString().split(',').map(id => parseInt(id.trim()))
        : [],
};
