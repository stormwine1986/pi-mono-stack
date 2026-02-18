#!/usr/bin/env python3
import os
import sys
import json
import subprocess
import urllib.request
import urllib.parse
import argparse

def get_api_key():
    """Retrieves API key from TAVILY_API_KEY environment variable."""
    api_key = os.environ.get("TAVILY_API_KEY")
    if api_key:
        return api_key.strip()
    
    print("Error: TAVILY_API_KEY environment variable not set.", file=sys.stderr)
    sys.exit(1)

def tavily_search(query, max_results=5, search_depth="basic"):
    api_key = get_api_key()
    url = "https://api.tavily.com/search"
    
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": search_depth,
        "max_results": max_results,
        "include_answer": True,
        "include_raw_content": False,
        "include_images": False,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, 
        data=data, 
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req) as response:
            if response.status != 200:
                print(f"Error: API returned status {response.status}", file=sys.stderr)
                sys.exit(1)
            
            result = json.load(response)
            
            # Format output for LLM consumption
            print(f"Search Query: {result.get('query')}")
            
            answer = result.get('answer')
            if answer:
                print(f"\nDirect Answer:\n{answer}\n")
            
            print(f"Results ({len(result.get('results', []))}):")
            for i, item in enumerate(result.get('results', []), 1):
                print(f"\n--- Result {i} ---")
                print(f"Title: {item.get('title')}")
                print(f"URL: {item.get('url')}")
                print(f"Content: {item.get('content')}")
                print(f"Score: {item.get('score')}")

    except urllib.error.URLError as e:
        print(f"Network error: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        print("Error: Failed to parse JSON response", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search using Tavily API")
    parser.add_argument("query", help="Search query string")
    parser.add_argument("--max", type=int, default=5, help="Maximum number of results")
    parser.add_argument("--depth", choices=["basic", "advanced"], default="basic", help="Search depth")
    
    args = parser.parse_args()
    tavily_search(args.query, args.max, args.depth)
