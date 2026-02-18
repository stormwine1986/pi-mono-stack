#!/bin/bash

cat << "EOF"
  _______       __      _______ _      __     __
 |__   __|/\    \ \    / /_   _| |     \ \   / /
    | |  /  \    \ \  / /  | | | |      \ \_/ / 
    | | / /\ \    \ \/ /   | | | |       \   /  
    | |/ ____ \    \  /   _| |_| |____    | |   
    |_/_/    \_\    \/   |_____|______|   |_|   
                                                
EOF

echo "Tavily container started. Keeping it alive with tail -f /dev/null..."
tail -f /dev/null
