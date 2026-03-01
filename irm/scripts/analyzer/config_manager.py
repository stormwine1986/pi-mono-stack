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

def list_pe_bands():
    graph = get_falkordb_graph()
    cypher = "MATCH (h:Hub:Valuation) RETURN h.target, h.pe_min, h.pe_max ORDER BY h.target"
    result = graph.query(cypher)
    
    if not result.result_set:
        print("No PE bands found in Ontology Graph.")
        return

    print(f"{'Ticker':<10} | {'Min PE':<10} | {'Max PE':<10} | {'Source':<10}")
    print("-" * 50)
    for row in result.result_set:
        ticker = row[0]
        min_pe = row[1] if row[1] is not None else "N/A"
        max_pe = row[2] if row[2] is not None else "N/A"
        print(f"{ticker:<10} | {min_pe:<10} | {max_pe:<10} | Graph Node")

def update_pe_band(ticker, min_pe, max_pe):
    graph = get_falkordb_graph()
    cypher = f"MATCH (h:Hub:Valuation) WHERE h.target = '{ticker}' SET h.pe_min = {min_pe}, h.pe_max = {max_pe} RETURN h"
    result = graph.query(cypher)
    
    if not result.result_set:
        # 如果节点不存在，尝试创建或者提示错误。通常应该是先有本体结构。
        print(f"Error: No Hub:Valuation node found for ticker {ticker}. Please sync schema first.")
        return

    print(f"Successfully updated Graph PE band for {ticker}: [{min_pe}, {max_pe}]")

def list_eps_bands():
    graph = get_falkordb_graph()
    cypher = "MATCH (h:Hub:Earnings) RETURN h.target, h.eps_min, h.eps_max ORDER BY h.target"
    result = graph.query(cypher)
    
    if not result.result_set:
        print("No EPS growth bands found in Ontology Graph.")
        return

    print(f"{'Ticker':<10} | {'Min Growth':<12} | {'Max Growth':<12} | {'Source':<12}")
    print("-" * 55)
    for row in result.result_set:
        ticker = row[0]
        min_g = row[1] if row[1] is not None else "N/A"
        max_g = row[2] if row[2] is not None else "N/A"
        print(f"{ticker:<10} | {min_g:<12} | {max_g:<12} | Graph Node")

def update_eps_band(ticker, min_growth, max_growth):
    graph = get_falkordb_graph()
    cypher = f"MATCH (h:Hub:Earnings) WHERE h.target = '{ticker}' SET h.eps_min = {min_growth}, h.eps_max = {max_growth} RETURN h"
    result = graph.query(cypher)

    if not result.result_set:
        print(f"Error: No Hub:Earnings node found for ticker {ticker}. Please sync schema first.")
        return

    print(f"Successfully updated Graph EPS growth band for {ticker}: [{min_growth}, {max_growth}]")

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
