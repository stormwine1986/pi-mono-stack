#!/bin/bash

# Print ASCII Art
cat << "EOF"
  _______             _ _             __      _______ ______          __
 |__   __|           | (_)            \ \    / /_   _|  ____\ \        / /
    | |_ __ __ _  __| |_ _ __   __ _   \ \  / /  | | | |__   \ \  /\  / / 
    | | '__/ _` |/ _` | | '_ \ / _` |   \ \/ /   | | |  __|   \ \/  \/ /  
    | | | | (_| | (_| | | | | | (_| |    \  /   _| |_| |____   \  /\  /   
    |_|_|  \__,_|\__,_|_|_| |_|\__, |     \/   |_____|______|   \/  \/    
                                __/ |                                     
                               |___/                                      
EOF

echo "TradingView container started. Keeping it alive with tail -f /dev/null..."

# Keep the container alive
tail -f /dev/null