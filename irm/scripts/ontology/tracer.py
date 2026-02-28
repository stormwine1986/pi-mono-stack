import json
import argparse
import os
from urllib.parse import urlparse
from falkordb import FalkorDB

class IRMTracer:
    def __init__(self, graph_name="Graph-001"):
        self.graph_name = graph_name
        self.decay_factor = 0.8  # Dn: Distance Decay
        
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

    def get_portfolio_assets(self, owner="Admin"):
        """Fetch current portfolio holdings from the graph to make it dynamic."""
        cypher = f"MATCH (n:Portfolio {{owner: '{owner}'}})-[r:HOLDS]->(m) RETURN m.ticker, r.weight_pct, r.shares, r.avg_cost"
        result = self._query_falkor(cypher)
        
        portfolio = {}
        if not result or not result.result_set:
            return portfolio

        for row in result.result_set:
            try:
                ticker = row[0]
                portfolio[ticker] = {
                    "weight": float(row[1]),
                    "shares": float(row[2]),
                    "avg_cost": float(row[3])
                }
            except (ValueError, IndexError, TypeError):
                continue
        return portfolio

    def get_neighbors(self, ticker):
        """Find nodes impacted by the given ticker and return edge attributes + target node state."""
        cypher = (
            f"MATCH (n)-[r]->(m) WHERE COALESCE(n.ticker, n.name) = '{ticker}' "
            f"RETURN COALESCE(m.ticker, m.name), type(r), r.base_beta, r.gamma_sensitive, "
            f"r.state_trigger, labels(m)[0], m.percentile, r.modifier_metric, r.threshold_config, n.percentile"
        )
        result = self._query_falkor(cypher)
        
        neighbors = []
        if not result or not result.result_set:
            return neighbors

        for row in result.result_set:
            try:
                neighbors.append({
                    "ticker": row[0],
                    "rel_type": row[1],
                    "base_beta": float(row[2]) if row[2] is not None else 1.0,
                    "gamma_sensitive": str(row[3]).lower() == 'true',
                    "state_trigger": row[4],
                    "label": row[5],
                    "target_percentile": float(row[6]) if row[6] is not None else None,
                    "modifier_metric": row[7],
                    "threshold_config": row[8] if len(row) > 8 else None,
                    "source_percentile": float(row[9]) if (len(row) > 9 and row[9] is not None) else None
                })
            except (ValueError, IndexError, TypeError):
                continue
        return neighbors

    def _calculate_mu(self, percentile, threshold_config_str):
        """
        Dynamically calculate the State Modifier (mu) based on JSON threshold rules.
        """
        if percentile is None or not threshold_config_str:
            return 1.0

        try:
            rules = json.loads(threshold_config_str)
            for rule in rules:
                min_val = rule.get("min", -float('inf'))
                max_val = rule.get("max", float('inf'))
                if min_val <= percentile < max_val:
                    return float(rule.get("mu", 1.0))
        except Exception as e:
            pass
            
        return 1.0

    def trace_impact(self, start_ticker, initial_delta, current_vix=20):
        """
        Trace the impact with dynamic state modifiers.
        Formula: Impact = Source_Delta * (Beta * Mu(Path, State) * Gamma) * Decay
        """

        # Queue stores: (current_ticker, incoming_impact, depth, path_string)
        queue = [(start_ticker, float(initial_delta), 0, start_ticker)]
        results = []

        print(f"[*] Starting Trace: {start_ticker} with Delta: {initial_delta}")
        print("-" * 60)

        while queue:
            current_ticker, incoming_impact, depth, path_str = queue.pop(0)
            
            neighbors = self.get_neighbors(current_ticker)
            
            for n in neighbors:
                target = n['ticker']
                if target in path_str.split(" -> ") or depth >= 5: continue
                
                # 1. Base Beta
                beta = n['base_beta']
                
                # 2. Gamma (Volatility Accelerator)
                gamma = 1.0
                if n['gamma_sensitive'] and current_vix > 30:
                    gamma = 1.5 if current_vix <= 45 else 2.5
                
                # 3. DYNAMIC State Modifier (mu) - JSON Config Driven!
                if n['modifier_metric'] == 'source_percentile':
                    reference_percentile = n['source_percentile']
                else:
                    reference_percentile = n['target_percentile']
                
                mu = self._calculate_mu(reference_percentile, n.get('threshold_config'))
                
                # 4. Distance Decay
                d_factor = self.decay_factor ** depth
                
                impact = incoming_impact * (beta * mu * gamma) * d_factor
                
                new_path_str = f"{path_str} -> {target}"
                
                # Record result
                path_info = {
                    "from": current_ticker,
                    "to": target,
                    "type": n['rel_type'],
                    "step_impact": round(impact, 4),
                    "depth": depth + 1,
                    "path": new_path_str,
                    "logic": f"Beta:{beta} * Mu:{mu} * Gamma:{gamma} * Decay:{round(d_factor,2)}"
                }
                results.append(path_info)
                
                
                # Fetch target node name for better printing if available, else just ticker
                target_name = target if target else "Unnamed Node"
                print(f"[{depth+1}] {new_path_str} ({n['rel_type']}): {round(impact, 4)}%  ({n['label']})")

                # Continue traversal if impact is still significant
                if abs(impact) > 0.05:
                    queue.append((target, impact, depth + 1, new_path_str))

        return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IRM Ontology Tracer")
    parser.add_argument("--ticker", required=True, help="Source ticker (e.g., US10Y)")
    parser.add_argument("--delta", type=float, default=1.0, help="Initial shock percentage (e.g., 1.0 for +1%)")
    parser.add_argument("--vix", type=float, default=20, help="Current VIX level")
    parser.add_argument("--owner", type=str, default="Admin", help="Portfolio Owner")
    
    args = parser.parse_args()
    
    tracer = IRMTracer()
    
    # 1. Dynamically Load Portfolio
    portfolio = tracer.get_portfolio_assets(owner=args.owner)
    if not portfolio:
         print(f"[!] Warning: Portfolio for '{args.owner}' not found or empty.")
         portfolio_assets = []
    else:
         portfolio_assets = list(portfolio.keys())
         
    # 3. Run Trace - Now with dynamic internal path-specific logic
    impacts = tracer.trace_impact(args.ticker, args.delta, current_vix=args.vix)
    
    # 4. Aggregate Portfolio Summary
    print("\n" + "="*20 + " PORTFOLIO IMPACT SUMMARY " + "="*20)
    
    # Initialize all portfolio assets to 1.0 multiplier (no change)
    summary = {asset: 1.0 for asset in portfolio_assets}
    
    for imp in impacts:
        if imp['to'] in portfolio_assets:
            # Multiplicative compounding: convert impact % to a multiplier (e.g., -30% -> 0.7)
            shock_multiplier = 1.0 + (imp['step_impact'] / 100.0)
            # Physical limit: Asset price can't drop below zero
            if shock_multiplier < 0:
                shock_multiplier = 0.0
            summary[imp['to']] *= shock_multiplier
            
    # Convert final aggregated multipliers back to percentage impacts
    for asset in portfolio_assets:
        summary[asset] = (summary[asset] - 1.0) * 100.0
    
    total_portfolio_impact = 0.0
    for asset in portfolio_assets:
        total_imp = summary.get(asset, 0)
        weight = portfolio[asset]['weight']
        weighted_imp = total_imp * weight
        total_portfolio_impact += weighted_imp
        
        color = "\033[91m" if total_imp < 0 else "\033[92m" if total_imp > 0 else "\033[0m"
        print(f"{asset:<5} | Weight: {weight*100:>5.1f}% | Absolute Impact: {color}{total_imp:>6.2f}%\033[0m | Weighted PNL Contribution: {weighted_imp:>6.2f}%")
    
    print("-" * 66)
    port_color = "\033[91m" if total_portfolio_impact < 0 else "\033[92m" if total_portfolio_impact > 0 else "\033[0m"
    print(f"ESTIMATED TOTAL PORTFOLIO NAV SHOCK: {port_color}{total_portfolio_impact:>6.2f}%\033[0m")
    print("=" * 66)
