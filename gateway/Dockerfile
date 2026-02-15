# Build stage
FROM node:20-slim AS builder

WORKDIR /app

# Copy root package files and workspace packages
COPY package*.json ./
COPY gateway/package*.json ./gateway/
COPY protocol/package*.json ./protocol/

# Install dependencies for all workspaces
RUN npm install

# Copy source code
COPY protocol ./protocol
COPY gateway ./gateway

# Build protocol first, then gateway
RUN npm run build -w protocol
RUN npm run build -w gateway

# Runtime stage
FROM node:20-slim AS runner

WORKDIR /app

ENV NODE_ENV=production

# Copy root package files and production deps
COPY package*.json ./
COPY gateway/package*.json ./gateway/
COPY protocol/package*.json ./protocol/

# Install only production dependencies
RUN npm install --omit=dev

# Copy built files from builder
COPY --from=builder /app/protocol/dist ./protocol/dist
COPY --from=builder /app/gateway/dist ./gateway/dist

# Start the application
CMD ["npm", "start", "-w", "gateway"]
