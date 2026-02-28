import os
import json
import redis
import argparse
from urllib.parse import urlparse

def get_redis_client():
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
    parsed = urlparse(redis_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 6379
    return redis.Redis(host=host, port=port, decode_responses=True)

def list_pe_bands():
    r = get_redis_client()
    bands = r.hgetall("irm:config:pe_bands")
    
    if not bands:
        print("No PE bands configured in Redis.")
        return

    print(f"{'Ticker':<10} | {'Min PE':<10} | {'Max PE':<10} | {'Metric':<10}")
    print("-" * 50)
    for ticker, data_str in sorted(bands.items()):
        try:
            data = json.loads(data_str)
            min_pe = data.get("min", "N/A")
            max_pe = data.get("max", "N/A")
            metric = data.get("metric", "pe_ratio")
            print(f"{ticker:<10} | {min_pe:<10} | {max_pe:<10} | {metric:<10}")
        except Exception:
            print(f"{ticker:<10} | Error parsing data: {data_str}")

def update_pe_band(ticker, min_pe, max_pe):
    r = get_redis_client()
    data = {
        "min": float(min_pe),
        "max": float(max_pe),
        "metric": "pe_ratio"
    }
    r.hset("irm:config:pe_bands", ticker, json.dumps(data))
    print(f"Successfully updated PE band for {ticker}: [{min_pe}, {max_pe}]")

def list_eps_bands():
    r = get_redis_client()
    bands = r.hgetall("irm:config:eps_bands")
    
    if not bands:
        print("No EPS growth bands configured in Redis.")
        return

    print(f"{'Ticker':<10} | {'Min Growth':<12} | {'Max Growth':<12}")
    print("-" * 40)
    for ticker, data_str in sorted(bands.items()):
        try:
            data = json.loads(data_str)
            min_g = data.get("min", "N/A")
            max_g = data.get("max", "N/A")
            print(f"{ticker:<10} | {min_g:<12} | {max_g:<12}")
        except Exception:
            print(f"{ticker:<10} | Error parsing data: {data_str}")

def update_eps_band(ticker, min_growth, max_growth):
    r = get_redis_client()
    data = {
        "min": float(min_growth),
        "max": float(max_growth),
        "metric": "earnings_growth"
    }
    r.hset("irm:config:eps_bands", ticker, json.dumps(data))
    print(f"Successfully updated EPS growth band for {ticker}: [{min_growth}, {max_growth}]")

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

    # pe-bands command
    pe_parser = subparsers.add_parser("pe-bands", help="Manage PE bands configuration")
    pe_subparsers = pe_parser.add_subparsers(dest="subcommand", help="PE bands subcommands")
    pe_subparsers.add_parser("ls", help="List all PE bands")
    update_pe_parser = pe_subparsers.add_parser("update", help="Update or create a PE band")
    update_pe_parser.add_argument("ticker", help="Asset ticker (e.g. AAPL)")
    update_pe_parser.add_argument("min", type=float, help="Minimum PE value")
    update_pe_parser.add_argument("max", type=float, help="Maximum PE value")

    # sources command
    sources_parser = subparsers.add_parser("sources", help="Manage data sources configuration")
    sources_subparsers = sources_parser.add_subparsers(dest="subcommand", help="Sources subcommands")
    sources_subparsers.add_parser("ls", help="List all data sources")
    update_sources_parser = sources_subparsers.add_parser("update", help="Update or create a data source")
    update_sources_parser.add_argument("ticker", help="Asset ticker (e.g. US10Y)")
    update_sources_parser.add_argument("symbol", help="Provider symbol (e.g. ^TNX)")
    update_sources_parser.add_argument("provider", choices=["yfinance", "fred"], help="Data provider")

    # eps-bands command
    eps_parser = subparsers.add_parser("eps-bands", help="Manage EPS growth bands configuration")
    eps_subparsers = eps_parser.add_subparsers(dest="subcommand", help="EPS bands subcommands")
    eps_subparsers.add_parser("ls", help="List all EPS bands")
    update_eps_parser = eps_subparsers.add_parser("update", help="Update or create an EPS growth band")
    update_eps_parser.add_argument("ticker", help="Asset ticker (e.g. AAPL)")
    update_eps_parser.add_argument("min", type=float, help="Minimum growth value (e.g. 0.05 for 5%)")
    update_eps_parser.add_argument("max", type=float, help="Maximum growth value (e.g. 0.20 for 20%)")

    args = parser.parse_args()

    if args.command == "pe-bands":
        if args.subcommand == "ls":
            list_pe_bands()
        elif args.subcommand == "update":
            update_pe_band(args.ticker, args.min, args.max)
    elif args.command == "sources":
        if args.subcommand == "ls":
            list_sources()
        elif args.subcommand == "update":
            update_source(args.ticker, args.symbol, args.provider)
        else:
            print("Usage: irm sources {ls,update}")
    elif args.command == "eps-bands":
        if args.subcommand == "ls":
            list_eps_bands()
        elif args.subcommand == "update":
            update_eps_band(args.ticker, args.min, args.max)
        else:
            print("Usage: irm eps-bands {ls,update}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
