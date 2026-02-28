# AGENTS.md - Your Workspace

This folder is home. Treat it that way.

## About Your System
reference `references/OVERVIEW.md` for more information

## Agent 子系统
- 必须使用 `date` 命令查询系统的UTC当前时间，禁止随机编造当前时间.答复用户时必须使用用户所在时区的本地时间。用户提及的时间，如没有特别标记，都是用户所在时区的本地时间。
- 必须使用 `media image send <path>` 发送图片，具体用法见 `media -h`。禁止使用 `read` 命令发送图片。
- 备份工作区数据，必须参照 [工作区备份标准操作程序](./references/SOP_Workspace_Backup.md) 进行。

## 计算子系统 Compute Subsystem
Manages different compute source configurations, providing compute support for the agent system. The core command is `compute`. 

## 记忆子系统 Memory Subsystem
The Memory Subsystem is responsible for managing the Agent's long-term and short-term memory, standardizing both the organization and recall methods of memory. more information refernece `references/OVERVIEW.md` Chapter `Memory Subsystem`. The core command is `memsearch`. 

**When to Write**:
- Instruction: When the user explicitly instructs to "Remember this".
- Preference: When user preferences or important facts about the user are discovered during the conversation.
- POLICY: When the user prohibits the use of certain tools or specific behaviors.
- Lessons Learned: When new lessons learned or best practices are acquired.

**When to Recall**:
Before answering anything about prior work, decisions, dates, people, preferences, or todos: run `memsearch search <query>` with `bash` to search. you can run `memsearch --help` to get help.

## 技能子系统 Skill Subsystem
- 规范工具容器的识别和安装，提供工具容器的注册服务。更多信息参见 `references/OVERVIEW.md` 的 `Skills Subsystem` 章节。
- 必须使用 `skill` 命令处理工具容器以及技能子系统相关的任务，具体用法参照 `skill -h`

## 调度子系统 Scheduler Subsystem
- 调度子系统为 Agent 管理所有的后台任务和提醒
- `dkron` 命令提供检查调度子系统和调度计划任务的有用操作，可以通过 `-h` 查看帮助。
- 必须使用调度子系统创建后台任务，需要设置 `--executor background`
- 必须使用调度子系统创建提醒，需要设置 `--executor reminder`。在创建提醒时，对于含相对时间的指令，必须强制使用 `date` 命令获取最新的系统时间。

you can get more information from `references/OVERVIEW.md` Chapter `Scheduler Subsystem`