#!/bin/sh

# Set DKRON_URL with a default fallback
DKRON_URL=${DKRON_URL:-"http://127.0.0.1:18047/v1"}

echo "[$(date)] Starting cleanup of finished non-periodic jobs..."

# 当前时间戳
NOW=$(date +%s)
# 1 小时前的时间戳
ONE_HOUR_AGO=$((NOW - 3600))

# 使用 jq 筛选符合条件的任务名：
# 1. next 为 null 或 零值（表示没有未来的调度计划）
# 2. success_count + error_count > 0 (表示至少执行过一次)
# 3. last_success 且 last_error 均早于 1 小时前
NAMES_TO_DELETE=$(curl -s "${DKRON_URL}/jobs" | jq -r --argjson limit "$ONE_HOUR_AGO" '
  .[] | 
  select((.next == null or .next == "0001-01-01T00:00:00Z") and (.success_count + .error_count > 0)) |
  select(((.last_success // "1970-01-01T00:00:00Z") | fromdateiso8601 < $limit) and 
         ((.last_error // "1970-01-01T00:00:00Z") | fromdateiso8601 < $limit)) |
  .name
')

if [ -z "$NAMES_TO_DELETE" ]; then
    echo "No matching jobs found to clean up."
else
    for NAME in $NAMES_TO_DELETE; do
        echo "Deleting job: $NAME"
        curl -s -X DELETE "${DKRON_URL}/jobs/$NAME" > /dev/null
    done
fi

echo "[$(date)] Cleanup completed."
