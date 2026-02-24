# Use official Playwright image with Python 3.12 (noble)
# browser-use requires Python >= 3.11, jammy only has 3.10
FROM mcr.microsoft.com/playwright/python:v1.49.1-noble

# Install uv for fast package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Install browser-use and playwright
RUN uv pip install --system --no-cache --prerelease=allow "browser-use[cli]" playwright

# Install chromium browser
RUN python3 -m playwright install --with-deps chromium

# Setup user and directories (noble image may already have UID 1000)
RUN (id -u 1000 &>/dev/null || useradd -u 1000 -m -s /bin/bash pi-mono) && \
    mkdir -p /home/pi-mono/.pi/agent/workspace/.browser-use && \
    chown -R 1000:1000 /home/pi-mono

# Copy application files
WORKDIR /app
COPY . .
RUN chmod +x scripts/entrypoint.sh

# Set runtime environment
USER 1000
WORKDIR /home/pi-mono/.pi/agent/workspace

CMD ["/app/scripts/entrypoint.sh"]
