#!/bin/sh

cat << "EOF"
  _______        _____ _______ _______ _______  ______
     |    |  |  |   |      |       |    |______ |_____/
     |    |__|__| __|__    |       |    |______ |    \_
                                                       
EOF

echo "node version: $(node --version)"

echo "Twitter (twapi) container started. Keeping it alive with tail -f /dev/null..."
tail -f /dev/null
