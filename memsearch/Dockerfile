FROM python:3.11-slim

WORKDIR /app

# 安装基础依赖
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 直接从 PyPI 安装 memsearch 及其常用扩展
RUN pip install --no-cache-dir "memsearch" "memsearch[google]" "memsearch[voyage]"

# 创建 pi-mono 用户和组 (1000:1000)
RUN groupadd -g 1000 pi-mono && \
    useradd -u 1000 -g pi-mono -m -s /bin/bash pi-mono

# 复制并设置入口脚本 (由 root 执行)
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# 切换到 pi-mono 用户
USER pi-mono
WORKDIR /home/pi-mono
ENV HOME=/home/pi-mono

# 创建工作区中的数据存储目录 (由 pi-mono 执行)
RUN mkdir -p /home/pi-mono/.memsearch


# 使用 entrypoint 脚本
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
