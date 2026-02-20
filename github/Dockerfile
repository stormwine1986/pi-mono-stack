FROM alpine:latest

# Install github-cli, git, bash and other dependencies
RUN apk add --no-cache github-cli bash git docker-cli

# Create pi-mono user and group with UID/GID 1000
RUN addgroup -g 1000 pi-mono && \
    adduser -u 1000 -G pi-mono -D pi-mono

# Create /app directory and set ownership
RUN mkdir -p /app && chown 1000:1000 /app

# Set up working directory
RUN chown -R pi-mono:pi-mono /home/pi-mono

WORKDIR /home/pi-mono

# Copy the github skill files
COPY . /app
RUN chown -R pi-mono:pi-mono /app
RUN chmod +x /app/scripts/entrypoint.sh

USER pi-mono

ENV GIT_AUTHOR_NAME=stormwine1986
ENV GIT_AUTHOR_EMAIL=stormwine.jia@gmail.com
ENV GIT_COMMITTER_NAME=stormwine1986
ENV GIT_COMMITTER_EMAIL=stormwine.jia@gmail.com

# Set the default command to run the entrypoint script
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
