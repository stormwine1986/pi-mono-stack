import os
import json
import redis
import falkordb
from urllib.parse import urlparse

def migrate():
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
    parsed = urlparse(redis_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 6379
    
    r = redis.Redis(host=host, port=port, decode_responses=True)
    db = falkordb.FalkorDB(host=host, port=port)
    graph = db.select_graph("Graph-001")

    print("[*] Migrating PE bands from Redis to FalkorDB...")
    pe_bands = r.hgetall("irm:config:pe_bands")
    for ticker, data_str in pe_bands.items():
        data = json.loads(data_str)
        pe_min = data.get("min")
        pe_max = data.get("max")
        if pe_min is not None and pe_max is not None:
            cypher = f"MATCH (h:Hub:Valuation) WHERE h.target = '{ticker}' SET h.pe_min = {pe_min}, h.pe_max = {pe_max} RETURN h"
            res = graph.query(cypher)
            if res.result_set:
                print(f" [+] Migrated PE band for {ticker}: [{pe_min}, {pe_max}]")
            else:
                print(f" [!] No Hub:Valuation node found for {ticker}")

    print("[*] Migrating EPS bands from Redis to FalkorDB...")
    eps_bands = r.hgetall("irm:config:eps_bands")
    for ticker, data_str in eps_bands.items():
        data = json.loads(data_str)
        eps_min = data.get("min")
        eps_max = data.get("max")
        if eps_min is not None and eps_max is not None:
            cypher = f"MATCH (h:Hub:Earnings) WHERE h.target = '{ticker}' SET h.eps_min = {eps_min}, h.eps_max = {eps_max} RETURN h"
            res = graph.query(cypher)
            if res.result_set:
                print(f" [+] Migrated EPS band for {ticker}: [{eps_min}, {eps_max}]")
            else:
                print(f" [!] No Hub:Earnings node found for {ticker}")

    print("[+] Migration complete.")

if __name__ == "__main__":
    migrate()
