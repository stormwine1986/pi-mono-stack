# Polymarket Skill

This skill provides access to the Polymarket Gamma API, allowing agents to query markets, search for specific prediction markets, and get detailed information about them.

## Capabilities

- **List Markets**: Browse markets with comprehensive filtering and sorting.
- **Search Markets**: Find specific markets by keyword with criteria.
- **Get Market**: Retrieve full metadata for a single market by ID.

## Usage

The tool is executed via the `gamma_tool` command (or `python3 /app/scripts/gamma_tool.py`).

### Common Commands

```bash
# List top 10 active markets by volume
gamma_tool list --limit 10 --sort volume --desc

# Search for "Bitcoin" markets with at least 1M volume
gamma_tool search "Bitcoin" --min-volume 1000000 --sort liquidity --desc

# Get full details for a specific market
gamma_tool get 517310
```

### Available Filters

These filters can be applied to both `list` and `search` commands:

| Filter | Description | Default |
| :--- | :--- | :--- |
| `--active` | Show only active markets. | True |
| `--no-active` | Include inactive markets. | - |
| `--closed` | Include closed markets. | False |
| `--min-volume <num>` | Filter by minimum total volume. | - |
| `--min-liquidity <num>` | Filter by minimum liquidity. | - |
| `--start-date <ISO>` | Markets starting after this date (e.g., 2025-01-01). | - |
| `--end-date <ISO>` | Markets ending before this date. | - |
| `--full` | Show all available JSON fields. | False |

### Sorters

Use `--sort <field>` with `--desc` (descending) or `--asc` (ascending).

| Sorter | Description |
| :--- | :--- |
| `volume` | Sort by total volume (Alias for `volumeNum`). |
| `liquidity` | Sort by current liquidity (Alias for `liquidityNum`). |
| `endDate` | Sort by the market's expiration date. |
| `startDate` | Sort by when the market opened. |
| `updatedAt` | Sort by the last time the market was updated. |

## Examples



**Find high-liquidity active "Trump" markets:**

```bash

gamma_tool search "Trump" --active --min-liquidity 100000 --sort liquidity --desc

```



**List upcoming markets closing soon:**

```bash

gamma_tool list --limit 20 --sort endDate --asc --active

```



## Response Fields







By default, `list` and `search` return a curated set of common fields. `get` returns all metadata by default. Use `--full` with `list` or `search` to see all metadata.







| Field | Description |







| :--- | :--- |





| `id` | Unique identifier for the market. |

| `question` | The prediction question (e.g., "Will Bitcoin hit 
00k?"). |

| `outcomes` | JSON string of possible results (e.g., `["Yes", "No"]`). |

| `outcomePrices` | JSON string of current prices/odds (e.g., `["0.65", "0.35"]`). |

| `volume` | Total lifetime trading volume. |

| `liquidity` | Current available liquidity. |

| `description` | Detailed rules and resolution criteria for the market. |

| `endDate` | ISO timestamp when the market resolves. |


