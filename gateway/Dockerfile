# Build stage
FROM node:20-slim AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./
COPY gateway/package*.json ./gateway/

# Install dependencies
RUN npm install

# Copy source code
COPY gateway ./gateway

# Build gateway
RUN npm run build -w gateway

# Runtime stage
FROM node:20-slim AS runner

WORKDIR /app

ENV NODE_ENV=production

# Copy package files
COPY package*.json ./
COPY gateway/package*.json ./gateway/

# Install only production dependencies
RUN npm install --omit=dev

# Copy built files from builder
COPY --from=builder /app/gateway/dist ./gateway/dist

# Start the application
CMD ["npm", "start", "-w", "gateway"]
