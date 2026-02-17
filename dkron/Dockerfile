FROM golang:1.21-alpine AS builder

WORKDIR /app

# Copy source code first
COPY wrapper.go .

# Init module and tidy dependencies
# wrapper.go imports redis, so tidy will fetch it
RUN go mod init dkron-wrapper && \
    go mod tidy

# Build the binary
RUN CGO_ENABLED=0 GOOS=linux go build -o dkron-wrapper .


# Final Stage: Dkron Image
FROM dkron/dkron:latest

# Copy binary from builder
COPY --from=builder /app/dkron-wrapper /usr/local/bin/

# Set Permissions
RUN chmod +x /usr/local/bin/dkron-wrapper

# Set Environment Variables
ENV GODEBUG=netdns=go

# Set Entrypoint Command
CMD ["agent", "--server", "--log-level=debug", "--http-addr=:18047", "--bootstrap-expect=1"]
