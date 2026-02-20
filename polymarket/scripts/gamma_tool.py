#!/usr/bin/env python3
import argparse
import json
import sys
import os

# The agents directory is now a package
try:
    from agents.polymarket.gamma import GammaMarketClient
except ImportError as e:
    print(f"Error importing GammaMarketClient: {e}", file=sys.stderr)
    sys.exit(1)

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

def filter_fields(market_data, full=False):
    if full or market_data is None:
        return market_data
    if isinstance(market_data, list):
        return [{k: v for k, v in m.items() if k in DEFAULT_FIELDS} for m in market_data]
    else:
        return {k: v for k, v in market_data.items() if k in DEFAULT_FIELDS}

def build_params(args):
    params = {
        "active": "true" if args.active else "false",
        "closed": "true" if args.closed else "false",
        "archived": "false",
    }
    if args.min_volume:
        params["volume_num_min"] = args.min_volume
    if args.min_liquidity:
        params["liquidity_num_min"] = args.min_liquidity
    if args.start_date:
        params["start_date_min"] = args.start_date
    if args.end_date:
        params["end_date_max"] = args.end_date
    
    sort_field = args.sort
    if sort_field == "volume":
        sort_field = "volumeNum"
    elif sort_field == "liquidity":
        sort_field = "liquidityNum"
    
    params["order"] = sort_field
    params["ascending"] = "false" if args.desc else "true"
    
    return params

def list_markets(args, client):
    print(f"Fetching markets (limit {args.limit}, sort {args.sort})...", file=sys.stderr)
    try:
        params = build_params(args)
        params["limit"] = args.limit
        
        markets = client.get_markets(querystring_params=params)
        filtered = filter_fields(markets, args.full)
        print(json.dumps(filtered, indent=2))
    except Exception as e:
        print(f"Error fetching markets: {e}", file=sys.stderr)

def search_markets(args, client):
    print(f"Searching for '{args.query}' (sort {args.sort})...", file=sys.stderr)
    try:
        params = build_params(args)
        params["query"] = args.query
        params["limit"] = args.limit
        
        markets = client.get_markets(querystring_params=params)
        filtered = filter_fields(markets, args.full)
        print(json.dumps(filtered, indent=2))
    except Exception as e:
        print(f"Error searching markets: {e}", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(description="Polymarket Gamma API Tool")
    parser.add_argument("action", choices=["list", "get", "search"], help="Action to perform")
    parser.add_argument("target", nargs="?", help="Market ID (for get) or Search Query (for search)")
    
    parser.add_argument("--limit", type=int, default=10, help="Number of markets to show")
    parser.add_argument("--sort", type=str, default="volume", help="Field to sort by")
    parser.add_argument("--desc", action="store_true", default=True, help="Sort in descending order")
    parser.add_argument("--asc", action="store_false", dest="desc", help="Sort in ascending order")
    
    parser.add_argument("--active", action="store_true", default=True, help="Only active markets")
    parser.add_argument("--no-active", action="store_false", dest="active")
    parser.add_argument("--closed", action="store_true", default=False)
    parser.add_argument("--min-volume", type=float)
    parser.add_argument("--min-liquidity", type=float)
    parser.add_argument("--start-date", type=str)
    parser.add_argument("--end-date", type=str)
    parser.add_argument("--full", action="store_true", help="Show all available fields (default for 'get')")

    args = parser.parse_args()
    client = GammaMarketClient()

    if args.action == "list":
        list_markets(args, client)
    elif args.action == "get":
        if not args.target:
            print("Error: Market ID required", file=sys.stderr)
            sys.exit(1)
        market = client.get_market(args.target)
        # 'get' command shows full fields by default
        print(json.dumps(market, indent=2))
    elif args.action == "search":
        if not args.target:
            print("Error: Search query required", file=sys.stderr)
            sys.exit(1)
        args.query = args.target
        search_markets(args, client)

if __name__ == "__main__":
    main()