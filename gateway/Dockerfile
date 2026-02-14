# Build stage
FROM node:20-slim AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install all dependencies
RUN npm install

# Copy source code and config
COPY tsconfig.json ./
COPY src ./src

# Build TypeScript to JS
RUN npm run build

# Runtime stage
FROM node:20-slim AS runner

WORKDIR /app

ENV NODE_ENV=production

# Copy package files
COPY package*.json ./

# Install only production dependencies
RUN npm install --omit=dev

# Copy built files from builder
COPY --from=builder /app/dist ./dist

# Start the application
CMD ["npm", "start"]
