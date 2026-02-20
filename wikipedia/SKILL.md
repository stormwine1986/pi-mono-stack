---
name: wikipedia
description: Access Wikipedia and Wikidata to search for articles, entities, and structured data. Use this skill for general knowledge, factual verification, and deep data retrieval.
---

# Wikipedia & Wikidata Skill

This skill provides a combined interface to access both **Wikipedia** (for prose/summaries) and **Wikidata** (for structured data and SPARQL queries).

## Execution

All commands are executed via the `wikipedia` Docker container.

```bash
docker exec wikipedia python3 /app/scripts/<script_name> <command> <input>
```

---

## 📚 Wikipedia

Access Wikipedia to search for articles and read summaries.

### Usage
```bash
docker exec wikipedia python3 /app/scripts/query_wikipedia.py <command> <input>
```

**Commands:**
- `search`: Search for articles matching a query. Returns a list of titles and snippets.
- `page`: Retrieve a summary (lead section) of a specific page by title in Markdown.
- `fullpage`: Retrieve the full content of a specific page by title in Markdown.

**Examples:**
- **Search:** `docker exec wikipedia python3 /app/scripts/query_wikipedia.py search "Large language model"`
- **Summary:** `docker exec wikipedia python3 /app/scripts/query_wikipedia.py page "Large language model"`

---

## 📊 Wikidata

Access Wikidata to search for entities and properties, retrieve structured data, and execute SPARQL queries.

### Usage
```bash
docker exec wikipedia python3 /app/scripts/query_wikidata.py <command> <input>
```

**Commands:**
- `search`: Search for entities (items).
- `property`: Search for property codes (PIDs).
- `get <QID> [PID]`: Retrieve entity summary OR specific property values if PID is provided.
- `sparql`: Execute a SPARQL query.

**Common Property Mapping:**

| Property Name | PID | Description |
| :--- | :--- | :--- |
| **Instance of** | `P31` | Nature of the entity (e.g., human, city, film) |
| **Date of Birth** | `P569` | Date on which the subject was born |
| **Occupation** | `P106` | Main profession or work |
| **Official Website**| `P856` | URL of the official website of an item |

**Examples:**
- **Search for "Birthday" property:** `docker exec wikipedia python3 /app/scripts/query_wikidata.py property "Birthday"`
- **Get Date of Birth (P569) for Douglas Adams (Q42):** `docker exec wikipedia python3 /app/scripts/query_wikidata.py get Q42 P569`

---

## 🛠 Workflow Recommendations

1.  **Start with Search**: Unless you know the exact Title or QID, always use the `search` command first.
2.  **Breadcrumbs**: Use Wikipedia for context and general reading, then switch to Wikidata if you need specific, machine-readable facts (like coordinates, dates, or identifiers).
3.  **SPARQL**: Use the `sparql` command for complex queries (e.g., "List all cities in Japan with a population over 1 million").