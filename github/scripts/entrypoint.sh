#!/bin/bash
cat << "BANNER_EOF"
  ____ ___ _____ _   _ _   _ ____  
 / ___|_ _|_   _| | | | | | | __ ) 
| |  _ | |  | | | |_| | | | |  _ \ 
| |_| || |  | | |  _  | |_| | |_) |
 \____|___| |_| |_| |_|\___/|____/ 
                                   
BANNER_EOF

echo "GitHub container started. GitHub CLI (gh), git, and docker are available."
gh auth setup-git
docker --version
git --version
gh --version
echo "User: $(whoami) (UID: $(id -u))"
echo "Workdir: $(pwd)"

# Initialize .github directory in workspace
WORKSPACE_DIR="/home/pi-mono/.pi/agent/workspace"
if [ -d "$WORKSPACE_DIR" ]; then
    GITHUB_DIR="$WORKSPACE_DIR/.github"
    if [ ! -d "$GITHUB_DIR" ]; then
        echo "Initializing .github directory at $GITHUB_DIR..."
        mkdir -p "$GITHUB_DIR"
    else
        echo ".github directory already exists at $GITHUB_DIR"
    fi
else
    echo "Warning: Workspace directory $WORKSPACE_DIR does not exist."
fi

echo "Keeping it alive with tail -f /dev/null..."
tail -f /dev/null