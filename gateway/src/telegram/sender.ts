import { Telegraf } from 'telegraf';
import { WorkerResponse } from 'pi-protocol';
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

    async sendResponse(chatId: number, messageId: number, response: WorkerResponse) {
        if (response.status === 'success') {
            try {
                const htmlContent = formatToTelegramHtml(response.response);
                await this.bot.telegram.sendMessage(chatId, htmlContent, {
                    parse_mode: 'HTML',
                    reply_parameters: { message_id: messageId },
                });
            } catch (err) {
                logger.error('Failed to send HTML message, falling back to plain text:', err);
                await this.bot.telegram.sendMessage(chatId, response.response, {
                    reply_parameters: { message_id: messageId },
                });
            }
        } else if (response.status === 'error') {
            // Escape for MarkdownV2 just in case, but here we use simple formatting
            const escapedError = response.error.replace(/([_*\[\]()~`>#+\-=|{}.!])/g, '\\$1');
            await this.bot.telegram.sendMessage(chatId, `❌ *Error*: \`${escapedError}\``, {
                parse_mode: 'MarkdownV2',
                reply_parameters: { message_id: messageId },
            });
        } else if (response.status === 'progress') {
            await this.bot.telegram.sendChatAction(chatId, 'typing');
        }
    }

    async sendAdminMessage(adminId: number, title: string, content: string, isError: boolean = false) {
        // Simple wrapper for admin notifications (like Dkron)
        const emoji = isError ? '❌' : '🔔';
        const formattedContent = content
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');

        await this.bot.telegram.sendMessage(adminId, `${emoji} <b>${title}</b>\n\n${formattedContent}`, {
            parse_mode: 'HTML'
        });
    }
}
