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

if [ -z "$DKRON_URL" ]; then
    echo "Warning: DKRON_URL not set, skipping Dkron job registration."
else
    echo "Registering IRM scheduled jobs with Dkron..."
    
    # helper for dkron job registration
    register_job() {
        local name=$1
        local schedule=$2
        local command=$3
        
        echo "Registering job: irm-$name ($schedule)..."
        curl -s -X POST "$DKRON_URL/jobs" \
            -H "Content-Type: application/json" \
            -d "{
                \"name\": \"irm-$name\",
                \"schedule\": \"$schedule\",
                \"timezone\": \"Asia/Shanghai\",
                \"owner\": \"irm\",
                \"executor\": \"shell\",
                \"executor_config\": {
                    \"command\": \"$command\"
                },
                \"retries\": 3,
                \"concurrency\": \"forbid\"
            }" > /dev/null
    }

    # Register earnings update (Daily at 12:00)
    register_job "update-earnings" "0 0 12 * * *" "docker exec irm python3 /app/scripts/ontology/update_earnings.py"
    
    # Register percentile update (Daily at 12:00)
    register_job "update-percentiles" "0 0 12 * * *" "docker exec irm python3 /app/scripts/ontology/update_percentiles.py"
    
    # Register price signals update (Weekly on Monday at 12:00)
    register_job "update-price-signals" "0 0 12 * * 1" "docker exec irm python3 /app/scripts/ontology/update_price_signals.py"

    # Register Beta calculation (Manual only)
    register_job "calc-betas" "@manually" "docker exec irm python3 /app/scripts/ontology/calc_betas.py"

    echo "Dkron job registration complete."
fi

echo "Keeping container alive with tail -f /dev/null..."

# Keep the container alive
tail -f /dev/null

