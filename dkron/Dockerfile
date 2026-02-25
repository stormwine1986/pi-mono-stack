FROM golang:1.24-alpine AS builder

WORKDIR /app

# Copy the entire dkron directory content
COPY . .

# Tidy dependencies
RUN go mod tidy

# Build the background executor plugin
RUN CGO_ENABLED=0 GOOS=linux go build -o dkron-executor-background plugins/executor-background/main.go

# Build the reminder executor plugin
RUN CGO_ENABLED=0 GOOS=linux go build -o dkron-executor-reminder plugins/executor-reminder/main.go


# Final Stage: Dkron Image
FROM dkron/dkron:latest

# Copy binary from builder
COPY --from=builder /app/dkron-executor-background /usr/local/bin/
COPY --from=builder /app/dkron-executor-reminder /usr/local/bin/

# Set Permissions
RUN chmod +x /usr/local/bin/dkron-executor-background
RUN chmod +x /usr/local/bin/dkron-executor-reminder

# Install dependencies: curl, docker-cli, redis
RUN apk add --no-cache curl docker-cli redis

# Set Environment Variables
ENV GODEBUG=netdns=go

# Set Entrypoint Command
CMD ["agent", "--server", "--log-level=info", "--http-addr=:18047", "--bootstrap-expect=1"]
