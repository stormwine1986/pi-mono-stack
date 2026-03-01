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
        cypher = f"MATCH (n:Portfolio {{owner: '{owner}'}})-[r:HOLDS]->(m) RETURN m.ticker, r.weight_pct"
        result = self._query_falkor(cypher)
        
        portfolio = {}
        if not result or not result.result_set:
            return portfolio

        import redis
        host = self.db.connection.connection_pool.connection_kwargs.get('host', 'localhost')
        port = self.db.connection.connection_pool.connection_kwargs.get('port', 6379)
        r_client = redis.Redis(host=host, port=port, decode_responses=True)

        for row in result.result_set:
            try:
                ticker = (row[0] or "").strip().upper()
                if not ticker: continue
                
                redis_key = f"irm:portfolio:{owner}:holdings:{ticker}"
                redis_data = r_client.hgetall(redis_key)
                
                portfolio[ticker] = {
                    "weight": float(row[1]),
                    "shares": float(redis_data.get('shares', 0.0)),
                    "avg_cost": float(redis_data.get('avg_cost', 0.0))
                }
            except (ValueError, IndexError, TypeError):
                continue
        return portfolio

    def get_neighbors(self, ticker):
        """Find nodes impacted by the given ticker and return edge attributes + target node state."""
        cypher = (
            f"MATCH (n)-[r]->(m) WHERE COALESCE(n.ticker, n.name) = '{ticker}' "
            f"RETURN COALESCE(m.ticker, m.name), type(r), r.base_beta, r.gamma_sensitive, "
            f"r.state_trigger, labels(m)[0], m.percentile, r.modifier_metric, r.threshold_config, n.percentile, "
            f"m.pe_percentile, m.erp_percentile, r.id"
        )
        result = self._query_falkor(cypher)
        
        neighbors = []
        if not result or not result.result_set:
            return neighbors

        for row in result.result_set:
            try:
                neighbors.append({
                    "ticker": (row[0] or "").strip().upper(),
                    "rel_type": row[1],
                    "base_beta": float(row[2]) if row[2] is not None else 1.0,
                    "gamma_sensitive": str(row[3]).lower() == 'true',
                    "state_trigger": row[4],
                    "label": row[5],
                    "target_percentile": float(row[6]) if row[6] is not None else None,
                    "modifier_metric": row[7],
                    "threshold_config": row[8] if len(row) > 8 else None,
                    "source_percentile": float(row[9]) if (len(row) > 9 and row[9] is not None) else None,
                    "target_pe_percentile": float(row[10]) if (len(row) > 10 and row[10] is not None) else None,
                    "target_erp_percentile": float(row[11]) if (len(row) > 11 and row[11] is not None) else None,
                    "id": row[12] if len(row) > 12 else None
                })
            except (ValueError, IndexError, TypeError):
                continue
        return neighbors

    def get_vix_state(self):
        """Fetch the current market VIX value from the graph."""
        cypher = "MATCH (a:Asset {ticker: 'VIX'}) RETURN a.value"
        result = self._query_falkor(cypher)
        if result and result.result_set:
            try:
                return float(result.result_set[0][0])
            except (ValueError, TypeError, IndexError):
                pass
        return 20.0  # Conservative fallback

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

        print(f"[*] Starting Trace: {start_ticker} with Delta: {initial_delta}%")
        print(f"[*] Market Context - Base VIX: {current_vix}")
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
                if n['gamma_sensitive']:
                    # Use the effective VIX (which might include a shock) for Gamma
                    if current_vix >= 30:
                        gamma = 1.5 if current_vix <= 45 else 2.5
                
                # Routing logic for different modifier metrics
                metric = n['modifier_metric']
                if metric == 'source_percentile':
                    reference_percentile = n['source_percentile']
                    # [Dynamic State Trigger] If the source node is the one being shocked, 
                    # its static historical percentile is no longer valid. We heuristically simulate 
                    # an elevated/decreased percentile based on the shock magnitude.
                    if current_ticker == start_ticker and reference_percentile is not None:
                        # e.g., +50% delta -> roughly +0.25 to the percentile
                        reference_percentile = min(0.99, max(0.01, reference_percentile + (args.delta / 200.0)))
                elif metric == 'target_erp_percentile':
                    reference_percentile = n['target_erp_percentile']
                elif metric == 'target_pe_percentile':
                    reference_percentile = n['target_pe_percentile']
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
                    "logic": f"Beta:{beta} * Mu:{mu} * Gamma:{gamma} * Decay:{round(d_factor,2)}",
                    "edge_id": n.get('id')
                }
                results.append(path_info)
                
                
                # Fetch target node name for better printing if available, else just ticker
                target_name = target if target else "Unnamed Node"
                print(f"[{depth+1}] {new_path_str} ({n['rel_type']} ID:{n.get('id')}): {round(impact, 4)}%  ({n['label']})")

                # Continue traversal if impact is still significant
                if abs(impact) > 0.05:
                    queue.append((target, impact, depth + 1, new_path_str))

        return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IRM Ontology Tracer")
    parser.add_argument("--ticker", required=True, help="Source ticker (e.g., US10Y)")
    parser.add_argument("--delta", type=float, default=1.0, help="Initial shock percentage (e.g., 1.0 for +1%)")
    parser.add_argument("--owner", type=str, default="Admin", help="Portfolio Owner")
    
    args = parser.parse_args()
    
    tracer = IRMTracer()
    
    # 1. Fetch current market VIX from graph
    base_vix = tracer.get_vix_state()
    
    # 2. Calculate effective VIX for the trace
    # If we are shocking VIX itself, the effective VIX for Gamma should reflect the shock.
    effective_vix = base_vix
    if args.ticker == "VIX":
        effective_vix = base_vix * (1 + args.delta / 100.0)
    
    # 3. Dynamically Load Portfolio
    portfolio = tracer.get_portfolio_assets(owner=args.owner)
    if not portfolio:
         print(f"[!] Warning: Portfolio for '{args.owner}' not found or empty.")
         portfolio_assets = []
    else:
         portfolio_assets = list(portfolio.keys())
         
    # 4. Run Trace with automatically determined VIX
    # Get metadata for the source ticker to handle metric conversion
    cypher_meta = f"MATCH (n) WHERE COALESCE(n.ticker, n.name) = '{args.ticker}' RETURN n.metric_type, n.value"
    meta_result = tracer._query_falkor(cypher_meta)
    
    source_delta_val = args.delta
    if meta_result and meta_result.result_set:
        m_type = meta_result.result_set[0][0]
        cur_val = meta_result.result_set[0][1]
        
        # If source is a rate or volatility, convert the % delta to absolute point change
        # beta is calculated as (% change in target) per (1 unit change in source)
        if m_type in ['rate', 'volatility'] and cur_val is not None:
            # Absolute change = current_value * (percentage_delta / 100)
            source_delta_val = float(cur_val) * (args.delta / 100.0)
            print(f"[*] Metric Correction: Converting {args.delta}% relative shock to {round(source_delta_val, 4)} absolute point change (Source: {m_type})")

    impacts = tracer.trace_impact(args.ticker, source_delta_val, current_vix=effective_vix)
    
    # 5. Aggregate Portfolio Summary
    print("\n" + "="*20 + " PORTFOLIO IMPACT SUMMARY " + "="*20)
    
    # We use a 'Max Absolute Impact' approach for parallel paths from the same source event
    # instead of multiplicative compounding to avoid double-counting correlated risk paths.
    summary_impacts = {asset.upper(): 0.0 for asset in portfolio_assets}
    
    # [FIX] Normalize source ticker check
    source_ticker_upper = args.ticker.strip().upper()
    if source_ticker_upper in summary_impacts:
        summary_impacts[source_ticker_upper] = source_delta_val
    
    for imp in impacts:
        target = (imp['to'] or "").strip().upper()
        if target in summary_impacts:
            current_best = summary_impacts[target]
            new_val = imp['step_impact']
            # Take the one with the largest absolute magnitude (most severe impact)
            if abs(new_val) > abs(current_best):
                summary_impacts[target] = new_val
    
    total_portfolio_impact = 0.0
    for asset in portfolio_assets:
        total_imp = summary_impacts.get(asset, 0)
        weight = portfolio[asset]['weight']
        weighted_imp = total_imp * weight
        total_portfolio_impact += weighted_imp
        
        # Color coding for terminal output
        color = "\033[91m" if total_imp < -5 else "\033[93m" if total_imp < 0 else "\033[92m" if total_imp > 0 else "\033[0m"
        print(f"{asset:<5} | Weight: {weight*100:>5.1f}% | Absolute Impact: {color}{total_imp:>7.2f}%\033[0m | Weighted PNL Contribution: {weighted_imp:>7.2f}%")
    
    print("-" * 66)
    port_color = "\033[91m" if total_portfolio_impact < -5 else "\033[93m" if total_portfolio_impact < 0 else "\033[92m" if total_portfolio_impact > 0 else "\033[0m"
    print(f"ESTIMATED TOTAL PORTFOLIO NAV SHOCK: {port_color}{total_portfolio_impact:>7.2f}%\033[0m")
    print("=" * 66)
