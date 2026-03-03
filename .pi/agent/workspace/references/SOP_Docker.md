# Docker 标准操作程序 (SOP)

本向导用于规范 Agent 在其自身运行环境（Agent 容器）中执行 Docker 相关操作的标准流程。

## 1. 核心原则
- Agent 容器通过挂载 `/var/run/docker.sock` 拥有直接操作宿主机 Docker 引擎的能力。
- Agent 应当直接在终端中调用 `docker` 命令进行镜像检查、管理等操作，无需通过 `swe` 容器（除非涉及复杂的代码克隆与构建流）。

## 2. 常用操作示例

### 2.1 检查镜像清单 (Manifest Inspect)
在需要确认远程镜像支持的架构（如 `amd64` / `arm64`）或元数据时，直接执行：

```bash
docker manifest inspect ghcr.io/ggml-org/llama.cpp:server-cuda
```

### 2.2 拉取远程镜像 (Docker Pull)
在确认镜像架构和版本无误后，执行拉取操作。由于镜像拉取通常是耗时较长的任务，**必须使用后台命令执行模式**进行。

```bash
# 示例：利用 dkron cli 创建一个立即执行的一次性后台任务来拉取镜像
dkron job create --displayname "Pulling llama.cpp server-cuda" --schedule "@at $(date -u +%Y-%m-%dT%H:%M:%SZ)" --command "docker pull ghcr.io/ggml-org/llama.cpp:server-cuda" --executor background
```

执行后，使用 `dkron job logs <job_name> --last` 跟踪进度。

## 3. 注意事项
- **直接调用**: Agent 应意识到自己已经拥有 `docker` CLI，可以直接运行命令。
- **权限说明**: Agent 以 `pi-mono` 用户运行，已加入相关的 docker 权限组。