function getTimestamp() {
    const now = new Date();
    const pad = (n: number, l = 2) => n.toString().padStart(l, '0');
    return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ` +
        `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}.${pad(now.getMilliseconds(), 3)}`;
}

export const logger = {
    info: (msg: string, ...args: any[]) => console.log(`[${getTimestamp()}] [INFO] ${msg}`, ...args),
    warn: (msg: string, ...args: any[]) => console.warn(`[${getTimestamp()}] [WARN] ${msg}`, ...args),
    error: (msg: string, ...args: any[]) => console.error(`[${getTimestamp()}] [ERROR] ${msg}`, ...args),
};
