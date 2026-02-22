# Build stage
FROM node:20-slim AS builder

WORKDIR /app/gateway

# 仅拷贝 gateway 自身的 package 文件，避免根目录 workspaces 干扰
COPY gateway/package*.json ./

# 安装依赖（使用 --no-workspaces 确保只处理当前目录）
RUN npm install

# 拷贝源代码和类型定义
COPY gateway/src ./src
COPY gateway/tsconfig.json ./

# 构建
RUN npm run build

# Runtime stage
FROM node:20-slim AS runner

WORKDIR /app/gateway

ENV NODE_ENV=production

# 拷贝 package 文件
COPY gateway/package*.json ./

# 只安装生产依赖
RUN npm install --omit=dev

# 从 builder 阶段拷贝编译后的文件
COPY --from=builder /app/gateway/dist ./dist

# 启动应用
CMD ["npm", "start"]
