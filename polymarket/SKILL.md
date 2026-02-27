---
name: "polymarket"
description: "Access Polymarket Gamma API to search prediction markets by keyword and get detailed market metadata."
---

# Polymarket Skill

This skill provides access to the Polymarket Gamma API, allowing agents to search for specific prediction markets and get detailed information about them.

## Capabilities

- **Search Markets**: Find specific markets by keyword.
- **Get Market**: Retrieve full metadata for a single market by ID.

## Usage

The tool MUST be executed within the `polymarket` container using `docker exec`:

```bash
docker exec polymarket gamma_tool <action> [options]
```

### Common Commands

```bash
# Search for "Bitcoin" markets
docker exec polymarket gamma_tool search "Bitcoin" --limit 5

# Get full details for a specific market
docker exec polymarket gamma_tool get 517310
```

### Available Options

For the `search` command:

| Option | Description | Default |
| :--- | :--- | :--- |
| `--limit <num>` | Maximum number of markets to return. | 10 |

**Note**: To keep results clean and highly relevant, the `search` command is hardcoded to **only** return active, unclosed markets.
- `search` is sorted by **API relevance** based on the keyword.
- All commands support `-h` or `--help` for detailed usage instructions.

## Examples
**Find top "Trump" markets:**
```bash
docker exec polymarket gamma_tool search "Trump" --limit 5
```

## Response Fields
By default, `search` returns a curated set of common fields. The `get` command returns all available metadata for a specific market.

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