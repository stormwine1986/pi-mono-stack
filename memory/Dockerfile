FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Mem0 and its dependencies
# Including fastapi, uvicorn, redis for the memory service
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip install --no-cache-dir \
    "mem0ai" \
    "chromadb" \
    "redis" \
    "openai" \
    "fastapi" \
    "uvicorn" \
    "python-multipart"

# Create pi-mono user and group (1000:1000)
RUN groupadd -g 1000 pi-mono && \
    useradd -u 1000 -g pi-mono -m -s /bin/bash pi-mono

# Copy scripts and source code
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
COPY scripts/ /app/

RUN chmod +x /usr/local/bin/entrypoint.sh

# Data directory for Milvus and SQLite
RUN mkdir -p /data && chown -R pi-mono:pi-mono /data

# Switch to pi-mono user
USER pi-mono
WORKDIR /home/pi-mono
ENV HOME=/home/pi-mono
ENV PYTHONPATH=/app

# Use entrypoint script
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
