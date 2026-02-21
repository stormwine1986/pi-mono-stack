---
name: "tavily"
description: "Web search and research tool powered by Tavily. Use when the user asks for real-time information, news, fact-checking, or broad web research."
---

# Tavily Search Skill

This skill allows you to perform optimized web searches using the Tavily API. It is designed to retrieve high-quality, factual information suitable for answering questions about current events, technical documentation, or general knowledge.

## Capabilities

- **Basic Search**: Quick retrieval of relevant web pages.
- **Advanced Search**: Deeper research (configurable via flags).
- **Direct Answers**: Often provides a summarized answer along with sources.

## Usage

This skill can be executed either via a running Docker container.

### Docker Container

Ensure the `tavily` container is running.

```bash
docker exec tavily /app/scripts/tavily_client.py "<query>" [--max <number>] [--depth <basic|advanced>]
```

### Parameters

- `<query>`: The search string. **Always wrap in quotes.**
- `--max`: (Optional) Number of results to return (default: 5).
- `--depth`: (Optional) `basic` for fast results, `advanced` for comprehensive research (slower).

## Examples

**User:** "Who won the Super Bowl in 2024?"
**Action:**
```bash
docker exec tavily /app/scripts/tavily_client.py "Super Bowl 2024 winner"
```

**User:** "Find me recent papers on LLM agents and summarize them."
**Action:**
```bash
docker exec tavily /app/scripts/tavily_client.py "recent research papers on LLM agents" --max 7 --depth advanced
```
