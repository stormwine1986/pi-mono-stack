#!/usr/bin/env python3
import argparse
import json
import sys
import os


DEFAULT_FIELDS = [
    "id", 
    "question", 
    "description",
    "outcomes", 
    "outcomePrices", 
    "volume", 
    "liquidity", 
    "endDate",
    "active"
]

def filter_fields(market_data):
    if market_data is None:
        return market_data
    if isinstance(market_data, list):
        return [{k: v for k, v in m.items() if k in DEFAULT_FIELDS} for m in market_data]
    else:
        return {k: v for k, v in market_data.items() if k in DEFAULT_FIELDS}


def list_markets(args):
    print(f"Fetching markets (limit {args.limit}, sort volume desc)...", file=sys.stderr)
    try:
        import httpx
        url = "https://gamma-api.polymarket.com/markets"
        params = {
            "active": "true",
            "closed": "false",
            "archived": "false",
            "order": "volumeNum",
            "ascending": "false",
            "limit": args.limit
        }
        resp = httpx.get(url, params=params)
        resp.raise_for_status()
        markets = resp.json()
        
        filtered = filter_fields(markets)
        print(json.dumps(filtered, indent=2))
    except Exception as e:
        print(f"Error fetching markets: {e}", file=sys.stderr)

def search_markets(args):
    print(f"Searching for '{args.query}' (sort volume desc)...", file=sys.stderr)
    try:
        import httpx
        url = "https://gamma-api.polymarket.com/public-search"
        params = {
            "q": args.query, 
            "active": "true", 
            "closed": "false",
            "order": "volumeNum",
            "ascending": "false"
        }
        resp = httpx.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        
        all_markets = []
        for event in data.get("events", []):
            if "markets" in event:
                for market in event["markets"]:
                    if not market.get("active", False):
                        continue
                    if market.get("closed", False):
                        continue
                    # Convert properties to floats to support numerical sorting
                    raw_vol = market.get("volume", "0")
                    try:
                        market["volumeNum"] = float(raw_vol) if raw_vol is not None else 0.0
                    except (ValueError, TypeError):
                        market["volumeNum"] = 0.0
                    all_markets.append(market)
                    
        # Apply sort by volume descending
        all_markets.sort(key=lambda x: x.get("volumeNum", 0.0), reverse=True)
        
        # Apply limit
        all_markets = all_markets[:args.limit]
        
        final_markets = filter_fields(all_markets)
        print(json.dumps(final_markets, indent=2))
    except Exception as e:
        print(f"Error searching markets: {e}", file=sys.stderr)

def get_market(args):
    if not args.target:
        print("Error: Market ID required", file=sys.stderr)
        sys.exit(1)
    import httpx
    url = f"https://gamma-api.polymarket.com/markets/{args.target}"
    try:
        resp = httpx.get(url)
        resp.raise_for_status()
        market = resp.json()
        # 'get' command shows full fields by default
        print(json.dumps(market, indent=2))
    except Exception as e:
        print(f"Error fetching market: {e}", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(
        description="Polymarket Gamma API Tool - Access prediction markets metadata and prices.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  gamma_tool list --limit 20
  gamma_tool search "Bitcoin" --limit 5
  gamma_tool get 517310
"""
    )
    subparsers = parser.add_subparsers(dest="action", required=True, help="Available actions")

    # List action
    list_parser = subparsers.add_parser("list", help="List popular active markets")
    list_parser.description = "List the most popular active and unclosed markets, sorted by trading volume descending."
    list_parser.add_argument("--limit", type=int, default=10, help="Maximum number of markets to return (default: 10)")

    # Get action
    get_parser = subparsers.add_parser("get", help="Get detailed market metadata")
    get_parser.description = "Retrieve full metadata for a specific market using its unique ID."
    get_parser.add_argument("target", help="The unique Market ID (e.g., 517310)")

    # Search action
    search_parser = subparsers.add_parser("search", help="Search markets by keyword")
    search_parser.description = "Find active and unclosed markets matching a keyword, sorted by trading volume descending."
    search_parser.add_argument("target", help="The search query or keyword (e.g., 'Bitcoin')")
    search_parser.add_argument("--limit", type=int, default=10, help="Maximum number of markets to return (default: 10)")

    args = parser.parse_args()

    if args.action == "list":
        list_markets(args)
    elif args.action == "get":
        get_market(args)
    elif args.action == "search":
        args.query = args.target
        search_markets(args)

if __name__ == "__main__":
    main()