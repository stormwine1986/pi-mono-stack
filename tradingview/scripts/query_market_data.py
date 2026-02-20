#!/usr/bin/env python3
import argparse
import json
import sys
import datetime

# Attempt to import akshare and tvDatafeed
try:
    import akshare as ak
    import pandas as pd
    from tvDatafeed import TvDatafeed, Interval
except ImportError:
    print(json.dumps({"error": "akshare, pandas or tvDatafeed not installed."}))
    sys.exit(1)

def get_tv_data(symbol, exchange, n_bars=1):
    try:
        tv = TvDatafeed()
        df = tv.get_hist(symbol=symbol, exchange=exchange, interval=Interval.in_1_minute, n_bars=n_bars)
        if df is None or df.empty:
            return {"error": f"No data found for {exchange}:{symbol} on TradingView."}
        
        last_row = df.tail(1).to_dict(orient='records')[0]
        # Clean up timestamp if it's in index or a column
        return last_row
    except Exception as e:
        return {"error": f"TradingView error for {symbol}: {str(e)}"}

def parse_and_fetch(input_str, default_exchange=None):
    # Auto-map common indicators to TradingView symbols
    indicator_map = {
        "CN10Y": ("TVC", "CN10Y"),
        "US10Y": ("TVC", "US10Y"),
        "JP10Y": ("TVC", "JP10Y"),
        "VIX": ("CBOE", "VIX"),
        "DXY": ("TVC", "DXY"),
        "GOLD": ("TVC", "GOLD"),
        "UKOIL": ("TVC", "UKOIL"),
        "USDJPY": ("FX_IDC", "USDJPY"),
        "USDEUR": ("FX_IDC", "EURUSD"), # Inverted or direct? Usually EURUSD
        "EURUSD": ("FX_IDC", "EURUSD"),
        "USDCNY": ("FX_IDC", "USDCNY")
    }

    if input_str in indicator_map:
        exchange, symbol = indicator_map[input_str]
        return get_tv_data(symbol, exchange)

    if ":" in input_str:
        exchange, symbol = input_str.split(":", 1)
        return get_tv_data(symbol, exchange)
    
    # Fallback to default exchange if provided
    if default_exchange:
        return get_tv_data(input_str, default_exchange)
        
    return {"error": f"Invalid format or unknown indicator: {input_str}. Use 'EXCHANGE:SYMBOL'."}

class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.strftime('%Y-%m-%d')
        return super().default(obj)

def main():
    parser = argparse.ArgumentParser(description="Query financial data using akshare and tvDatafeed")
    parser.add_argument("query", help="Query string in 'EXCHANGE:SYMBOL' or indicator format (e.g., CBOE:BBJP, CN10Y, JP10Y)")
    parser.add_argument("--default-exchange", help="Default exchange if not provided in query")
    
    args = parser.parse_args()
    
    result = parse_and_fetch(args.query, args.default_exchange)
        
    print(json.dumps(result, indent=2, ensure_ascii=False, cls=DateEncoder))

if __name__ == "__main__":
    main()