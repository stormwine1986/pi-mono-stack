FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Install python dependencies for risk management
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip install --no-cache-dir requests pandas numpy scipy redis falkordb openbb && \
    python -c "from openbb import obb" || true && \
    chmod -R 777 /usr/local/lib/python3.11/site-packages/openbb /usr/local/lib/python3.11/site-packages/openbb_core || true

# Create non-root user and set up app directory
RUN mkdir /app && groupadd -g 1000 pi-mono && \
    useradd -u 1000 -g 1000 -m pi-mono && \
    chown -R pi-mono:pi-mono /app

WORKDIR /app

# Copy scripts
COPY --chown=pi-mono:pi-mono scripts /app/scripts
COPY --chown=pi-mono:pi-mono SKILL.md /app/SKILL.md

# Ensure entrypoint and CLI are executable
RUN chmod +x /app/scripts/entrypoint.sh /app/scripts/irm.sh && \
    ln -s /app/scripts/irm.sh /usr/local/bin/irm

# Change WORKDIR to the workspace for runtime operations
WORKDIR /home/pi-mono/.pi/agent/workspace
RUN chown -R pi-mono:pi-mono /home/pi-mono/.pi
USER 1000:1000

# Set the entrypoint script
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
