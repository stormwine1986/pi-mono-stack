FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Install python dependencies
# akshare depends on many libs, tvDatafeed depends on pandas/requests
# We install akshare first, then tvDatafeed from git
RUN pip install --no-cache-dir requests pandas akshare
RUN pip install --no-cache-dir git+https://github.com/rongardF/tvdatafeed.git

# Set up app directory
WORKDIR /app

# Copy scripts

COPY scripts /app/scripts
COPY SKILL.md /app/SKILL.md

# Ensure scripts are executable
RUN chmod +x /app/scripts/entrypoint.sh /app/scripts/query_market_data.py

# Set the entrypoint script
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
