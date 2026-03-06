import os
import json
import redis
import argparse
import falkordb
import sys
from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import urlparse
import unicodedata

# Ensure /app is in sys.path so 'scripts' package can be found
app_root = str(Path(__file__).resolve().parent.parent.parent)
if app_root not in sys.path:
    sys.path.append(app_root)

from scripts.providers import get_provider, PROVIDER_REGISTRY

def get_display_width(s):
    """Calculate the display width of a string considering wide characters (e.g. Chinese)."""
    width = 0
    for char in s:
        if unicodedata.east_asian_width(char) in ('W', 'F'):
            width += 2
        else:
            width += 1
    return width

def format_cell(s, width, align='left'):
    """Format a cell with specific width, handling wide characters."""
    s = s or "-"
    current_width = 0
    truncated_s = ""
    for char in s:
        w = 2 if unicodedata.east_asian_width(char) in ('W', 'F') else 1
        if current_width + w > width:
            break
        truncated_s += char
        current_width += w
    
    padding = max(0, width - current_width)
    if align == 'left':
        return truncated_s + ' ' * padding
    else:
        return ' ' * padding + truncated_s

def get_redis_client():
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
    parsed = urlparse(redis_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 6379
    return redis.Redis(host=host, port=port, decode_responses=True)

def get_falkordb_graph(graph_name="Graph-001"):
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
    parsed = urlparse(redis_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 6379
    db = falkordb.FalkorDB(host=host, port=port)
    return db.select_graph(graph_name)

def list_sources():
    r = get_redis_client()
    assets = r.hgetall("irm:config:sources")
    
    if not assets:
        print("No data sources configured in Redis.")
        return

    cols = [
        ("Ticker", 10, 'left'),
        ("Name", 20, 'left'),
        ("Symbol", 15, 'left'),
        ("Provider", 15, 'left')
    ]
    
    header = " | ".join(format_cell(c[0], c[1], c[2]) for c in cols)
    print("\n" + header)
    print("-" * (sum(c[1] for c in cols) + 3 * (len(cols) - 1)))

    for ticker, data_str in sorted(assets.items()):
        try:
            data = json.loads(data_str)
            name = data.get("name", "-")
            symbol = data.get("symbol", "N/A")
            provider = data.get("provider", "yfinance")
            
            cells = [
                format_cell(ticker, 10, 'left'),
                format_cell(name, 20, 'left'),
                format_cell(symbol, 15, 'left'),
                format_cell(provider, 15, 'left')
            ]
            print(" | ".join(cells))
        except Exception:
            print(f"{ticker:<10} | Error parsing data: {data_str}")

def update_source(ticker, symbol, provider, name=None):
    r = get_redis_client()
    data = {
        "symbol": symbol,
        "provider": provider
    }
    if name:
        data["name"] = name
    r.hset("irm:config:sources", ticker, json.dumps(data))
    print(f"Successfully updated source {ticker}: {symbol} ({name or ''}) via {provider}")

def delete_source(ticker):
    r = get_redis_client()
    if r.hdel("irm:config:sources", ticker):
        print(f"Successfully deleted source: {ticker}")
    else:
        print(f"Error: Source {ticker} not found.")

def query_source(target_ticker=None):
    r = get_redis_client()
    assets = r.hgetall("irm:config:sources")
    
    if target_ticker:
        if target_ticker not in assets:
            print(f"Error: Ticker {target_ticker} not found in configuration.")
            return
        to_test = {target_ticker: assets[target_ticker]}
    else:
        to_test = assets

    if not to_test:
        print("No sources to query.")
        return

    print(f"\n{'Ticker':<10} | {'Provider':<10} | {'Status':<10} | {'Details'}")

    fred_api_key = os.getenv("FRED_API_KEY")
    start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')

    print(f"\n{'Ticker':<10} | {'Provider':<10} | {'Status':<10} | {'Details'}")
    print("-" * 75)

    for ticker, data_str in sorted(to_test.items()):
        try:
            data = json.loads(data_str)
            symbol = data.get("symbol")
            provider = data.get("provider")
            
            status = "WAIT"
            details = "Unknown"
            
            try:
                # Use the provider registry instead of hardcoded if/else
                provider_inst = get_provider(provider)
                df = provider_inst.fetch(symbol, start_date)
                value_col = provider_inst.get_value_column(df)

                if not df.empty and value_col in df.columns:
                    status = "\033[92mPASS\033[0m"
                    details = f"Value: {df[value_col].iloc[-1]:.2f} ({symbol})"
                else:
                    status = "\033[91mFAIL\033[0m"
                    details = "Empty dataset"
            except Exception as e:
                status = "\033[91mFAIL\033[0m"
                details = str(e).split('\n')[0][:45]
                
            cols = [
                (ticker, 10, 'left'),
                (provider, 12, 'left'),
                (status, 10, 'left'),
                (details, 50, 'left')
            ]
            print(" | ".join(format_cell(c[0], c[1], c[2]) for c in cols))
            
        except Exception as e:
            print(f"{ticker:<10} | {'-':<10} | \033[91mERROR\033[0m | {e}")

    print("-" * 88 + "\n")

def main():
    parser = argparse.ArgumentParser(description="IRM Configuration Manager")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # sources command
    sources_parser = subparsers.add_parser("sources", help="Manage data sources configuration")
    sources_subparsers = sources_parser.add_subparsers(dest="subcommand", help="Sources subcommands")
    sources_subparsers.add_parser("ls", help="List all data sources")
    update_sources_parser = sources_subparsers.add_parser("update", help="Update or create a data source")
    update_sources_parser.add_argument("ticker", help="Asset ticker (e.g. US10Y)")
    update_sources_parser.add_argument("symbol", help="Provider symbol (e.g. ^TNX)")
    update_sources_parser.add_argument("provider", choices=list(PROVIDER_REGISTRY.keys()), help="Data provider")
    update_sources_parser.add_argument("--name", help="Display name for the source (e.g. Chinese name)")
    
    query_sources_parser = sources_subparsers.add_parser("query", help="Query real-time data from sources")
    query_sources_parser.add_argument("ticker", nargs="?", help="Specific ticker to query (optional)")

    delete_sources_parser = sources_subparsers.add_parser("rm", help="Delete a data source")
    delete_sources_parser.add_argument("ticker", help="Asset ticker to remove")

    args = parser.parse_args()

    if args.command == "sources":
        if args.subcommand == "ls":
            list_sources()
        elif args.subcommand == "update":
            update_source(args.ticker, args.symbol, args.provider, args.name)
        elif args.subcommand == "query":
            query_source(args.ticker)
        elif args.subcommand == "rm":
            delete_source(args.ticker)
        else:
            print("Usage: irm sources {ls,update,query,rm}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
