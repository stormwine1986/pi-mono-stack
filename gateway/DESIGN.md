# Gateway 模块概要设计 (Outline Design)

`gateway` 模块是 `pi-mono-stack` 系统中的接入层，主要功能是作为 Telegram Bot 的网关，负责与外部用户的交互以及内部消息流的串联。

## 1. 模块用途 (Purpose)

Gateway 模块的核心职责包括：
- **用户接入**：通过 Telegram Bot 接收用户的文本消息、图片及交互指令（如 `/new`, `/stop`）。
- **消息代理**：将用户请求封装并推送到 Redis 消息队列中，供后端 Agent 或其他微服务消费。
- **响应推送**：实时监听 Redis 结果队列，将后端处理完成的结果（推文、分析报告、状态更新等）反馈给用户。
- **任务调度集成**：与 Dkron 配合，执行定时恢复任务，并向用户推送任务提醒或执行状态。

## 2. 与其他模块的关系 (Relationships)

Gateway 在系统中处于边缘位置，起着承上启下的作用：

- **Telegram (外部接口)**: 直接与用户交互的唯一入口。
- **Redis (通信枢纽)**:
    - **上行流 (Request)**: 
        - `agent_in` (Redis Stream): 用户任务请求（文本、图片）。
        - `agent_ctl` (Redis Pub/Sub): 实时控制指令转发（如 `/stop`, `/new`, `/steer`）。
    - **下行流 (Response/Notice)**: 
        - `agent_out` (Redis Stream): Agent 处理结果。
        - `background_out` (Redis Stream): 后台任务执行结果通知（由 Summary Listener 接管进行 AI 摘要）。
        - `summary_out` (Redis Stream): 大模型生成后的后台任务摘要结果（JSON）。
        - `reminder_out` (Redis Stream): 提醒事项通知（来自 Dkron）。
    - **运维流 (Admin)**: 
        - `gateway_ctl` (Redis Stream): 接收系统级运维指令（如由 Dkron 定期触发的 `RECOVER_PENDING`）。
    - **数据协议**: 参考本文件结尾的协议规范。
- **Dkron (调度器)**: 
    - **作业管理**: Gateway 负责在系统启动时自动向 Dkron 注册并同步其自身的业务管理作业：
        - `gateway-recovery`: 定期触发挂起任务的恢复逻辑。
        - `gateway-temp-cleanup`: 定期清理网关生成的临时图片和工作空间文件。
    - **消息分发**: 监听 `reminder_out` 流，将来自 Dkron 的提醒消息转发给特定的 Telegram 管理员或用户。
- **Agent (业务核心)**: Gateway 与 Agent 不直接通信，而是通过 Redis 异步解耦。
- **Llama Server (本地模型)**: 为 Summary Listener 提供推理支持，用于将复杂的 Dkron 执行日志总结为 100 字以内的精简摘要。

## 3. 目录结构 (Directory Structure)

```text
gateway/
├── Dockerfile           # 容器镜像构建文件
├── package.json         # Node.js 项目配置及依赖管理
├── tsconfig.json        # TypeScript 编译配置
├── entrypoint.sh        # 容器运行时初始化脚本
└── src/                 # 源代码目录
    ├── index.ts         # 应用主入口，负责 Bot 初始化、服务注删与监听器启动
    ├── config.ts        # 全局配置管理（环境变量映射）
    ├── summary.ts       # 摘要监听器，利用边缘 AI 对 background_out 进行处理。生成摘要后会写入 summary_out 流，并同步推送到 TG。
    ├── logger.ts        # 基于 Winston 或类似的日志记录工具
    ├── types.ts         # 全局类型定义（消息格式、接口定义）
    ├── telegram/        # Telegram 业务层
    │   ├── handlers.ts  # 指令处理器（/start, /help 等）
    │   ├── listener.ts  # 结果监听器，通过 Redis 订阅将消息推回 TG
    │   └── sender.ts    # 消息发送封装类，支持 Markdown、HTML 格式
    ├── web/             # 测试 Web UI 与内部 REST API
    │   ├── server.ts    # Express 服务初始化与生命周期管理
    │   ├── routes.ts    # REST API 路由 (消息发送, TG开关, Dkron代理)
    │   ├── sse.ts       # SSE 服务端事件推送 (实时同步消息与记忆审计)
    │   └── public/      # 静态前端资源 (HTML/CSS/JS)
    └── dkron/           # 调度器集成层
        ├── setup.ts     # 系统自启动时自动注册/更新 Dkron Jobs
        ├── reminder.ts  # 处理用户设置的消息提醒逻辑。
```

## 4. 使用的技术栈 (Technology Stack)

- **Runtime**: Node.js (Latest LTS)
- **Language**: TypeScript (Strongly Typed)
- **Bot Framework**: [Telegraf](https://telegraf.js.org/) (基于 Middleware 的 Telegram 框架)
- **Queue/Cache**: [ioredis](https://github.com/luin/ioredis) (高性能 Redis 交互)
- **Execution**: tsx (开发模式直接运行), tsc (生产环境编译)
- **Architecture**: Event-Driven (事件驱动) & Micro-services (微服务架构中的接入网关)
# Gateway 模块数据协议设计 (Data Protocol Design)

本文档概述了 Pi Mono Stack 中 Gateway (网关) 模块的数据协议设计，用于规范各模块间的通信格式。

## 1. 概述 (Overview)

Gateway 模块作为系统对外的唯一接入点，负责外部消息（如 Telegram）的转换、路由以及内部执行结果的回传。

---

## 2. 协议详述 (Protocol Specifications)

### 2.1 Agent 输入流 (`agent_in`)
- **Redis 键名**: `agent_in` (Redis Stream)
- **保留策略**: `MAXLEN ~ 1000` (约保留最新 1000 条)
- **流向**: Gateway -> Agent

代表发送给 Agent 处理的任务或提示词。

**格式 (JSON):**
```json
{
  "id": "string",            // 任务唯一标识 (nanoId)
  "user_id": "string",       // 任务所属用户标识 (如 TG chat id)
  "source": "string",        // 请求来源 ("telegram", "dkron")
  "prompt": "string",        // 用户提示词或命令文本
  "metadata": {              // 来源相关的路由信息
    "telegram": "chatId:messageId",   // 当 source 为 "telegram" 时存在
    "dkron": { ... }                  // 当 source 为 "dkron" 时存在，包含作业执行数据
  }
}
```

### 2.2 Agent 输出流 (`agent_out`)
- **Redis 键名**: `agent_out` (Redis Stream)
- **保留策略**: `MAXLEN ~ 1000`
- **流向**: Agent -> Gateway

代表 Agent 的处理响应或状态更新。

**格式 (JSON):**
```json
{
  "id": "string",            // 对应输入流的任务 ID
  "user_id": "string",       // 对应输入流的用户标识
  "source": "string",        // 对应请求的来源 ("telegram", "dkron")
  "agent_id": "string",      // 执行任务的 Agent 标识
  "status": "success" | "error" | "progress",
  "response": "string",      // 最终文本回复 (仅当 status 为 success 时)
  "error": "string",         // 错误消息 (仅当 status 为 error 时)
  "event": "llm_start" | "llm_end" | "tool_start" | "tool_end" | "send_media",
  "data": { 
    "path": "string",       // 工作区相对路径 (媒体文件)
    "type": "image" | "file" // 媒体类型
  }            // 事件附加数据
}
```

### 2.3 Agent 控制信道 (`agent_ctl`)
- **Redis 键名**: `agent_ctl` (Redis PubSub)
- **流向**: Gateway -> Agent

用于管理 Agent 生命周期或当前操作的实时控制信号。

**格式 (JSON):**
```json
{
  "id": "string",            // (可选) 目标任务 ID
  "user_id": "string",       // 触发控制指令的用户标识
  "source": "string",        // 控制指令来源
  "command": "stop" | "steer" | "reset",
  "message": "string"        // (可选) 具体的指令或补充信息
}
```

### 2.4 后台作业输出结果 (`background_out`)
- **Redis 键名**: `background_out` (Redis Stream)
- **保留策略**: `MAXLEN ~ 1000`
- **流向**: Dkron -> Gateway

由于后台作业（如备份、拉取镜像）通常执行时间较长，其完成事件会推送到此流。
**注意**: Gateway 的 `Summary Listener` 会监听此流，并自动调用 **Llama Server** 获取作业日志并生成 AI 摘要。摘要结果会同步推送到 `summary_out` 流和 Telegram。

**格式 (JSON):** (payload 字段为 JSON 字符串)
```json
{
  "job": "string",           // 作业名称 (如 "pull-llama-cpp")
  "owner": "string",         // 作业负责人标识
  "exit_code": number,       // 退出码 (0 表示成功)
  "timestamp": "ISO-8601"    // 执行时间戳 (UTC)
}
```

### 2.5 提醒事项输出 (`reminder_out`)
- **Redis 键名**: `reminder_out` (Redis Stream)
- **保留策略**: `MAXLEN ~ 1000`
- **流向**: Dkron -> Gateway

代表由调度器触发的实时提醒事件。

**格式 (JSON):** (payload 字段为 JSON 字符串)
```json
{
  "job": "string",           // 作业名称
  "owner": "string",         // 负责人 ID
  "message": "string",       // 提醒的具体内容文本
  "timestamp": "ISO-8601"    // 触发时间
}
```

### 2.6 任务摘要输出 (`summary_out`)
- **Redis 键名**: `summary_out` (Redis Stream)
- **保留策略**: `MAXLEN ~ 1000`
- **流向**: Gateway -> Other Services

代表经 AI 总结后的后台任务执行快照。

**格式 (JSON):** (payload 字段为 JSON 字符串)
```json
{
  "job": "string",           // 作业名称
  "summary": "string",       // 中文 AI 摘要文本
  "timestamp": "ISO-8601"    // 生成时间
}
```

### 2.7 Gateway 运维流 (`gateway_ctl`)
- **Redis 键名**: `gateway_ctl` (Redis Stream)
- **保留策略**: `MAXLEN ~ 100`
- **流向**: Dkron -> Gateway

用于触发 Gateway 模块的自动恢复或维护操作（如定期清理待处理消息）。

**格式 (键值对):**
- `action`: `RECOVER_PENDING` (触发清理/恢复待处理消息)

### 2.8 记忆审计流 (`memory_audit`)
- **Redis 键名**: `memory_audit` (Redis Stream)
- **保留策略**: `MAXLEN ~ 1000`
- **流向**: Memory -> Observer/Gateway

代表记忆子系统（Memory Service）中事实的生命周期变更事件，用于实现原子事实提取过程的可观测性。

**格式 (JSON):** (payload 字段为 JSON 字符串)
```json
{
  "timestamp": "ISO-8601",   // 事件发生时间 (UTC)
  "event": "ADD" | "UPDATE" | "DELETE", // 变更类型
  "user_id": "string",       // 所属用户 ID
  "memory_id": "string",     // 记忆在向量库中的唯一标识
  "fact": "string",          // 提取出的原子事实内容
  "metadata": {              // 溯源元数据
    "agent_id": "string",    // 来源 Agent ID
    "prompt_preview": "string" // 触发此记忆提取的原始 Prompt 预览
  }
}
```
