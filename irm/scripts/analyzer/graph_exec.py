import argparse
import os
import json
from urllib.parse import urlparse
from falkordb import FalkorDB

class IRMGraphExec:
    def __init__(self, graph_name="Graph-001"):
        self.graph_name = graph_name
        
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        parsed = urlparse(redis_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 6379
        
        try:
            self.db = FalkorDB(host=host, port=port)
            self.graph = self.db.select_graph(graph_name)
        except Exception as e:
            print(f"[!] Failed to connect to FalkorDB at {host}:{port}: {e}")
            self.graph = None

    def execute(self, cypher):
        if not self.graph:
            return

        print(f"[*] Executing Cypher: {cypher}\n")
        try:
            result = self.graph.query(cypher)
            
            has_results = False
            if hasattr(result, 'result_set') and result.result_set:
                has_results = True
                
                # Try to print header if available in falkordb python client
                # However, some versions might not expose it identically, so we wrap it
                if hasattr(result, 'header') and result.header:
                    try:
                        header = []
                        for col in result.header:
                            if isinstance(col, (list, tuple)) and len(col) > 1:
                                header.append(str(col[1]))
                            else:
                                header.append(str(col))
                        print(" | ".join(header))
                        print("-" * sum([len(h) + 3 for h in header]))
                    except:
                        pass
                
                # Print rows
                for row in result.result_set:
                    print(" | ".join([str(val) for val in row]))
            
            if not has_results:
                print("(empty result)")
            
            # Print statistics (e.g., nodes created, properties set)
            if hasattr(result, 'statistics') and result.statistics:
                print("\n[+] Statistics:")
                for key, val in result.statistics.items():
                    print(f"  - {key}: {val}")

        except Exception as e:
            print(f"[!] Query Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IRM Cypher Executor")
    parser.add_argument("query", help="Cypher query to execute")
    args = parser.parse_args()
    
    executor = IRMGraphExec()
    executor.execute(args.query)
