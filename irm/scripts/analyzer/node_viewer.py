import argparse
import os
from urllib.parse import urlparse
from falkordb import FalkorDB

class IRMNodeViewer:
    def __init__(self, graph_name="Graph-001"):
        self.graph_name = graph_name
        
        # Priority: REDIS_URL env var > default
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

    def _query_falkor(self, cypher):
        """Execute Cypher query via falkordb-python."""
        if not self.graph:
            return None
        try:
            return self.graph.query(cypher)
        except Exception as e:
            print(f"[!] Query Error: {e}")
            return None

    def list_nodes(self):
        """Fetch and display all nodes except Portfolio."""
        # Query labels, ticker, name, percentile, target
        cypher = (
            "MATCH (n) WHERE NOT n:Portfolio "
            "RETURN labels(n), n.ticker, n.name, n.percentile, n.target "
            "ORDER BY labels(n)[0], COALESCE(n.ticker, n.target), n.name"
        )
        result = self._query_falkor(cypher)
        
        if not result or not result.result_set:
            print("[!] No nodes found (excluding Portfolio).")
            return

        # Header
        print("\n" + "="*105)
        print(f" {'TYPE(S)':<25} | {'ID/TICKER':<15} | {'NAME':<40} | {'PERCENTILE':>10}")
        print("="*105)
        
        for row in result.result_set:
            labels = row[0]
            ticker = row[1]
            name = row[2]
            percentile = row[3]
            target = row[4]
            
            # Formatting Labels
            display_type = ":".join(labels)
            
            # Formatting ID/Ticker
            if ticker:
                node_id = ticker
            elif target:
                node_id = f"[{target}]" # Hub target
            else:
                node_id = "-"
                
            display_name = name if name else "-"
            
            # Formatting Percentile
            pct_val = f"{float(percentile):.2f}" if percentile is not None else "-"
            
            print(f" {display_type:<25} | {node_id:<15} | {display_name[:40]:<40} | {pct_val:>10}")

        print("="*105 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IRM Node Viewer")
    args = parser.parse_args()
    
    viewer = IRMNodeViewer()
    viewer.list_nodes()
