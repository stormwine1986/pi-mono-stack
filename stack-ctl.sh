#!/usr/bin/env bash
set -euo pipefail

# ──────────────────────────────────────────────
# stack-ctl.sh — control script for pi-mono-stack
# ──────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---------- secrets from pass ----------
load_secrets() {
  echo "🔑 Loading secrets from pass …"
  export GEMINI_API_KEY="$(pass show GEMINI_API_KEY)"
  export TELEGRAM_TOKEN="$(pass show TELEGRAM_TOKEN)"
  export OPENROUTER_API_KEY="$(pass show OPENROUTER_API_KEY)"
  export LANGFUSE_SECRET_KEY="$(pass show LANGFUSE_SECRET_KEY)"
  export VOYAGE_API_KEY="$(pass show VOYAGE_API_KEY)"
  echo "✅ Secrets loaded."
}

# ---------- commands ----------
cmd_up() {
  load_secrets
  echo "🚀 Starting stack …"
  docker compose -f "${SCRIPT_DIR}/docker-compose.yml" up -d "$@"
  echo "✅ Stack is up."
}

cmd_logs() {
  echo "📋 Following logs …"
  docker compose -f "${SCRIPT_DIR}/docker-compose.yml" logs -f "$@"
}

cmd_build() {
  echo "🏗️ Building stack …"
  docker compose -f "${SCRIPT_DIR}/docker-compose.yml" build "$@"
  echo "✅ Build complete."
}

# ---------- usage ----------
usage() {
  cat <<EOF
Usage: $(basename "$0") <command> [options]

Commands:
  up      Load secrets from pass and start all services (docker compose up -d)
  build   Build or rebuild services
  logs    Follow service logs (docker compose logs -f)

EOF
  exit 1
}

# ---------- main ----------
if [[ $# -lt 1 ]]; then
  usage
fi

COMMAND="$1"; shift

case "$COMMAND" in
  up)     cmd_up "$@" ;;
  build)  cmd_build "$@" ;;
  logs)   cmd_logs "$@" ;;
  *)      echo "❌ Unknown command: $COMMAND"; usage ;;
esac
