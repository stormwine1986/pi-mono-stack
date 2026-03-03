#!/bin/bash
cat << "BANNER_EOF"
  ______        _______ 
 / ___\ \      / / ____|
 \___ \\ \ /\ / /|  _|  
  ___) |\ V  V / | |___ 
 |____/  \_/\_/  |_____|
                                    
BANNER_EOF

echo "SWE container started. GitHub CLI (gh), git, and docker are available."
gh auth setup-git
docker --version
git --version
gh --version
echo "User: $(whoami) (UID: $(id -u))"
echo "Workdir: $(pwd)"

# Register Dkron jobs if DKRON_URL is set
if [ -n "$DKRON_URL" ]; then
    echo "Registering Dkron jobs..."
    curl -s -X POST "$DKRON_URL/jobs" \
        -H "Content-Type: application/json" \
        -d '{
            "name": "swe-docker-prune-dangling",
            "displayname": "自动清理 Dangling 镜像",
            "schedule": "0 0 */2 * * *",
            "timezone": "Asia/Shanghai",
            "owner": "swe",
            "executor": "shell",
            "executor_config": {
                "command": "docker image prune -f"
            },
            "retries": 3,
            "concurrency": "forbid"
        }' > /dev/null 2>&1 || true
    echo "Dkron job registration complete."
fi

# Initialize .swe directory in workspace
WORKSPACE_DIR="/home/pi-mono/.pi/agent/workspace"
if [ -d "$WORKSPACE_DIR" ]; then
    SWE_DIR="$WORKSPACE_DIR/.swe"
    if [ ! -d "$SWE_DIR" ]; then
        echo "Initializing .swe directory at $SWE_DIR..."
        mkdir -p "$SWE_DIR"
    else
        echo ".swe directory already exists at $SWE_DIR"
    fi
else
    echo "Warning: Workspace directory $WORKSPACE_DIR does not exist."
fi

echo "Keeping it alive with tail -f /dev/null..."
tail -f /dev/null