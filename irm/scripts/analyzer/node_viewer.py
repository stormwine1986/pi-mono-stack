import argparse
import os
import unicodedata
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

    def _get_display_width(self, text):
        """Calculate the actual display width of a string (CJK characters count as 2)."""
        width = 0
        for char in str(text):
            if unicodedata.east_asian_width(char) in ('W', 'F'):
                width += 2
            else:
                width += 1
        return width

    def _pad_string(self, text, length, align='left'):
        """Pad string to target display width correctly."""
        text = str(text)
        current_width = self._get_display_width(text)
        padding = max(0, length - current_width)
        if align == 'left':
            return text + (' ' * padding)
        elif align == 'right':
            return (' ' * padding) + text
        else: # center
            left_pad = padding // 2
            right_pad = padding - left_pad
            return (' ' * left_pad) + text + (' ' * right_pad)

    def list_nodes(self):
        """Fetch and display all nodes except Portfolio with ALL relevant attributes."""
        cypher = (
            "MATCH (n) WHERE NOT n:Portfolio "
            "RETURN labels(n), "
            "       COALESCE(n.ticker, n.target, '-'), "
            "       n.name, "
            "       n.value, "
            "       n.percentile, "
            "       n.pe_min, n.pe_max, "
            "       n.eps_min, n.eps_max, "
            "       n.pe_percentile, n.erp_percentile, "
            "       n.name_cn, n.metric_type, n.role, n.market "
            "ORDER BY labels(n)[0], COALESCE(n.ticker, n.target), n.name"
        )
        result = self._query_falkor(cypher)
        
        if not result or not result.result_set:
            print("[!] No nodes found (excluding Portfolio).")
            return

        # Header Definition
        cols = [
            ("TYPE(S)", 18, 'left'),
            ("ID", 8, 'left'),
            ("NAME", 28, 'left'),
            ("VAL", 8, 'right'),
            ("DETAILS / BANDS", 38, 'left'),
            ("PCT (MAIN/SUB)", 16, 'right')
        ]
        
        header_parts = [self._pad_string(c[0], c[1], c[2]) for c in cols]
        header_line = " | ".join(header_parts)
        sep_line = "-+-".join("-" * c[1] for c in cols)
        total_width = len(header_line)
        
        print("\n" + "="*total_width)
        print(header_line)
        print(sep_line)
        
        for row in result.result_set:
            labels, node_id, name, value, pct, pe_min, pe_max, eps_min, eps_max, pe_pct, erp_pct, name_cn, m_type, role, market = row
            
            display_type = ":".join(labels)[:18]
            display_id = str(node_id)[:8]
            
            # Smart Name: Use CN if available for Sector/Theme/Asset with CN, else EN
            raw_name = name_cn if name_cn and labels[0] in ['Sector', 'Theme'] else name
            if not raw_name: raw_name = "-"
            
            # Simple truncation placeholder - the pad_string handles width during print
            display_name = str(raw_name)
            if self._get_display_width(display_name) > 28:
                # Basic truncation for safety
                display_name = display_name[:20] + ".." 

            display_val = f"{float(value):.2f}" if value is not None else "-"
            
            # --- Build Details String ---
            details = []
            if pe_min is not None: details.append(f"PE:[{pe_min},{pe_max}]")
            if eps_min is not None: details.append(f"EPS:[{eps_min:.1%},{eps_max:.1%}]")
            if name_cn and labels[0] not in ['Sector', 'Theme']: details.append(f"CN:{name_cn}")
            if m_type: details.append(f"T:{m_type}")
            if role: details.append(f"R:{role}")
            if market: details.append(f"M:{market}")
            
            details_str = " | ".join(details)
            if self._get_display_width(details_str) > 38:
                details_str = details_str[:35] + ".."
            if not details_str: details_str = "-"

            # --- Build PCT String ---
            if pct is not None:
                main_pct = f"{float(pct):.2f}"
                if pe_pct is not None or erp_pct is not None:
                    pe_s = f"{float(pe_pct):.2f}" if pe_pct is not None else "-"
                    erp_s = f"{float(erp_pct):.2f}" if erp_pct is not None else "-"
                    pct_str = f"{main_pct} ({pe_s}/{erp_s})"
                else:
                    pct_str = main_pct
            else:
                pct_str = "-"

            line_data = [
                self._pad_string(display_type, 18, 'left'),
                self._pad_string(display_id, 8, 'left'),
                self._pad_string(display_name, 28, 'left'),
                self._pad_string(display_val, 8, 'right'),
                self._pad_string(details_str, 38, 'left'),
                self._pad_string(pct_str, 16, 'right')
            ]
            print(" | ".join(line_data))

        print("="*total_width + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IRM Node Viewer")
    args = parser.parse_args()
    
    viewer = IRMNodeViewer()
    viewer.list_nodes()
