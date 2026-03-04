# 🧠 记忆子系统概要设计 (Memory Subsystem Design)

## 1. 系统概述
记忆子系统（代号 `memory`）负责管理 Agent 的长期对话记忆与事实沉淀。系统从传统的文件检索模式升级为基于 **Mem0 SDK** 的原子级对话记忆系统，支持语义检索、事实自动脱水与多维度隔离。

本系统的设计核心原则是：**数据不出本地、处理过程异步、检索过程主动。**

---

## 2. 核心架构

系统采用“观察者-执行者”模式，与 Agent 主逻辑解耦。

### 2.1 模块构成
1.  **Redis Stream Observer (被动感知层)**：监听 `agent_in` 与 `agent_out` 流。提取完整的“问-答”对，并过滤掉内部（internal）任务。
2.  **Mem0 Worker (异步处理层)**：基于单线程串行处理（Serial Writing），确保本地数据库操作的排他性与稳定性。
3.  **Local AI Engine (推理层)**：
    *   **LLM (18080)**: 用于 Mem0 的 AUDN (Atomic User Dialogue Network) 状态机，负责从对话中提取原子事实。
    *   **Embedding (18081)**: 提供 512 维度的向量化能力，并开启 `--pooling mean` 以兼容 OpenAI 协议。
4.  **Storage (持久化层)**：
    *   **ChromaDB**: 本地持久化向量数据库，在高并发数据卷挂载环境下具有更好的稳定性。
    *   **SQLite**: 存储记忆的变更历史 (History Store)。
5.  **HTTP API & CLI (检索接入层)**：为 Agent 提供主动回溯记忆的接口。

---

## 3. 运行模型与稳定性 (Operational Model)

为了解决本地文件数据库在容器环境下的死锁与竞争问题，系统采用了以下优化方案：
- **Single Process Mode**: 观察者 (Observer) 与 API 服务运行在同一个 Python 进程的不同线程中，共享同一个 Chroma 客户端实例。
- **Serial Worker**: 提取任务通过 `max_workers=1` 的线程池处理，确保写入操作绝对串行。
- **Lazy Loading**: 数据库对象采用懒加载单例模式，仅在第一次需要时初始化。

---

## 4. 数据协议与隔离

记忆搜索与存储均基于以下标识符进行逻辑隔离：
- **`user_id`**: 用户的唯一标识（如 Telegram 用户 ID）。
- **`source_agent_id`**: 记录事实来源的 Agent（注：作为 metadata 存储，不作为 Mem0 提取参数，以确保系统正确进行“用户事实提取”而非“Agent事实提取”）。
- **`source`**: 记录消息物理来源（如 `telegram`, `dkron`）。

### 3.1 向量维度
系统统一采用 **512 维度**，与本地嵌入模型 `qwen3_embedding_4b` 的输出对齐。

---

## 4. 关键交互流程

### 4.1 记忆的自动存入 (Dehydration)
1.  **采集**: Observer 缓存 `agent_in` 中的 Prompt。
2.  **触发**: 当 `agent_out` 出现 `status: success` 时，获取 Response。
3.  **提取**: 将 Prompt + Response 发给本地 LLM 转换为原子事实（如 "用户喜欢喝不加糖的拿铁"）。
4.  **存储**: 事实被向量化并存入 ChromaDB，同时在 SQLite 记录一条 `ADD` 日志。

### 4.2 记忆的主动检索 (Retrieval)
1.  **决策**: Agent 在思考阶段发现需要背景信息。
2.  **调用**: Agent 执行 CLI 命令 `memory search --user_id=... "关键词"`。
3.  **响应**: CLI 通过 HTTP 请求 `memory` 服务的 `/search`接口，返回 Top-K 相关事实。
4.  **利用**: Agent 将事实融入上下文中生成更精准的回复。

---

## 5. 接口契约 (API Contract)

### 5.1 HTTP 服务 (Port: 18090)
- `POST /search`: 语义检索记忆。
    - 入参: `{ query: string, user_id: string, agent_id?: string, limit?: number }`
- `GET /memories`: 按用户拉取全量记忆列表。
    - 入参: `?user_id=xxx`

### 5.2 CLI 工具 (`/home/pi-mono/.pi/agent/bin/memory`)
- `memory search --user_id=7722403902 "我的咖啡偏好"`
- `memory list --user_id=7722403902`

---

## 6. 环境依赖
- **镜像**: `pi-mono-stack-memory:latest` (Python 3.11-slim)
- **核心包**: `mem0ai`, `chromadb`, `fastapi`, `redis`
- **挂载卷**: `.pi/agent/workspace/.memory` -> `/data` (存储数据库文件)
- **网络**: 必须能访问 Redis、llama-server (18080) 和 llama-embedding (18081)
