FROM python:3.11-slim

WORKDIR /app

# Copy application files (assumes context is tavily directory)
COPY . /app

# Make scripts executable
RUN chmod +x /app/scripts/*.sh /app/scripts/*.py

# Metadata
LABEL role="Tools"

# Entrypoint
ENTRYPOINT ["/app/scripts/entrypoint.sh"]