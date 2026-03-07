# Dkron 模块概要设计 (Dkron Module Design)

## 一、 模块概述

Dkron 是 Pi Mono Stack 中的核心任务调度平台。它主要负责管理周期性任务（Cron Jobs）和自动化剧本，作为系统的“定时闹钟”和“背景任务守护进程”。

### 主要用途：
1.  **自动化调度**：配置各种定时执行的 Shell 脚本或后台任务。
2.  **系统监控与自修复**：监控周期性任务状态，发现故障时自动触发提醒（Reminder）。
3.  **任务解耦**：通过 Redis Streams 将任务执行结果异步分发给 `gateway` 或 `agent` 处理。

---

## 二、 技术栈

*   **核心引擎**: [Dkron](https://dkron.io/) (Open source distributed job scheduling system)
*   **开发语言**: Golang (用于自定义 Executor 插件), Shell (用于系统管理和监控脚本)
*   **持久化与消息**: Redis (存储作业元数据及作为结果输出总线)
*   **依赖工具**: `curl`, `jq`, `docker-cli`, `sqlite3` (用于辅助脚本执行)

---

## 三、 目录结构

```text
dkron/
├── Dockerfile              # 基于 dkron/dkron:latest 的多阶段构建镜像
├── go.mod                  # Go 模块定义，用于构建插件
├── scripts/                # 自动化与入口脚本
│   ├── entrypoint.sh       # 容器入口，负责 API 等待及初始任务注册
│   ├── monitor_jobs.sh     # 失败任务监控逻辑（运行在 dkron shell 执行器中）
│   └── cleanup_once_jobs.sh # 已完成非周期任务清理逻辑
└── plugins/                # 自定义 Dkron Executor 插件
    ├── executor-background/ # 背景任务执行器，将 Shell 执行结果推送到 background_out
    └── executor-reminder/   # 提醒执行器，将特定消息推送到 reminder_out
```

---

## 四、 核心机制

### 1. 自定义执行器 (Executors)
Dkron 通过 gRPC 插件扩展其执行能力。本模块提供了两个关键插件：
*   **Background Executor**: 允许执行任意 Shell 命令，并将标准输出实时流式传输给 Dkron，最后将 `exit_code` 封装为 JSON 推送到 Redis `background_out` 流。
*   **Reminder Executor**: 专门用于触发简单的消息提醒，将 payload 推送到 Redis `reminder_out` 流。

### 2. 自动化初始化 (Entrypoint & Job Registration)
容器启动与系统初始化：
1.  Dkron 容器通过 `entrypoint.sh` 启动 agent。
2.  `entrypoint.sh` 在 API 就绪并确认集群就绪后，**自动注册** Dkron 自身的维护任务（`monitor-failed-shell-jobs`, `cleanup-finished-once-jobs`）。其 Owner 设为 `dkron`。
3.  `gateway` 启动时，仅同步注册与其业务相关的核心驱动任务（如 `gateway-recovery`, `gateway-temp-cleanup`）。

### 3. 失败监控逻辑
通过 `monitor_jobs.sh` 脚本，Dkron 每 15 分钟会“自我检查”一次：
*   调用 `/v1/jobs` API 获取所有任务。
*   筛选 `executor == "shell"` 且 `status == "error"` 的任务。
*   发现异常后，立即通过 Redis 向系统管理员发送 Reminder 提醒。

### 4. 任务治理 (Cleanup)
为了防止一次性任务（非周期任务）记录堆积，系统内建了清理机制：
*   **清理脚本**: `cleanup_once_jobs.sh`。
*   **清理逻辑**: 识别 `next` 调度为空且距离最后一次执行（last_success/error）已超过 1 小时的任务。
*   **时间兼容性**: 由于 Dkron 输出的时间戳带有纳秒精度（`.016162228Z`），脚本使用 `jq` 的 `sub` 正则将其归一化为标准秒精度后再进行比较，解决了 `fromdateiso8601` 解析失败的问题。
*   **调度**: 由 Dkron 入口脚本自动注册，每小时执行一次。

---

## 五、 服务交互与依赖

1.  **依赖服务**: 
    *   `redis`: Dkron 必须等待 Redis 启动后才能进行数据持久化和分发消息。
2.  **下游依赖**: 
    *   `agent`, `gateway`, `irm` 等服务均配置为 `condition: service_healthy` 依赖 Dkron。
    *   Dkron 镜像内建了 `/v1/status` 健康检查，确保依赖它的服务在其 API 就绪后再启动。
3.  **消息流向**:
    *   结果流: `bg_out` -> `redis` -> `gateway (Summary Listener + Llama Server)` -> `admin`
    *   监控流: `dkron` -> `monitor_jobs` -> `reminder_out` -> `gateway` -> `admin`
