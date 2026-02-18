#!/bin/bash
set -e

# 打印提示信息
cat << "EOF"
 ____                                       _   _            
| __ ) _ __ _____      _____  ___ _ __     | | | |___  ___   
|  _ \| '__/ _ \ \ /\ / / __|/ _ \ '__|    | | | / __|/ _ \  
| |_) | | | (_) \ V  V /\__ \  __/ |       | |_| \__ \  __/  
|____/|_|  \___/ \_/\_/ |___/\___|_|        \___/|___/\___|  

EOF

# Initialize workspace/.browser-use
WORKSPACE_DIR="/home/pi-mono/.pi/agent/workspace"
BROWSER_USE_DIR="${WORKSPACE_DIR}/.browser-use"

if [ ! -d "$BROWSER_USE_DIR" ]; then
    echo "Creating .browser-use directory in workspace: $BROWSER_USE_DIR"
    mkdir -p "$BROWSER_USE_DIR"
fi

echo "Container is running. You can now use 'browser-use' CLI command."

# 使用 tail -f /dev/null 让容器保持永久运行（这是 Docker 中常用的挂起命令）
exec tail -f /dev/null
