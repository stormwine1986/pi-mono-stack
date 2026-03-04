import { config } from '../config.js';
import { logger } from '../logger.js';

const RECOVERY_JOB_NAME = 'gateway-recovery';
const CLEANUP_JOB_NAME = 'gateway-temp-cleanup';

/**
 * Setup all Dkron jobs for the gateway.
 */
export async function setupAllJobs() {
    await setupRecoveryJob();
    await setupCleanupJob();
    await setupMonitorJob();
}

/**
 * Ensures a job is registered in Dkron that triggers pending message recovery.
 */
export async function setupRecoveryJob() {
    const jobData = {
        name: RECOVERY_JOB_NAME,
        schedule: '@every 5m',
        owner: 'gateway',
        executor: 'shell',
        executor_config: {
            command: "sh -c 'set -f; redis-cli -u $REDIS_URL XADD gateway_ctl MAXLEN ~ 100 * action RECOVER_PENDING'"
        },
        retries: 3,
        concurrency: 'forbid'
    };

    await ensureJob(jobData);
}

/**
 * Ensures a job is registered in Dkron that cleans up old temporary images in the .gateway directory.
 */
export async function setupCleanupJob() {
    // Delete files in .gateway older than 60 minutes, running every 2 hours
    const jobData = {
        name: CLEANUP_JOB_NAME,
        schedule: '@every 2h',
        owner: 'gateway',
        executor: 'shell',
        executor_config: {
            // Find files in .gateway that are more than 60 minutes old and delete them.
            // Using docker exec to run it inside the gateway container where the volume is mounted.
            command: "docker exec gateway find /home/pi-mono/.pi/agent/workspace/.gateway -type f -mmin +60 -delete"
        },
        retries: 1,
        concurrency: 'forbid'
    };

    await ensureJob(jobData);
}

/**
 * Ensures a job is registered in Dkron that monitors failed shell jobs and sends reminders.
 */
export async function setupMonitorJob() {
    const jobData = {
        name: 'monitor-failed-shell-jobs',
        schedule: '@every 15m',
        owner: 'gateway',
        executor: 'shell',
        executor_config: {
            command: "/usr/local/bin/monitor_jobs.sh"
        },
        tags: {
            role: "internal-monitor"
        },
        retries: 1,
        concurrency: 'forbid'
    };

    await ensureJob(jobData);
}

/**
 * Helper to POST a job definition to Dkron.
 */
async function ensureJob(jobData: any) {
    try {
        const jobsUrl = `${config.dkronUrl}/jobs`;
        logger.info(`Ensuring Dkron job "${jobData.name}" is up to date...`);

        const response = await fetch(jobsUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(jobData)
        });

        if (response.ok) {
            logger.info(`Dkron job "${jobData.name}" created/updated successfully.`);
        } else {
            const errorText = await response.text();
            logger.error(`Failed to create Dkron job "${jobData.name}": ${response.status} ${errorText}`);
        }
    } catch (err) {
        logger.error(`Error setting up Dkron job "${jobData.name}":`, err);
    }
}
