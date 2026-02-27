#!/bin/bash

# Print ASCII Art
cat << "EOF"
  _____ _____  __  __ 
 |_   _|  __ \|  \/  |
   | | | |__) | \  / |
   | | |  _  /| |\/| |
  _| |_| | \ \| |  | |
 |_____|_|  \_\_|  |_|
                      
 Investment Risk Management
EOF

echo "IRM container started."

# Initialize workspace .irm directory
WORKSPACE_DIR="/home/pi-mono/.pi/agent/workspace"
IRM_CONFIG_DIR="$WORKSPACE_DIR/.irm"

if [ ! -d "$IRM_CONFIG_DIR" ]; then
    echo "Initializing $IRM_CONFIG_DIR..."
    mkdir -p "$IRM_CONFIG_DIR"
fi

echo "Keeping container alive with tail -f /dev/null..."

# Keep the container alive
tail -f /dev/null
