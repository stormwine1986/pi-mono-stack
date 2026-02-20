#!/bin/bash
set -e

echo "  ____   ___  _  __   __ __  __    _    ____  _  _______ _____ "
echo " |  _ \ / _ \| | \ \ / /|  \/  |  / \  |  _ \| |/ / ____|_   _|"
echo " | |_) | | | | |  \ V / | |\/| | / _ \ | |_) | ' /|  _|   | |  "
echo " |  __/| |_| | |___| |  | |  | |/ ___ \|  _ <| . \| |___  | |  "
echo " |_|    \___/|_____|_|  |_|  |_/_/   \_\_| \_\_|\_\_____| |_|  "
echo ""

# Keep the container alive
echo "Container is running in idle mode..."
tail -f /dev/null
