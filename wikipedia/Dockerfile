FROM python:3.11-alpine

LABEL openclaw-skill=1

WORKDIR /app

# Install dependencies
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip install --no-cache-dir html2text

# Copy skill files and scripts
# We assume the build context is the 'wikipedia' directory
COPY . /app/

# Ensure the scripts are executable
RUN chmod +x /app/scripts/query_wikipedia.py \
             /app/scripts/query_wikidata.py \
             /app/scripts/entrypoint.sh

# Set the entrypoint
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
