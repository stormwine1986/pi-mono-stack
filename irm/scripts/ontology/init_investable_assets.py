from falkordb import FalkorDB
import os
from urllib.parse import urlparse

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
parsed = urlparse(redis_url)
host = parsed.hostname or "localhost"
port = parsed.port or 6379

db = FalkorDB(host=host, port=port)
graph = db.select_graph('Graph-001')

print("1. Injecting :Investable label to tradeable asset categories...")
# Stock, EquityETF, Crypto, Commodity are investable.
graph.query("""
MATCH (a:Asset)
WHERE 'Stock' in labels(a) OR 'EquityETF' in labels(a) OR 'Crypto' in labels(a) OR 'Commodity' in labels(a)
SET a:Investable
""")

print("2. Providing default safety Kelly Assumptions to all :Investable nodes...")
graph.query("""
MATCH (a:Investable)
SET a.base_win_rate = 0.55, 
    a.expected_upside = 0.30, 
    a.expected_max_dd = 0.20
""")

print("3. Overriding specific high-conviction assets with custom assumptions...")
assumptions = {
    "QQQM": {"base_win_rate": 0.70, "upside": 0.40, "max_dd": 0.20},  # b = 2.0
    "NVDA": {"base_win_rate": 0.65, "upside": 0.80, "max_dd": 0.40},  # b = 2.0
    "PLTR": {"base_win_rate": 0.60, "upside": 1.20, "max_dd": 0.50},  # b = 2.4
    "GOLD": {"base_win_rate": 0.60, "upside": 0.20, "max_dd": 0.10},  # b = 2.0
    "BTC":  {"base_win_rate": 0.55, "upside": 1.50, "max_dd": 0.60},  # b = 2.5
    "BBJP": {"base_win_rate": 0.60, "upside": 0.30, "max_dd": 0.20},  # b = 1.5
}

for ticker, data in assumptions.items():
    cypher = f"""MATCH (a:Investable {{ticker: '{ticker}'}}) 
                 SET a.base_win_rate = {data['base_win_rate']}, 
                     a.expected_upside = {data['upside']}, 
                     a.expected_max_dd = {data['max_dd']}"""
    graph.query(cypher)

print("4. Verifying Investable nodes...")
res = graph.query("MATCH (a:Investable) RETURN a.ticker, a.base_win_rate, a.expected_upside, a.expected_max_dd")
for row in res.result_set:
    print(f"{row[0]:<6} | WinRate: {row[1]:.2f} | Upside: {row[2]:.2f} | MaxDD: {row[3]:.2f}")

print("\n[+] Migration completed successfully.")
