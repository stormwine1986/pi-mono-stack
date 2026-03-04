#!/bin/bash

# Print ASCII Art
echo "
 __  __ ______ __  __  _____ ______          _____   _____ _    _ 
|  \/  |  ____|  \/  |/ ____|  ____|   /\   |  __ \ / ____| |  | |
| \  / | |__  | \  / | (___ | |__     /  \  | |__) | |    | |__| |
| |\/| |  __| | |\/| |\___ \|  __|   / /\ \ |  _  /| |    |  __  |
| |  | | |____| |  | |____) | |____ / ____ \| | \ \| |____| |  | |
|_|  |_|______|_|  |_|_____/|______/_/    \_\_|  \_\\_____|_|  |_|
"

echo "Memory Service Environment Information:"
echo "-------------------"
echo "Python Version: $(python3 --version 2>&1)"
echo "REDIS_URL: $REDIS_URL"
echo "LLAMA_SERVER_URL: $LLAMA_SERVER_URL"
echo "LLAMA_EMBEDDING_URL: $LLAMA_EMBEDDING_URL"
echo "-------------------"

# Ensure data directory has correct permissions (handled by Dockerfile but just in case)
# mkdir -p /data

echo "Launching Pi Memory Service (Observer + API)..."
python3 /app/main.py
