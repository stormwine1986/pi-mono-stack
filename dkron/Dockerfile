FROM golang:1.21-alpine AS builder

WORKDIR /app

# Copy source code first
COPY processor.go .

# Init module and tidy dependencies
# processor.go imports redis, so tidy will fetch it
RUN go mod init processor && \
    go mod tidy

# Build the binary
RUN CGO_ENABLED=0 GOOS=linux go build -o processor .


# Final Stage: Dkron Image
FROM dkron/dkron:latest

# Copy binary from builder
COPY --from=builder /app/processor /usr/local/bin/

# Set Permissions
RUN chmod +x /usr/local/bin/processor

# Install dependencies: curl, docker-cli
RUN apk add --no-cache curl docker-cli

# Set Environment Variables
ENV GODEBUG=netdns=go

# Set Entrypoint Command
CMD ["agent", "--server", "--log-level=info", "--http-addr=:18047", "--bootstrap-expect=1"]
