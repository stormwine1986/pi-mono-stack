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

# Ensure the symbolic link exists and points to the correct location
LINK_PATH="/home/pi-mono/.memsearch"
TARGET_PATH="/home/pi-mono/.pi/agent/workspace/.memsearch"

if [ ! -L "$LINK_PATH" ]; then
    echo "Creating symbolic link $LINK_PATH -> $TARGET_PATH"
    ln -sf "$TARGET_PATH" "$LINK_PATH"
fi

# Ensure data directory exists (it might be overridden by volume mount)
mkdir -p "$TARGET_PATH"

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

# Keep container running
exec tail -f /dev/null
