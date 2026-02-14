# TG Bot Gateway

This service acts as a bridge between Telegram and a Redis-based task queue.

## Workflow

1.  **Receive Updates**: Listens for messages from Telegram and pushes them to `tg_updates_queue` in Redis.
2.  **Send Results**: Monitors `tg_results_queue` in Redis and sends results back to the corresponding Telegram chat.

## Configuration

Copy `.env.example` to `.env` and fill in your values:

- `TELEGRAM_TOKEN`: Your bot token from @BotFather.
- `REDIS_URL`: Connection string for Redis.

## Development

```bash
npm install
npm run dev
```

## Production

```bash
npm run build
npm start
```

## Redis Message Formats

### Input Queue (`tg_updates_queue`)
```json
{
  "chatId": 12345678,
  "messageId": 100,
  "text": "Hello world",
  "username": "user123",
  "timestamp": 1700000000000
}
```

### Output Queue (`tg_results_queue`)
```json
{
  "chatId": 12345678,
  "messageId": 100,
  "response": "Processing complete!"
}
```
