---
name: "github"
description: "Interact with GitHub (gh CLI), Git (clone, commit, pull, checkout, push, fetch), and Docker (docker build). Tips: specify --repo for gh, use /home/pi-mono/.pi/agent/workspace/.github for git operations, and ensure GITHUB_TOKEN is set."
---

# GitHub Skill

This skill provides access to GitHub's features via the `gh` CLI, standard `git` operations, and `docker` capabilities. It is designed for repository management, code contribution, and CI/CD tasks.

## Capabilities

- **Repository Management**: Search, view, and clone repositories.
- **Git Operations**: Full support for `clone`, `commit`, `pull`, `checkout`, `push`, `fetch`, and branch management.
- **Docker Integration**: `docker build` images directly from within the container using the host's Docker daemon.
- **Issue Tracking & PRs**: List, view, and manage GitHub issues and pull requests.
- **API Access**: Direct GitHub API access via `gh api`.

## Usage

This skill is executed via a Docker container named `github`. 
- **Workspace**: `/home/pi-mono/.pi/agent/workspace` is the workspace directory.
- **Clone Root**: `/home/pi-mono/.pi/agent/workspace/.github` is the designated root for all cloned projects. Each project should be cloned into its own subdirectory within this root.
- **Docker**: The host's `docker.sock` is mounted, allowing `docker` commands.

### Parameters

- `gh <command>`: GitHub CLI commands.
- `git <command>`: Standard git commands.
- `docker <command>`: Standard docker commands.
- `--repo <owner/repo>`: Recommended for `gh` commands.

## Examples

### Git Clone
**User:** "Clone the repo owner/repo."
**Action:**
```bash
docker exec github git clone https://github.com/owner/repo.git /home/pi-mono/.pi/agent/workspace/.github/repo
```

### Git Checkout and Pull
**User:** "Switch to the 'develop' branch and pull the latest changes for 'repo'."
**Action:**
```bash
docker exec github bash -c "cd /home/pi-mono/.pi/agent/workspace/.github/repo && git checkout develop && git pull origin develop"
```

### Git Commit and Push
**User:** "Commit all changes and push to main for 'repo'."
**Action:**
```bash
docker exec github bash -c "cd /home/pi-mono/.pi/agent/workspace/.github/repo && git add . && git commit -m 'feat: update' && git push origin main"
```

### Git Fetch
**User:** "Fetch the latest updates from all branches for 'repo'."
**Action:**
```bash
docker exec github bash -c "cd /home/pi-mono/.pi/agent/workspace/.github/repo && git fetch --all"
```

### Docker Build
**User:** "Build a docker image from 'repo' named 'myapp:latest'."
**Action:**
```bash
docker exec github bash -c "cd /home/pi-mono/.pi/agent/workspace/.github/repo && docker build -t myapp:latest ."
```

### Search for Repositories
**User:** "Search for popular machine learning repositories on GitHub."
**Action:**
```bash
docker exec github gh repo search "machine learning" --sort stars --limit 5
```

### View a Repository README
**User:** "Show me the README for the google/gemini-cli repository."
**Action:**
```bash
docker exec github gh repo view google/gemini-cli
```

### List Issues
**User:** "What are the open issues in the owner/repo repository?"
**Action:**
```bash
docker exec github gh issue list --repo owner/repo
```

### View a Pull Request
**User:** "Show details for PR #123 in owner/repo."
**Action:**
```bash
docker exec github gh pr view 123 --repo owner/repo
```

### API Query
**User:** "Get the latest release for owner/repo."
**Action:**
```bash
docker exec github gh api repos/owner/repo/releases/latest --jq '.tag_name'
```