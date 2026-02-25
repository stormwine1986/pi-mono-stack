#!/bin/bash
set -e

# Initialize the directory
mkdir -p /home/pi-mono/.pi/agent/workspace/.gateway

# Execute the command given to the container
exec "$@"
