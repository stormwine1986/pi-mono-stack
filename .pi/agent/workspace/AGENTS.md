# AGENTS.md - Your Workspace

This folder is home. Treat it that way.

## 关于你的系统
你被部署在一个标准的 OCI（容器）环境中。你采用模块化设计，各类功能组件分布在不同的容器中。

## Gateway 子系统
容器名称为 `gateway`，作为系统的中央事件中心，负责集中处理所有事件的摄入、转换、路由和分发，从而确保信息流的一致性和可维护性。

## Agent 子系统
容器名称为 `agent`，托管 `pi-mono` 核心，作为决策、推理、规划以及使用工具达成目标的引擎。
- 必须使用 `date` 命令查询系统的UTC当前时间，禁止随机编造当前时间.答复用户时必须使用用户所在时区的本地时间。用户提及的时间，如没有特别标记，都是用户所在时区的本地时间。
- 必须使用 `media image send <path>` 发送图片，具体用法见 `media -h`。禁止使用 `read` 命令发送图片。
- 拉取Docker镜像相关任务，必须参照 [Docker 标准操作程序](./references/SOP_Docker.md) 进行。

## 计算子系统 Compute Subsystem
管理不同的计算资源配置，为 Agent 系统提供计算支持。核心命令为 `compute`。

## 记忆子系统 Memory Subsystem
记忆子系统负责管理 Agent 的长期记忆，规范记忆的组织与检索方法。

你拥有一个由 Mem0 驱动的对话记忆系统：
- **检索记忆**：使用 `memory search --user_id=<id> <query>` 来检索和当前会话用户相关的历史事实或对话片段。
- **隐私与上下文**：当用户提到过去的交互（例如“正如我们讨论过的”、“你知道我的偏好”）或者你需要跨会话的持久上下文时，请务必检索记忆。

**检索时机 (When to Recall)**：
在回答任何关于过往工作、决策、日期、人物、偏好或待办事项的问题之前：请使用 `memory search --user_id=<id> <query>` 进行搜索。你可以运行 `memory --help` 获取更多帮助。

## 技能子系统 Skill Subsystem
- 规范工具容器的识别和安装，提供工具容器的注册服务。更多信息参见 `references/OVERVIEW.md` 的 `Skills Subsystem` 章节。
- 必须使用 `skill` 命令处理工具容器以及技能子系统相关的任务，具体用法参照 `skill -h`

## 调度子系统 Scheduler Subsystem
- 调度子系统为 Agent 管理所有的后台任务和提醒
- `dkron` 命令提供检查调度子系统和调度计划任务的有用操作，可以通过 `-h` 查看帮助。
- 必须使用调度子系统创建后台任务，需要设置 `--executor background`
- 必须使用调度子系统创建提醒，需要设置 `--executor reminder`。在创建提醒时，对于含相对时间的指令，必须强制使用 `date` 命令获取最新的系统时间。