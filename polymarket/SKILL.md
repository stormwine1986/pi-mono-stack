---
name: "polymarket"
description: "Access Polymarket Gamma API to query prediction markets, search by keyword, and get detailed market metadata and prices."
---

# Polymarket Skill

This skill provides access to the Polymarket Gamma API, allowing agents to query markets, search for specific prediction markets, and get detailed information about them.

## Capabilities

- **List Markets**: Browse the most popular active markets.
- **Search Markets**: Find specific markets by keyword.
- **Get Market**: Retrieve full metadata for a single market by ID.

## Usage

The tool MUST be executed within the `polymarket` container using `docker exec`:

```bash
docker exec polymarket gamma_tool <action> [options]
# OR if calling via python directly
docker exec polymarket python3 /app/scripts/gamma_tool.py <action> [options]
```

### Common Commands

```bash
# List top 10 active markets by volume
docker exec polymarket gamma_tool list --limit 10

# Search for "Bitcoin" markets
docker exec polymarket gamma_tool search "Bitcoin" --limit 5

# Get full details for a specific market
docker exec polymarket gamma_tool get 517310
```

### Available Options

Only the following option is available for `list` and `search` commands:

| Option | Description | Default |
| :--- | :--- | :--- |
| `--limit <num>` | Maximum number of markets to return. | 10 |

**Note**: To keep results clean and highly relevant, `list` and `search` commands are hardcoded to **only** return active, unclosed markets. Results are always sorted by **trading volume in descending order**, and only return a default set of essential fields.

## Examples
**Find top "Trump" markets:**
```bash
docker exec polymarket gamma_tool search "Trump" --limit 5
```

**List the top 20 most traded active markets:**
```bash
docker exec polymarket gamma_tool list --limit 20
```

## Response Fields
By default, `list` and `search` return a curated set of common fields. The `get` command returns all available metadata for a specific market.

| Field | Description |
| :--- | :--- |
| `id` | Unique identifier for the market. |
| `question` | The prediction question (e.g., "Will Bitcoin hit $100k?"). |
| `outcomes` | JSON string of possible results (e.g., `["Yes", "No"]`). |
| `outcomePrices` | JSON string of current prices/odds (e.g., `["0.65", "0.35"]`). |
| `volume` | Total lifetime trading volume. |
| `liquidity` | Current available liquidity. |
| `description` | Detailed rules and resolution criteria for the market. |
| `endDate` | ISO timestamp when the market resolves. |