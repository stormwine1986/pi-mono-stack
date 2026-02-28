# SOP-001: 工作区备份任务操作规范

## 1. 概述

**文档编号:** SOP-001  
**生效日期:** 2026-02-25  
**版本:** 1.0  
**适用范围:** Agent Workspace 数据备份  

## 2. 目的

规范通过调度子系统（Dkron）创建工作区 S3 备份任务的标准流程，确保数据备份的可靠性和可追溯性。

## 3. 前提条件

- 调度子系统（Dkron）运行正常
- Agent 容器（agent）运行正常
- Agent 容器已配置 S3 访问密钥

## 4. 容器信息

| 组件 | 容器名 | 功能 |
|------|--------|------|
| 调度器 | `dkron` | 任务调度与触发 |
| 执行器 | `agent` | 执行 `s3 backup` 命令 |

## 5. 操作流程

### 5.1 创建手动备份任务

创建仅支持手动触发的备份任务：

```bash
dkron job create \
  --displayname "Workspace S3 Backup" \
  --schedule "@manually" \
  --command "docker exec agent s3 backup" \
  --executor background
```

**参数说明：**
- `--schedule "@manually"`：禁用自动触发，仅手动执行
- `--command "docker exec agent s3 backup"`：跨容器调用 agent 的备份命令

### 5.2 立即执行备份

```bash
# 手动触发任务
dkron job run <job-name>

# 示例
dkron job run workspace-s3-backup
```

### 5.3 查看执行结果

```bash
# 查看最新执行日志
dkron job logs <job-name> --last
```

**成功标志：**
```
[S3] Backup completed successfully: workspace_YYYYMMDD_HHMMSS.tar.gz
```

## 6. 创建周期性备份任务（可选）

如需定时自动备份，创建周期性任务：

```bash
# 每天凌晨 2:00 执行
dkron job create \
  --displayname "Daily Workspace Backup" \
  --schedule "0 2 * * *" \
  --command "docker exec agent s3 backup" \
  --executor background
```

**常用调度表达式：**

| 频率 | 调度表达式 |
|------|-----------|
| 每小时 | `0 * * * *` |
| 每天凌晨 2 点 | `0 2 * * *` |
| 每周日 | `0 0 * * 0` |
| 每 6 小时 | `0 */6 * * *` |

## 7. 任务管理

### 7.1 列出所有任务

```bash
dkron job ls --query "backup"
```

### 7.2 删除任务

```bash
dkron job delete <job-name>
```

### 7.3 检查调度系统状态

```bash
dkron status
```

## 8. 故障处理

| 现象 | 可能原因 | 解决方案 |
|------|---------|---------|
| 任务创建失败 | 参数格式错误 | 检查 cron 表达式或命令语法 |
| 备份命令未执行 | Agent 容器名错误 | 确认容器名为 `agent` |
| S3 上传失败 | 密钥配置缺失 | 检查 agent 容器 S3 配置 |
| 日志无输出 | 任务尚未执行 | 确认任务状态并手动触发 |

## 9. 相关命令速查

```bash
# 创建手动任务
dkron job create --displayname "Backup" --schedule "@manually" \
  --command "docker exec agent s3 backup" --executor background

# 创建定时任务
dkron job create --displayname "Daily" --schedule "0 2 * * *" \
  --command "docker exec agent s3 backup" --executor background

# 立即执行
dkron job run <job-name>

# 查看日志
dkron job logs <job-name> --last

# 删除任务
dkron job delete <job-name>

# 列出任务
dkron job ls
```

## 10. 附录

### 10.1 备份文件命名规范

```
workspace_YYYYMMDD_HHMMSS.tar.gz
```

示例：`workspace_20260225_083812.tar.gz`

### 10.2 保留策略

- S3 端自动保留最近 5 个备份
- 旧备份自动清理

---
**维护记录**

| 日期 | 版本 | 修订内容 | 修订人 |
|------|------|---------|--------|
| 2026-02-25 | 1.0 | 初始发布 | Agent Zero |
