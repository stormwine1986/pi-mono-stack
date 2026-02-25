# Build stage
FROM node:20-slim AS builder

WORKDIR /app/gateway

# 仅拷贝 gateway 自身的 package 文件，避免根目录 workspaces 干扰
COPY package*.json ./

# 安装依赖（使用 --no-workspaces 确保只处理当前目录）
RUN npm install

# 拷贝源代码和类型定义
COPY src ./src
COPY tsconfig.json ./

# 构建
RUN npm run build

# Runtime stage
FROM node:20-slim AS runner

WORKDIR /app/gateway

ENV NODE_ENV=production

# 拷贝 package 文件
COPY package*.json ./

# 只安装生产依赖
RUN npm install --omit=dev

# 从 builder 阶段拷贝编译后的文件
COPY --from=builder /app/gateway/dist ./dist

# 创建 pi-mono 用户（UID 1000），兼容 node 镜像自带的 node 用户
RUN if ! getent group pi-mono >/dev/null; then \
        if getent group 1000 >/dev/null; then \
            groupmod -n pi-mono $(getent group 1000 | cut -d: -f1); \
        else \
            groupadd -g 1000 pi-mono; \
        fi; \
    fi && \
    if ! getent passwd pi-mono >/dev/null; then \
        if getent passwd 1000 >/dev/null; then \
            usermod -l pi-mono -m -d /home/pi-mono $(getent passwd 1000 | cut -d: -f1); \
        else \
            useradd -u 1000 -g pi-mono -m -s /bin/bash pi-mono; \
        fi; \
    fi

# 确保工作目录权限
RUN chown -R pi-mono:pi-mono /app/gateway

# 拷贝 entrypoint.sh 并赋权
COPY --chmod=755 entrypoint.sh ./entrypoint.sh

USER pi-mono

ENTRYPOINT ["./entrypoint.sh"]

# 启动应用
CMD ["npm", "start"]
