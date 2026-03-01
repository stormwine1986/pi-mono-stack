import os
import json
import redis
import argparse
import falkordb
from datetime import datetime, timedelta
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

def test_sources(target_ticker=None):
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
        print("No sources to test.")
        return

    print("[*] Initializing OpenBB SDK for testing (this might take a few seconds)...")
    try:
        from openbb import obb
    except ImportError:
        print("Error: OpenBB SDK not found. Cannot perform tests.")
        return

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
                if provider == "yfinance":
                    res = obb.equity.price.historical(symbol=symbol, provider="yfinance", start_date=start_date)
                    df = res.to_dataframe()
                    if not df.empty:
                        status = "\033[92mPASS\033[0m"
                        details = f"Last Value: {df.iloc[-1].iloc[0]:.2f} (from {symbol})"
                    else:
                        status = "\033[91mFAIL\033[0m"
                        details = "Empty dataset returned"
                elif provider == "fred":
                    if not fred_api_key:
                        status = "\033[91mFAIL\033[0m"
                        details = "Missing FRED_API_KEY"
                    else:
                        res = obb.economy.fred_series(symbol=symbol, provider="fred", start_date=start_date, api_key=fred_api_key)
                        df = res.to_dataframe()
                        if not df.empty:
                            status = "\033[92mPASS\033[0m"
                            details = f"Last Value: {df.iloc[-1].iloc[0]:.2f} (from {symbol})"
                        else:
                            status = "\033[91mFAIL\033[0m"
                            details = "Empty dataset returned"
                else:
                    status = "\033[91mFAIL\033[0m"
                    details = f"Unsupported provider: {provider}"
            except Exception as e:
                status = "\033[91mFAIL\033[0m"
                details = str(e).split('\n')[0][:40] # Truncate long error messages
                
            print(f"{ticker:<10} | {provider:<10} | {status:<10} | {details}")
            
        except Exception as e:
            print(f"{ticker:<10} | {'-':<10} | \033[91mERROR\033[0m | {e}")

    print("-" * 75 + "\n")

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
    
    test_sources_parser = sources_subparsers.add_parser("test", help="Test connectivity of data sources")
    test_sources_parser.add_argument("--ticker", help="Optionally test only one ticker")

    args = parser.parse_args()

    if args.command == "sources":
        if args.subcommand == "ls":
            list_sources()
        elif args.subcommand == "update":
            update_source(args.ticker, args.symbol, args.provider)
        elif args.subcommand == "test":
            test_sources(args.ticker)
        else:
            print("Usage: irm sources {ls,update,test}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
