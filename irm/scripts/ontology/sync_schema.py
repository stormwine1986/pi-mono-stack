import sys
import os
from urllib.parse import urlparse
from falkordb import FalkorDB

def sync_schema(schema_path, graph_name="Graph-001"):
    if not os.path.exists(schema_path):
        print(f"[!] Schema file not found: {schema_path}")
        return

    print(f"[*] Reading schema from {schema_path}...")
    with open(schema_path, "r") as f:
        content = f.read()

    # Clean up the cypher (very simple cleaning)
    lines = content.split('\n')
    clean_lines = []
    for line in lines:
        l = line.strip()
        if l.startswith('//') or not l:
            continue
        # remove inline comments
        if '//' in l:
            l = l.split('//')[0].strip()
        clean_lines.append(l)

    clean_content = ' '.join(clean_lines)
    queries = clean_content.split(';')

    # Connection details from environment
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    parsed = urlparse(redis_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 6379

    print(f"[*] Connecting to FalkorDB at {host}:{port}...")
    try:
        db = FalkorDB(host=host, port=port)
        graph = db.select_graph(graph_name)
    except Exception as e:
        print(f"[!] Connection failed: {e}")
        return

    for i, query in enumerate(queries):
        query = query.strip()
        if not query:
            continue
        print(f"[*] Executing query {i+1}/{len(queries)-1}...")
        try:
            res = graph.query(query)
            if res.result_set:
                print(f"    - {res.result_set}")
            else:
                # Print stats
                print(f"    - Nodes created: {res.nodes_created}, Relationships created: {res.relationships_created}")
        except Exception as e:
            print(f"[!] Error executing query {i+1}: {e}")
            # Continue or stop? Let's stop on error for safety
            return

    print("[+] Schema sync complete.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema", default="/home/pi-mono/.pi/agent/workspace/.irm/SCHEMA.cypher")
    args = parser.parse_args()
    sync_schema(args.schema)
