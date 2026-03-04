#!/bin/sh

# Execute the original Dkron command
echo "[Entrypoint] Starting Dkron agent with args: $@"
exec dkron "$@"
