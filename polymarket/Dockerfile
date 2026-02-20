# Stage 1: Builder
FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Clone the repository
RUN git clone https://github.com/Polymarket/agents.git /build/polymarket-agents

# Install dependencies into /root/.local
RUN pip install --user --no-cache-dir \
    httpx \
    pydantic \
    eth-account \
    py-clob-client \
    python-dotenv \
    web3==6.11.0

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Set environment variables
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH="/app/polymarket-agents:${PYTHONPATH}"
ENV PYTHONUNBUFFERED=1

# Copy installed python packages from builder
COPY --from=builder /root/.local /root/.local

# Copy cloned repository from builder
COPY --from=builder /build/polymarket-agents /app/polymarket-agents

# Copy local skill files
COPY . /app/

# Create __init__.py files
RUN touch /app/polymarket-agents/agents/__init__.py /app/polymarket-agents/agents/polymarket/__init__.py

# Ensure scripts are executable
RUN chmod +x /app/scripts/gamma_tool.py /app/scripts/entrypoint.sh

# Link the tool for global access
RUN ln -s /app/scripts/gamma_tool.py /usr/local/bin/gamma_tool

# Set the entrypoint
ENTRYPOINT ["/app/scripts/entrypoint.sh"]