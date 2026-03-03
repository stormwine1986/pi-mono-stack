#!/bin/sh

# Function to register the job
register_job() {
    # Give Dkron some time to start and bind port
    sleep 5
    
    # Derive DKRON_URL from DKRON_HTTP_ADDR port
    PORT=$(echo "${DKRON_HTTP_ADDR:-:18047}" | sed 's/.*://')
    DKRON_URL="http://127.0.0.1:${PORT}/v1"

    echo "[Entrypoint] Waiting for Dkron API to be ready at ${DKRON_URL}..."
    MAX_RETRIES=30
    COUNT=0
    until curl -s "${DKRON_URL}/status" > /dev/null || [ $COUNT -eq $MAX_RETRIES ]; do
        sleep 2
        COUNT=$((COUNT + 1))
    done

    if [ $COUNT -eq $MAX_RETRIES ]; then
        echo "[Entrypoint] Error: Dkron API did not become ready in time."
        return 1
    fi

    echo "[Entrypoint] Dkron is ready. Checking monitoring job..."

    # Check if the monitoring job already exists
    JOB_CHECK=$(curl -s "${DKRON_URL}/jobs/monitor-failed-shell-jobs")
    
    if echo "$JOB_CHECK" | grep -q "not found" || [ -z "$JOB_CHECK" ] || [ "$JOB_CHECK" = "null" ]; then
        echo "[Entrypoint] Registering monitoring job 'monitor-failed-shell-jobs'..."
        curl -X POST -H "Content-Type: application/json" -d '{
            "name": "monitor-failed-shell-jobs",
            "schedule": "@every 15m",
            "executor": "shell",
            "executor_config": {
                "command": "/usr/local/bin/monitor_jobs.sh"
            },
            "owner": "system",
            "tags": {
                "role": "internal-monitor"
            }
        }' "${DKRON_URL}/jobs"
        echo "[Entrypoint] Monitoring job registered."
    else
        echo "[Entrypoint] Monitoring job already exists."
    fi
}

# Start the registration process in the background
register_job &

# Execute the original Dkron command
echo "[Entrypoint] Starting Dkron agent with args: $@"
exec dkron "$@"
