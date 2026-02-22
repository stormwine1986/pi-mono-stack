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
        const MAX_LENGTH = 4000;

        const sendChunk = async (text: string, isHtml: boolean = true) => {
            try {
                if (isHtml) {
                    await this.bot.telegram.sendMessage(adminId, formatToTelegramHtml(text), {
                        parse_mode: 'HTML'
                    });
                } else {
                    await this.bot.telegram.sendMessage(adminId, text);
                }
            } catch (err: any) {
                if (err.description?.includes('message is too long')) {
                    // If even a chunk is too long (unlikely if split correctly), further split it
                    const subChunks = this.simpleSplit(text, MAX_LENGTH);
                    for (const sub of subChunks) {
                        await this.bot.telegram.sendMessage(adminId, sub);
                    }
                } else if (isHtml) {
                    logger.error('Failed to send HTML chunk, falling back to plain text:', err);
                    await this.bot.telegram.sendMessage(adminId, text);
                } else {
                    logger.error('Failed to send plain text chunk:', err);
                }
            }
        };

        if (content.length <= MAX_LENGTH) {
            await sendChunk(content);
        } else {
            const chunks = this.splitByRelevantNewlines(content, MAX_LENGTH);
            for (const chunk of chunks) {
                await sendChunk(chunk);
            }
        }
    }

    private splitByRelevantNewlines(text: string, maxLength: number): string[] {
        const chunks: string[] = [];
        let remaining = text;

        while (remaining.length > 0) {
            if (remaining.length <= maxLength) {
                chunks.push(remaining);
                break;
            }

            let splitIndex = remaining.lastIndexOf('\n', maxLength);
            if (splitIndex === -1) {
                splitIndex = maxLength;
            }

            chunks.push(remaining.substring(0, splitIndex));
            remaining = remaining.substring(splitIndex).trimStart();
        }

        return chunks;
    }

    private simpleSplit(text: string, maxLength: number): string[] {
        const chunks: string[] = [];
        for (let i = 0; i < text.length; i += maxLength) {
            chunks.push(text.substring(i, i + maxLength));
        }
        return chunks;
    }
}
