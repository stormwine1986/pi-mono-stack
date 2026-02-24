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

# 路径定义
WORKSPACE_DIR="/home/pi-mono/.pi/agent/workspace"
BROWSER_USE_DIR="${WORKSPACE_DIR}/.browser-use"

# 运行时检查：因为宿主挂载会覆盖镜像预建目录，所以必须在启动时确保子目录存在
if [ ! -d "$BROWSER_USE_DIR" ]; then
    echo "Initializing: .browser-use directory not found in mounted workspace. Creating it..."
    mkdir -p "$BROWSER_USE_DIR"
fi

# 切换到目标工作目录（防止 WORKDIR 因为挂载失效或偏移）
cd "$BROWSER_USE_DIR"

echo "Browser-use container is ready."
echo "Current Directory: $(pwd)"
echo "You can now use 'docker exec browser-use browser-use <command>'"

# 保持容器永久运行
exec tail -f /dev/null
