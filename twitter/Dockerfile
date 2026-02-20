FROM node:20-alpine

WORKDIR /app

# Copy skill files
COPY SKILL.md /app/SKILL.md
COPY scripts/ /app/scripts/
RUN chmod +x /app/scripts/entrypoint.sh /app/scripts/twapi.js

# Link the twapi script so it's available globally
RUN ln -s /app/scripts/twapi.js /usr/local/bin/twapi

# Set the default command to run the entrypoint script
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
