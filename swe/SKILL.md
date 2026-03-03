---
name: "swe"
description: "软件工程综合技能，支持 GitHub (gh)、Git、Docker 以及 Hugging Face (hf) 的自动化操作、仓库管理与资源下载。"
---

# SWE 技能

此技能通过 `gh` CLI、标准 `git` 操作和 `docker` 能力提供对 GitHub 功能的访问。它专门为代码仓库管理、代码贡献和 CI/CD 任务而设计。

## 能力

- **仓库管理**: 搜索、查看和克隆仓库。
- **Git 操作**: 全面支持 `clone`, `commit`, `pull`, `checkout`, `push`, `fetch` 以及分支管理。
- **Docker 集成**: 使用宿主机的 Docker 守护进程直接从容器内执行 `docker build`。
- **Issue 追踪与 PR 管理**: 列出、查看和管理 GitHub 的 issue 和 pull request。
- **Hugging Face CLI**: 通过 `hf` 命令与 Hugging Face Hub 交互（下载/上传模型、数据集等）。
- **API 访问**: 通过 `gh api` 直接访问 GitHub API。

## 使用方法

此技能通过名为 `swe` 的 Docker 容器执行。
- **工作空间 (Workspace)**: `/home/pi-mono/.pi/agent/workspace` 是工作目录。
- **克隆根目录 (Clone Root)**: `/home/pi-mono/.pi/agent/workspace/.swe` 是所有克隆项目的指定根目录。
- **下载根目录 (Download Root)**: `/home/pi-mono/.pi/agent/workspace/.swe/download` 是所有 Hugging Face 下载内容的**强制**根目录。
- **Docker**: 挂载了宿主机的 `docker.sock`，允许执行 `docker` 命令。

### 参数

- `gh <command>`: GitHub CLI 命令。
- `git <command>`: 标准 git 命令。
- `hf <command>`: Hugging Face CLI 命令。
- `docker <command>`: 标准 docker 命令。
- `--repo <owner/repo>`: 建议在 `gh` 命令中使用。

## 示例

### Git Clone
**用户:** "克隆仓库 owner/repo。"
**操作:**
```bash
docker exec swe git clone https://github.com/owner/repo.git /home/pi-mono/.pi/agent/workspace/.swe/repo
```

### Git Checkout 和 Pull
**用户:** "切换到 'develop' 分支并拉取 'repo' 的最新更改。"
**操作:**
```bash
docker exec swe bash -c "cd /home/pi-mono/.pi/agent/workspace/.swe/repo && git checkout develop && git pull origin develop"
```

### Git Commit 和 Push
**用户:** "提交所有更改并推送到 'repo' 的 main 分支。"
**操作:**
```bash
docker exec swe bash -c "cd /home/pi-mono/.pi/agent/workspace/.swe/repo && git add . && git commit -m 'feat: update' && git push origin main"
```

### Git Fetch
**用户:** "从 'repo' 的所有分支拉取最新更新。"
**操作:**
```bash
docker exec swe bash -c "cd /home/pi-mono/.pi/agent/workspace/.swe/repo && git fetch --all"
```

### Docker Build
**用户:** "从 'repo' 构建名为 'myapp:latest' 的 docker 镜像。"
**操作:**
```bash
docker exec swe bash -c "cd /home/pi-mono/.pi/agent/workspace/.swe/repo && docker build -t myapp:latest ."
```

### 搜索仓库
**用户:** "在 GitHub 上搜索热门的机器学习仓库。"
**操作:**
```bash
docker exec swe gh repo search "machine learning" --sort stars --limit 5
```

### 查看仓库 README
**用户:** "显示 google/gemini-cli 仓库的 README。"
**操作:**
```bash
docker exec swe gh repo view google/gemini-cli
```

### 列出 Issue
**用户:** "owner/repo 仓库中有哪些未解决的 issue？"
**操作:**
```bash
docker exec swe gh issue list --repo owner/repo
```

### 查看 Pull Request
**用户:** "显示 owner/repo 中 PR #123 的详情。"
**操作:**
```bash
docker exec swe gh pr view 123 --repo owner/repo
```

### API 查询
**用户:** "获取 owner/repo 的最新版本信息。"
**操作:**
```bash
docker exec swe gh api repos/owner/repo/releases/latest --jq '.tag_name'
```

### Hugging Face 下载
**用户:** "下载 unsloth/Qwen3.5-9B-GGUF Q5_K_M。"
**操作:**
```bash
docker exec swe hf download unsloth/Qwen3.5-9B-GGUF Q5_K_M.gguf --local-dir /home/pi-mono/.pi/agent/workspace/.swe/download
```
