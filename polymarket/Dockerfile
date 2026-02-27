FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip install --no-cache-dir httpx

# Copy local skill files
COPY . /app/

# Ensure scripts are executable
RUN chmod +x /app/scripts/gamma_tool.py /app/scripts/entrypoint.sh

# Link the tool for global access
RUN ln -s /app/scripts/gamma_tool.py /usr/local/bin/gamma_tool

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Set the entrypoint
ENTRYPOINT ["/app/scripts/entrypoint.sh"]