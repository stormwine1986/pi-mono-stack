#!/usr/bin/env bash
set -euo pipefail

# ──────────────────────────────────────────────
# stack-ctl.sh — control script for pi-mono-stack
# ──────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export COMPOSE_PROJECT_NAME=pi-mono-stack
export BASE_CONFIG_PATH="${SCRIPT_DIR}"

# ---------- secrets from pass ----------
load_secrets() {
  echo "🔑 Loading secrets from pass …"
  export GEMINI_API_KEY="$(pass show GEMINI_API_KEY)"
  export TELEGRAM_TOKEN="$(pass show TELEGRAM_TOKEN)"
  export OPENROUTER_API_KEY="$(pass show OPENROUTER_API_KEY)"
  export TAVILY_API_KEY="$(pass show TAVILY_API_KEY)"
  export GITHUB_TOKEN="$(pass show GITHUB_TOKEN)"
  export HF_TOKEN="$(pass show HF_TOKEN)"
  export TWITTERAPI_KEY="$(pass show TWITTERAPI_KEY)"
  export FRED_API_KEY="$(pass show FRED_API_KEY)"
  export OPENOBSERVE_ADMIN_ACCOUNT="$(pass show OPENOBSERVE_ADMIN_ACCOUNT)"
  export OPENOBSERVE_ROOT_PASSWORD="$(pass show OPENOBSERVE_ROOT_PASSWORD)"
  export OPENOBSERVE_AUTH_HEADER="Basic $(echo -n "${OPENOBSERVE_ADMIN_ACCOUNT}:${OPENOBSERVE_ROOT_PASSWORD}" | base64)"

  echo "✅ Secrets loaded."
}

# ---------- commands ----------
cmd_up() {
  echo "📂 Ensuring .pi/agent directories exist …"
  mkdir -p "${SCRIPT_DIR}/.pi/agent/sessions"
  mkdir -p "${SCRIPT_DIR}/.pi/agent/workspace"

  echo "📂 Preparing .pi directory permissions …"
  if [ -d "${SCRIPT_DIR}/.pi" ]; then
    sudo chown -R 1000:1000 "${SCRIPT_DIR}/.pi"
    sudo chmod -R g+rwX "${SCRIPT_DIR}/.pi"
  fi
  echo "🚀 Starting stack …"
  docker compose -f "${SCRIPT_DIR}/docker-compose.yml" up -d "$@"
  echo "✅ Stack is up."
}

cmd_logs() {
  echo "📋 Following logs …"
  docker compose -f "${SCRIPT_DIR}/docker-compose.yml" logs -f "$@"
}

cmd_exec() {
  echo "🏃 Executing command in stack …"
  docker compose -f "${SCRIPT_DIR}/docker-compose.yml" exec "$@"
}

cmd_build() {
  echo "🏗️ Building stack …"
  docker compose -f "${SCRIPT_DIR}/docker-compose.yml" build "$@"
  echo "✅ Build complete."
}

cmd_down() {
  echo "🛑 Stopping stack …"
  docker compose -f "${SCRIPT_DIR}/docker-compose.yml" down "$@"
  echo "✅ Stack is down."
}

cmd_restart() {
  if [ $# -gt 0 ]; then
    echo "♻️ Restarting specific services: $@ …"
    cmd_up --force-recreate "$@"
  else
    cmd_down
    cmd_up
  fi
}

cmd_backup() {
  local TIMESTAMP=$(date +%Y%m%d%H%M%S)
  local BACKUP_NAME="pi-workspace-${TIMESTAMP}.tar.gz"
  local LOCAL_BACKUP_PATH="/tmp/${BACKUP_NAME}"
  local REMOTE="garage:pi-workspace"

  echo "📦 Compressing .pi/agent/workspace …"
  if [ ! -d "${SCRIPT_DIR}/.pi/agent/workspace" ]; then
    echo "❌ Error: Workspace directory not found at ${SCRIPT_DIR}/.pi/agent/workspace"
    exit 1
  fi
  tar --exclude='*.gguf' -czf "${LOCAL_BACKUP_PATH}" -C "${SCRIPT_DIR}/.pi/agent" workspace

  echo "📤 Uploading backup to ${REMOTE} …"
  rclone copy "${LOCAL_BACKUP_PATH}" "${REMOTE}"

  # Clean up local file
  rm "${LOCAL_BACKUP_PATH}"

  echo "🧹 Cleaning up old backups (keeping only 3) …"
  # List files, sort descending (newest first), skip first 3, and delete the rest
  local OLD_BACKUPS
  OLD_BACKUPS=$(rclone lsf "${REMOTE}" --files-only | sort -r | tail -n +4)
  
  if [ -n "$OLD_BACKUPS" ]; then
    for b in $OLD_BACKUPS; do
      echo "🗑️ Deleting old backup: $b"
      rclone deletefile "${REMOTE}/$b"
    done
  else
    echo "✨ No old backups to clean up."
  fi

  echo "✅ Backup complete."
}

# ---------- usage ----------
usage() {
  cat <<EOF
Usage: $(basename "$0") <command> [options]

Commands:
  up      Load secrets from pass and start all services (docker compose up -d)
  down    Stop and remove containers, networks (docker compose down)
  restart Stop and start all services (down then up)
  build   Build or rebuild services
  logs    Follow service logs (docker compose logs -f)
  exec    Run a command in a running container (docker compose exec)
  backup  Compress and backup agent workspace to rclone remote (garage)

EOF
  exit 1
}

# ---------- main ----------
if [[ $# -lt 1 ]]; then
  usage
fi

COMMAND="$1"; shift

# Load secrets for all commands that might interact with docker compose
case "$COMMAND" in
  up|down|restart|build|logs|exec) load_secrets ;;
esac

case "$COMMAND" in
  up)      cmd_up "$@" ;;
  down)    cmd_down "$@" ;;
  restart) cmd_restart "$@" ;;
  build)   cmd_build "$@" ;;
  logs)    cmd_logs "$@" ;;
  exec)    cmd_exec "$@" ;;
  backup)  cmd_backup ;;
  *)      echo "❌ Unknown command: $COMMAND"; usage ;;
esac
