import argparse
import os
import json
from urllib.parse import urlparse
from falkordb import FalkorDB
import unicodedata

def get_display_width(s):
    """Calculate the display width of a string considering wide characters (e.g. Chinese)."""
    width = 0
    for char in s:
        if unicodedata.east_asian_width(char) in ('W', 'F'):
            width += 2
        else:
            width += 1
    return width

def format_cell(s, width, align='left'):
    """Format a cell with specific width, handling wide characters."""
    s = s or "-"
    # Truncate if too long (approximate)
    current_width = 0
    truncated_s = ""
    for char in s:
        w = 2 if unicodedata.east_asian_width(char) in ('W', 'F') else 1
        if current_width + w > width:
            break
        truncated_s += char
        current_width += w
    
    padding = max(0, width - current_width)
    if align == 'left':
        return truncated_s + ' ' * padding
    else:
        return ' ' * padding + truncated_s

class IRMEdgeViewer:
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

    def list_edges(self):
        """Fetch and display all edges except HOLDS."""
        cypher = (
            "MATCH (a)-[r]->(b) WHERE type(r) <> 'HOLDS' "
            "RETURN labels(a), COALESCE(a.ticker, a.name), type(r), r.id, r.base_beta, r.gamma_sensitive, "
            "labels(b), COALESCE(b.ticker, b.name), r.threshold_config "
            "ORDER BY type(r), labels(a)[0], COALESCE(a.ticker, a.name)"
        )
        result = self._query_falkor(cypher)
        
        if not result or not result.result_set:
            print("[!] No edges found (excluding HOLDS).")
            return

        # Header definitions
        cols = [
            ("FROM (TYPE:ID)", 32, 'left'),
            ("RELATION", 12, 'left'),
            ("TO (TYPE:ID)", 32, 'left'),
            ("EDGE ID", 22, 'left'),
            ("BETA", 8, 'right'),
            ("GAMMA", 6, 'left'),
            ("THRESHOLD CONFIG (rules)", 45, 'left')
        ]

        # Build header line
        header = " " + " | ".join(format_cell(c[0], c[1], c[2]) for c in cols)
        print("\n" + "=" * len(header))
        print(header)
        print("-" * len(header))
        
        for row in result.result_set:
            src_labels = row[0]
            src_name = row[1]
            rel_type = row[2]
            edge_id = row[3] if row[3] else "-"
            beta = row[4]
            gamma = "YES" if str(row[5]).lower() == 'true' else "NO"
            tgt_labels = row[6]
            tgt_name = row[7]
            config_raw = row[8]
            
            src_display = f"{':'.join(src_labels)}({src_name})"
            tgt_display = f"{':'.join(tgt_labels)}({tgt_name})"
            
            beta_val = f"{float(beta):.3f}" if beta is not None else "-"

            # Format config to be human readable
            config_display = "-"
            if config_raw and config_raw != "[]":
                try:
                    rules = json.loads(config_raw)
                    display_parts = []
                    for rule in rules:
                        m_val = rule.get('min', 0)
                        max_val = rule.get('max', 1)
                        mu = rule.get('mu', 1.0)
                        display_parts.append(f"{int(m_val*100)}~{int(max_val*100)}%:{mu}x")
                    config_display = ", ".join(display_parts)
                except:
                    config_display = "Invalid JSON"
            
            # Format row
            cells = [
                format_cell(src_display, 32, 'left'),
                format_cell(rel_type, 12, 'left'),
                format_cell(tgt_display, 32, 'left'),
                format_cell(edge_id, 22, 'left'),
                format_cell(beta_val, 8, 'right'),
                format_cell(gamma, 6, 'left'),
                format_cell(config_display, 45, 'left')
            ]
            print(" " + " | ".join(cells))

        print("=" * len(header) + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IRM Edge Viewer")
    args = parser.parse_args()
    
    viewer = IRMEdgeViewer()
    viewer.list_edges()
