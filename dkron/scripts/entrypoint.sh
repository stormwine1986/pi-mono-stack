#!/bin/sh

DKRON_URL=${DKRON_URL:-"http://127.0.0.1:18047/v1"}

echo "[Entrypoint] Starting Dkron agent with args: $@"
dkron "$@" &
DKRON_PID=$!

# Wait for Dkron API to be ready
echo "[Entrypoint] Waiting for Dkron API..."
until curl -sf "${DKRON_URL}" > /dev/null 2>&1; do
    sleep 2
done
echo "[Entrypoint] Dkron API is ready, waiting 10s for backend initialization..."
sleep 10
echo "[Entrypoint] Proceeding with registration..."

# Register self-maintenance jobs
echo "[Entrypoint] Registering self-maintenance jobs..."

curl -sf -X POST "${DKRON_URL}/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "monitor-failed-shell-jobs",
    "schedule": "@every 15m",
    "owner": "dkron",
    "executor": "shell",
    "executor_config": {
      "command": "/usr/local/bin/monitor_jobs.sh"
    },
    "tags": {
      "role": "dkron"
    },
    "retries": 1,
    "concurrency": "forbid"
  }' && echo " -> monitor-failed-shell-jobs registered."

curl -sf -X POST "${DKRON_URL}/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "cleanup-finished-once-jobs",
    "schedule": "@every 1h",
    "owner": "dkron",
    "executor": "shell",
    "executor_config": {
      "command": "/usr/local/bin/cleanup_once_jobs.sh"
    },
    "tags": {
      "role": "dkron"
    },
    "retries": 1,
    "concurrency": "forbid"
  }' && echo " -> cleanup-finished-once-jobs registered."

echo "[Entrypoint] Self-maintenance jobs registered."

# Wait for Dkron process
wait $DKRON_PID
