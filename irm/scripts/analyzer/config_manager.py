import os
import json
import redis
import argparse
import falkordb
from urllib.parse import urlparse

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

    print(f"{'Ticker':<10} | {'Symbol':<15} | {'Provider':<10}")
    print("-" * 45)
    for ticker, data_str in sorted(assets.items()):
        try:
            data = json.loads(data_str)
            symbol = data.get("symbol", "N/A")
            provider = data.get("provider", "yfinance")
            print(f"{ticker:<10} | {symbol:<15} | {provider:<10}")
        except Exception:
            print(f"{ticker:<10} | Error parsing data: {data_str}")

def update_source(ticker, symbol, provider):
    r = get_redis_client()
    data = {
        "symbol": symbol,
        "provider": provider
    }
    r.hset("irm:config:sources", ticker, json.dumps(data))
    print(f"Successfully updated source {ticker}: {symbol} via {provider}")

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
    update_sources_parser.add_argument("provider", choices=["yfinance", "fred"], help="Data provider")

    args = parser.parse_args()

    if args.command == "sources":
        if args.subcommand == "ls":
            list_sources()
        elif args.subcommand == "update":
            update_source(args.ticker, args.symbol, args.provider)
        else:
            print("Usage: irm sources {ls,update}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
