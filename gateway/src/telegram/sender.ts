import { Telegraf } from 'telegraf';
import { logger } from '../logger.js';

// Helper to sanitize and format message content for Telegram HTML parse mode
export function formatToTelegramHtml(text: string): string {
    // 1. Escape HTML special characters first
    let escapedText = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    // 2. Process line by line for Tables and Headers
    const lines = escapedText.split('\n');
    const resultLines: string[] = [];
    let tableBuffer: string[] = [];

    for (const line of lines) {
        if (line.trim().startsWith('|')) {
            tableBuffer.push(line);
        } else {
            if (tableBuffer.length > 0) {
                // Wrap table in mono-space block for alignment
                resultLines.push(`<pre>${tableBuffer.join('\n')}</pre>`);
                tableBuffer = [];
            }

            const trimmed = line.trim();
            if (line.match(/^#+\s+/)) {
                // Headers: # Header -> <b>Header</b>
                resultLines.push(line.replace(/^#+\s+(.*)$/, '<b>$1</b>'));
            } else if (trimmed === '---' || trimmed === '***') {
                // Horizontal Rule
                resultLines.push('<b>──────────────</b>');
            } else {
                resultLines.push(line);
            }
        }
    }
    if (tableBuffer.length > 0) {
        resultLines.push(`<pre>${tableBuffer.join('\n')}</pre>`);
    }

    // 3. Apply inline formatting (Bold and Code)
    return resultLines.join('\n')
        .replace(/\*\*(.*?)\*\*/g, '<b>$1</b>')
        .replace(/`(.*?)`/g, '<code>$1</code>');
}

export class TelegramSender {
    constructor(private bot: Telegraf) { }

    async sendAdminMessage(adminId: number, content: string) {
        const formattedContent = formatToTelegramHtml(content);

        try {
            await this.bot.telegram.sendMessage(adminId, formattedContent, {
                parse_mode: 'HTML'
            });
        } catch (err) {
            logger.error('Failed to send HTML message, falling back to plain text:', err);
            await this.bot.telegram.sendMessage(adminId, content);
        }
    }
}
