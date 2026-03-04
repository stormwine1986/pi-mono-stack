#!/bin/bash

# Print ASCII Art
echo "
 __  __ ______ __  __  ____  _____ __     __
|  \/  |  ____|  \/  |/ __ \|  __ \\ \   / /
| \  / | |__  | \  / | |  | | |__) |\ \_/ / 
| |\/| |  __| | |\/| | |  | |  _  /  \   /  
| |  | | |____| |  | | |__| | | \ \   | |   
|_|  |_|______|_|  |_|\____/|_|  \_\  |_|   
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
