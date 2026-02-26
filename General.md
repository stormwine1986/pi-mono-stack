# Pi Mono Stack 概要设计 (General Design)

本文档描述了 Pi Mono Stack 的整体架构、模块职责、关键配置文件以及各模块之间的交互关系。

## 一、 系统架构概览

Pi Mono Stack 是一个基于容器化微服务架构的 AI Agent 系统。它通过 Redis 作为消息总线，将与用户的交互（Gateway）、后台任务调度（Dkron）、大语言模型代理（LiteLLM）、核心大脑引擎（Agent）以及多种外围工具（Tools）进行解耦和连接。整个系统由 `docker-compose.yml` 统一部署，并通过 `stack-ctl.sh` 脚本配合 `pass` 密码管理器进行安全的密钥注入与生命周期管理。

架构设计遵循“事件驱动”与“微服务”的哲学，核心 Agent 仅需关注任务处理，其余的路由、记忆、能力扩展（技能）均交由独立的微服务来完成。

---

## 二、 核心模块职责说明

### 1. 核心与平台服务
*   **Agent (`pi-mono-agent`)**
    *   **职责**：系统的“大脑”与执行引擎。它负责接收来自用户的 Prompt 或者自动化任务信号，调用大模型生成回复、执行各种工具操作，并将执行过程与结果发回给消息总线。
    *   **角色**：后台 Worker，订阅特定的消息队列来消化任务。
*   **Gateway (`pi-mono-stack-gateway`)**
    *   **职责**：通信网关，目前主要实现为 Telegram Bot。它负责监听 Telegram 用户的输入（消息、图片、控制命令），并将其转换为内部标准协议（JSON），然后推送到 Redis 流中。同时，它也负责监听 Agent 执行的结果或进度并推送回 Telegram 中对应的用户。
*   **Redis**
    *   **职责**：消息总线与状态存储。
    *   **作用**：作为 Gateway、Agent、Dkron 之间的异步消息流（Stream）、发布订阅（Pub/Sub）通道的核心组件，同时也是 Dkron 任务调度器的数据后端。
*   **LiteLLM (`litellm`)**
    *   **职责**：大模型 API 统一代理与可观测性网关。
    *   **作用**：将内部系统发送的模型请求，按路由规则分发给各种不同的模型供应商（如 Gemini, OpenRouter 的 Kimi/Minimax 等），并使用 Langfuse 处理追踪（Tracing）和分析，对内部 Agent 暴露统一的 API 端点。
*   **Dkron (`dkron`)**
    *   **职责**：分布式任务调度平台（Cron Job Scheduler）。
    *   **作用**：配置并触发各种定时任务和自动化剧本（如系统自修复触发、特定脚本执行、定时提醒等），其执行结果及通知可以通过 Redis 传输给 Gateway 并通知用户。

### 2. 长程记忆与检索服务
*   **Memsearch (`memsearch`)**
    *   **职责**：记忆搜索引擎（Vector DB Agent）。
    *   **作用**：使用 Milvus 维护向量数据库，并使用 Voyage 提供的 Embedding 能力将大量上下文或历史片段转化为向量。当需要记忆检索或上下文回溯时，Agent 能够通过它搜索过去存储的信息。它同时还能调用内部 LLM 来进行记忆压缩。

### 3. 工具 / 技能 (Tools / Skills) 服务
这些模块通常被标记为 `role: Tools`，多数封装为 API 微服务或通过特定的运行时环境供 Agent 调用：
*   **browser-use**：接管浏览器实现各种网页自动化交互与网络抓取操作的引擎。
*   **tavily**：高质高效的搜索引擎，针对生成式 AI 优化，提供实时的网络信息检索与总结。
*   **github**：代码库管理工具，允许 Agent 操作 GitHub（抓取 Issue、提交 PR 等）。
*   **tradingview & polymarket**：金融与预测市场数据获取/交互分析工具。
*   **twitter**：Twitter API 交互模块，支持 Agent 发布推文与进行社交监听。
*   **wikipedia**：对 Wiki 词条进行查阅和信息获取的外部技能。

---

## 三、 关键配置文件

1.  **`docker-compose.yml`**
    *   **位置**：根目录。
    *   **作用**：定义了所有容器服务的网络（以 `host` 模式为主提升内网通讯效率及穿透需求）、环境变量映射、持久化卷映射（主要是 `.pi` 目录与 `docker.sock`），确立了组件的物理拓扑。
2.  **`stack-ctl.sh`**
    *   **位置**：根目录。
    *   **作用**：系统的控制脚本。负责在启动整个栈时（`./stack-ctl.sh up`）从 macOS/Linux 的 `pass` 工具中安全提取各种 API Key（如 `GEMINI_API_KEY`, `TELEGRAM_TOKEN`），并将其作为环境变量注入到相应的容器中去，避免密钥在代码或明文配置中泄露。同时也提供 `build`, `down`, `logs`, `backup` 等操作。
3.  **`.pi/agent/litellm.config.yaml`**
    *   **位置**：用户挂载的 `.pi/agent` 配置目录。
    *   **作用**：LiteLLM 路由配置文件。
    *   **详情**：定义了系统中允许使用哪些前端指定的 `model_name`（如 `gemini-3-flash-preview`, `kimi-k2.5`），它们如何映射到底层提供商（Google, OpenRouter），要使用哪个密钥字段（通过系统环境变量读取），并定义了可观测性追踪的回调流（如 `langfuse_otel`）。
4.  **`.pi/agent/memsearch.config.toml`**
    *   **位置**：用户挂载的 `.pi/agent` 配置目录。
    *   **作用**：配置向量记忆检索器的工作参数。
    *   **详情**：包括 Milvus 数据库的本地存放路径、向量化（Embedding）所采用的平台及模型（如 `voyage-4`），以及 chunking（文本切片）的约束条件和压缩（Compact）使用的模型配置。
5.  **`Protocol.md`**
    *   **位置**：根目录。
    *   **作用**：定义了各个模块跨 Redis 通讯时约定的数据格式（JSON），如 `agent_in` (入口任务)、`agent_out` (出口响应)、`agent_ctl` (控制信号，用于重置、停止与 Steer)、以及 Dkron 输出流的契约结构。

---

## 四、 模块间的交互关系

整个系统的工作流依赖于各服务的松耦合协同运作。以下是核心链路的典型交互：

### 1. 用户会话请求流程 (User Interaction Workflow)
1.  **用户** 在 Telegram 向 Bot 发送消息（例如："今天的天气，并通过 Twitter 发送一下"）。
2.  **Gateway** 接收到请求，进行鉴权，并将其包装为符合标准的 JSON 对象，带有唯一 `taskId` 和 `source: "telegram"`。
3.  **Gateway** 将该请求写入 Redis 的任务流（`agent_in`），并可能会发送 Typing 标记给用户。
4.  **Agent** 处于 Block 读取状态，监听到流中的新任务，开始对指令进行解包。
5.  在思考或处理时，**Agent** 如果需要查阅资料或调用工具，它向代理请求大模型服务，此时请求打给 **LiteLLM** 节点（LiteLLM 决定调发给 OpenAI/Gemini 并将延迟、耗费 Token 上报 Langfuse 中）。
6.  **Agent** 根据决策去调用位于网络空间的 **Tavily** 或者 **Twitter** 等工具，获得搜索结果和发送指令。
7.  处理过程中的任何状态（进展、思考事件）以及最后的成果，被 **Agent** 封装进 `progress` / `success` JSON 数据，向 Redis 发布到 `agent_out` 流。
8.  **Gateway** 监听到响应到达，由于记录了 `taskId`，再把结果（文本及图文）用对应的机器人 API 推送回 Telegram 给对应的用户。

### 2. 并行控制命令调度
*   如果用户察觉模型回答错误，可以在 Telegram 键入 `/stop`，`/new` 或 `/steer <引导意见>`。
*   **Gateway** 接收到控制命令后，不写入长任务队 (`agent_in`)，而是通过 Redis **Pub/Sub** 通道（`agent_ctl`）向 Agent 广播状态更迭命令。
*   **Agent** 的内部任务监控子线程捕捉到控制命令，可以立刻执行停止推流（Aborted）、更换提示词（Steer）或者重置内部状态（Reset）。并且 Gateway 发送 `/new` 时会触发 Agent 发回一条带有所用模型基础信息的欢迎提示。

### 3. 定时背景任务触发与自动化
1.  **Dkron** 根据既定的 Cron 表达式到达调度时间。
2.  它开始去执行内置的任务或者是针对特定模块的清理调用（例如检查 Gateway 中的滞留死信数据或者触发 Reminder）。
3.  **Dkron** 的运行情况和输出结果经专门的 Redis 信道写入 `background_out`, `reminder_out` 或是直接发送 `gateway_ctl` 通知（如 `RECOVER_PENDING` 指令）。
4.  **Gateway** 捕获到这些外部调度事件之后，自动将作业的文字报告（或者主动的机器人问询请求）向系统管理员推送。
5.  当有更复杂的上下文查询诉求时，Agent 后台通过 **Memsearch** 的 SDK 查询过去的文档快照或记忆摘要片段，并将新思考后的见解通过 Voyage Embedding 并插入回 Milvus 库中形成循环。
