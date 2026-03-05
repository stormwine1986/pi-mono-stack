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
    - **数据协议**: 参考 [协议文档](../Protocol.md)
- **Dkron (调度器)**: 
    - Gateway 负责注册回收作业 (`gateway-recovery`) 以确保系统健壮性。
    - 监听 Dkron 推送的 Webhook 或任务状态变化，转发给特定的 Telegram 管理员或用户。
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
