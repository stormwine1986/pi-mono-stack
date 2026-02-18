# Use official Playwright image which includes browsers and system dependencies
FROM mcr.microsoft.com/playwright/python:v1.49.1-jammy

# Install uv for fast package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install browser-use and its dependencies
RUN uv pip install --system "browser-use[cli]" playwright

# Ensure browsers are ready (though base image has them, sometimes specific versions are needed by the lib)
RUN python -m playwright install chromium

# Copy skill definition and scripts
# Assumes build context is the browser-use directory
COPY SKILL.md /app/SKILL.md
COPY scripts/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Setup user 1000 and directory permissions
RUN id -u 1000 &>/dev/null || useradd -u 1000 -m -s /bin/bash pi-mono
RUN mkdir -p /home/pi-mono/.pi/agent/workspace && \
    chown -R 1000:1000 /home/pi-mono

CMD ["/app/entrypoint.sh"]
