import { config } from '../config.js';
import { logger } from '../logger.js';

const JOB_NAME = 'gateway-recovery';

export async function setupRecoveryJob() {
    const jobData = {
        name: JOB_NAME,
        schedule: '@every 5m',
        owner: 'gateway',
        executor: 'shell',
        executor_config: {
            command: "sh -c 'set -f; redis-cli -u $REDIS_URL XADD gateway_ctl * action RECOVER_PENDING'"
        },
        retries: 3,
        concurrency: 'forbid'
    };

    try {
        const jobsUrl = `${config.dkronUrl}/jobs`;
        logger.info(`Ensuring Dkron job "${JOB_NAME}" is up to date...`);

        const createResponse = await fetch(jobsUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(jobData)
        });

        if (createResponse.ok) {
            logger.info(`Dkron job "${JOB_NAME}" created successfully.`);
        } else {
            const errorText = await createResponse.text();
            logger.error(`Failed to create Dkron job: ${createResponse.status} ${errorText}`);
        }
    } catch (err) {
        logger.error('Error setting up Dkron recovery job:', err);
    }
}
