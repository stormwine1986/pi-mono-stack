export const config = {
    telegramToken: process.env.TELEGRAM_TOKEN || '',
    redisUrl: process.env.REDIS_URL || 'redis://localhost:6379',
    agent_in: 'agent_in',
    agent_out: 'agent_out',
    agent_ctl: 'agent_ctl',
    background_out: 'background_out',
    reminder_out: 'reminder_out',
    tgConsumerGroup: 'tg-bot',
    tgConsumerName: 'bot-1',
    dkronConsumerGroup: 'gateway-dkron',
    dkronConsumerName: 'gateway-1',
    adminId: parseInt(process.env.TG_ADMIN_ID || '0'),
};
