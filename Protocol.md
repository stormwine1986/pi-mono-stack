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
**注意**: Gateway 的 `Summary Listener` 会监听此流，并自动调用 **Llama Server** 获取作业日志并生成 AI 摘要推送给管理员。

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

### 2.6 Gateway 运维流 (`gateway_ctl`)
- **Redis 键名**: `gateway_ctl` (Redis Stream)
- **保留策略**: `MAXLEN ~ 100`
- **流向**: Dkron -> Gateway

用于触发 Gateway 模块的自动恢复或维护操作（如定期清理待处理消息）。

**格式 (键值对):**
- `action`: `RECOVER_PENDING` (触发清理/恢复待处理消息)

### 2.7 记忆审计流 (`memory_audit`)
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
