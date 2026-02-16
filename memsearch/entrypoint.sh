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

# Ensure the config directory exists
mkdir -p /home/pi-mono/.memsearch

echo "System Information:"
echo "-------------------"
if [ -f /etc/os-release ]; then
    . /etc/os-release
    echo "Linux Version: $PRETTY_NAME"
else
    echo "Linux Version: $(uname -sr)"
fi

echo "Python Version: $(python3 --version 2>&1)"
echo "Memsearch Version: $(pip show memsearch | grep Version | awk '{print $2}')"
echo "-------------------"

# Index memory directory on startup
echo "Indexing memory directory..."
memsearch index /home/pi-mono/.pi/agent/workspace/memory/

# Keep container alive
echo "Memsearch is ready."
tail -f /dev/null
