#!/bin/sh

# Derive DKRON_URL from DKRON_HTTP_ADDR port
PORT=$(echo "${DKRON_HTTP_ADDR:-:18047}" | sed 's/.*://')
DKRON_URL="http://127.0.0.1:${PORT}/v1"
REDIS_URL=${REDIS_URL:-"redis://127.0.0.1:6379"}

echo "[$(date)] Starting failed jobs check..."

# Get all jobs
JOBS=$(curl -s "${DKRON_URL}/jobs")

if [ -z "$JOBS" ] || [ "$JOBS" = "null" ]; then
    echo "No jobs found or failed to fetch jobs."
    exit 0
fi

# Iterate through jobs using jq
# Filter for jobs where executor is 'shell' and status is 'error'
echo "$JOBS" | jq -c '.[] | select(.executor == "shell" and .status == "error")' | while read -r job; do
    NAME=$(echo "$job" | jq -r '.name')
    
    echo "Found failed shell job: $NAME"
    
    # Prepare payload exactly as dkron-executor-reminder does
    PAYLOAD=$(jq -n \
        --arg job "$NAME" \
        --arg owner "system" \
        --arg message "Periodic shell job failed: $NAME. Please check logs." \
        --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        '{job: $job, owner: $owner, message: $message, timestamp: $ts}')
        
    echo "Pushing reminder for $NAME to reminder_out..."
    
    # Push to Redis stream reminder_out
    # We use redis-cli -u to support redis:// URLs
    redis-cli -u "$REDIS_URL" XADD reminder_out MAXLEN ~ 1000 payload "$PAYLOAD"
done

echo "[$(date)] Check completed."
