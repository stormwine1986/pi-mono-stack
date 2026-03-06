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
        """Fetch current portfolio holdings from the graph to make it dynamic.
        Returns dict with denomination info per asset for multi-currency awareness.
        """
        # Also fetch base_currency from Portfolio node
        port_cypher = f"MATCH (n:Portfolio {{owner: '{owner}'}}) RETURN n.currency"
        port_result = self._query_falkor(port_cypher)
        base_currency = "USD"
        if port_result and port_result.result_set:
            base_currency = port_result.result_set[0][0] or "USD"

        cypher = f"MATCH (n:Portfolio {{owner: '{owner}'}})-[r:HOLDS]->(m) RETURN m.ticker, r.weight_pct, r.denomination"
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
                
                # Denomination priority: edge attribute > Redis > base_currency
                edge_denom = row[2] if len(row) > 2 and row[2] else None
                denomination = edge_denom or redis_data.get('denomination', base_currency)
                
                portfolio[ticker] = {
                    "weight": float(row[1]),
                    "shares": float(redis_data.get('shares', 0.0)),
                    "avg_cost": float(redis_data.get('avg_cost', 0.0)),
                    "denomination": denomination
                }
            except (ValueError, IndexError, TypeError):
                continue
        return portfolio

    def get_neighbors(self, ticker):
        """Find nodes impacted by the given ticker and return edge attributes + target node state."""
        cypher = (
            f"MATCH (n)-[r]->(m) WHERE toUpper(COALESCE(n.ticker, n.name)) = '{ticker.upper()}' "
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

    def trace_impact(self, start_ticker, initial_delta, current_vix=20, target_ticker=None, source_delta_pct=None):
        """
        Trace the impact with dynamic state modifiers.
        Formula: Impact = Source_Delta * (Beta * Mu(Path, State) * Gamma) * Decay
        
        If target_ticker is specified, only paths reaching that target are printed.
        source_delta_pct is used for heuristic percentile adjustment on the source node.
        """

        # Queue stores: (current_ticker, incoming_impact, depth, path_string)
        queue = [(start_ticker, float(initial_delta), 0, start_ticker)]
        results = []

        print(f"[*] Starting Trace: {start_ticker} with Delta: {initial_delta}%")
        if target_ticker:
            print(f"[*] Target Filter: evaluating impact on {target_ticker}")
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
                    # Soft-step Piecewise Linear Gamma:
                    # VIX <= 20: 1.0 (Normal)
                    # VIX 20-40: 1.0 -> 2.0 (Linear ramp)
                    # VIX 40-60: 2.0 -> 3.0 (Panic acceleration)
                    # VIX > 60: 3.0 (Extreme shock)
                    if current_vix <= 20:
                        gamma = 1.0
                    elif current_vix <= 40:
                        gamma = 1.0 + ((current_vix - 20) / 20.0) * 1.0
                    elif current_vix <= 60:
                        gamma = 2.0 + ((current_vix - 40) / 20.0) * 1.0
                    else:
                        gamma = 3.0
                    gamma = round(gamma, 2)
                
                # Routing logic for different modifier metrics
                metric = n['modifier_metric']
                if metric == 'source_percentile':
                    reference_percentile = n['source_percentile']
                    # [Dynamic State Trigger] If the source node is the one being shocked, 
                    # its static historical percentile is no longer valid. We heuristically simulate 
                    # an elevated/decreased percentile based on the shock magnitude.
                    if current_ticker == start_ticker and reference_percentile is not None:
                        # e.g., +50% delta -> roughly +0.25 to the percentile
                        delta_pct = source_delta_pct if source_delta_pct is not None else initial_delta
                        reference_percentile = min(0.99, max(0.01, reference_percentile + (delta_pct / 200.0)))
                elif metric == 'target_erp_percentile':
                    reference_percentile = n['target_erp_percentile']
                elif metric == 'target_pe_percentile':
                    reference_percentile = n['target_pe_percentile']
                else:
                    reference_percentile = n['target_percentile']
                
                mu = self._calculate_mu(reference_percentile, n.get('threshold_config'))
                
                # 4. Distance Decay
                # Each hop applies a single decay factor D. Since incoming_impact
                # already carries accumulated decay from prior hops, multiplying
                # by D once per hop yields total decay of D^n after n hops.
                # 
                # EXCEPTION: Structural relations are accounting identities.
                # 'DETERMINES' (P = PE * EPS), 'COMPOSES' (Index Weight), 'TRACKS' (ETF Proxy)
                # They do not suffer information loss, so decay is exactly 1.0.
                if depth == 0 or n['rel_type'] in ['DETERMINES', 'COMPOSES', 'TRACKS']:
                    d_factor = 1.0
                else:
                    d_factor = self.decay_factor
                
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
                    "logic": f"Beta:{beta} * Mu:{mu} * Gamma:{gamma} * Decay:{d_factor}",
                    "edge_id": n.get('id')
                }
                results.append(path_info)
                
                # Print step (if --target is set, only print steps on paths toward the target)
                if not target_ticker or target.upper() == target_ticker.upper() or self._can_reach_target(target, target_ticker):
                    print(f"[{depth+1}] {new_path_str} ({n['rel_type']} ID:{n.get('id')}): {round(impact, 4)}%  ({n['label']})")

                # Continue traversal if impact is still significant
                if abs(impact) > 0.01:
                    queue.append((target, impact, depth + 1, new_path_str))

        return results

    def _can_reach_target(self, current_ticker, target_ticker, max_depth=5):
        """Check if a path exists from current_ticker to target_ticker within max_depth hops."""
        cypher = (
            f"MATCH path = (n)-[*1..{max_depth}]->(m) "
            f"WHERE toUpper(COALESCE(n.ticker, n.name)) = '{current_ticker.upper()}' "
            f"AND toUpper(COALESCE(m.ticker, m.name)) = '{target_ticker.upper()}' "
            f"RETURN count(path) LIMIT 1"
        )
        result = self._query_falkor(cypher)
        if result and result.result_set:
            return result.result_set[0][0] > 0
        return False

    def estimate_vix_impact(self, start_ticker, initial_delta, max_depth=2):
        """
        Pre-trace: estimate how the event would move VIX through graph propagation.
        Uses beta and mu (state modifiers) but NOT gamma (to avoid circular dependency,
        since gamma itself depends on VIX).
        """
        if start_ticker.upper() == 'VIX':
            return float(initial_delta)

        queue = [(start_ticker, float(initial_delta), 0, start_ticker)]
        vix_impacts = []

        while queue:
            current_ticker, incoming_impact, depth, path_str = queue.pop(0)
            if depth >= max_depth:
                continue

            neighbors = self.get_neighbors(current_ticker)
            for n in neighbors:
                target = n['ticker']
                if not target or target in path_str.split(" -> "):
                    continue

                beta = n['base_beta']

                # Resolve reference percentile (same routing as trace_impact)
                metric = n['modifier_metric']
                if metric == 'source_percentile':
                    reference_percentile = n['source_percentile']
                elif metric == 'target_erp_percentile':
                    reference_percentile = n['target_erp_percentile']
                elif metric == 'target_pe_percentile':
                    reference_percentile = n['target_pe_percentile']
                else:
                    reference_percentile = n['target_percentile']

                mu = self._calculate_mu(reference_percentile, n.get('threshold_config'))

                # No gamma in pre-trace (circular dependency avoidance)
                if depth == 0 or n['rel_type'] in ['DETERMINES', 'COMPOSES', 'TRACKS']:
                    d_factor = 1.0
                else:
                    d_factor = self.decay_factor

                impact = incoming_impact * (beta * mu) * d_factor

                if target.upper() == 'VIX':
                    vix_impacts.append(impact)
                elif abs(impact) > 0.01:
                    new_path = f"{path_str} -> {target}"
                    queue.append((target, impact, depth + 1, new_path))

        return sum(vix_impacts) if vix_impacts else 0.0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IRM Ontology Tracer")
    parser.add_argument("--ticker", required=True, help="Source ticker (e.g., US10Y)")
    parser.add_argument("--delta", type=float, default=1.0, help="Initial shock percentage (e.g., 1.0 for +1%%)")
    parser.add_argument("--owner", type=str, default="Admin", help="Portfolio Owner")
    parser.add_argument("--target", type=str, default=None, help="Target node ticker to evaluate impact on (e.g., NVDA)")
    parser.add_argument("--vix", type=float, default=None, help="Override VIX value for Gamma calculation (e.g., 35)")
    
    args = parser.parse_args()
    
    tracer = IRMTracer()
    
    # 1. Fetch current market VIX from graph
    base_vix = tracer.get_vix_state()
    
    # 3. Dynamically Load Portfolio (needed for portfolio summary mode)
    portfolio = tracer.get_portfolio_assets(owner=args.owner)
    if not portfolio:
         print(f"[!] Warning: Portfolio for '{args.owner}' not found or empty.")
         portfolio_assets = []
    else:
         portfolio_assets = list(portfolio.keys())
         
    # 4. Metric correction for source delta
    cypher_meta = f"MATCH (n) WHERE COALESCE(n.ticker, n.name) = '{args.ticker}' RETURN n.metric_type, n.value"
    meta_result = tracer._query_falkor(cypher_meta)
    
    source_delta_val = args.delta
    if meta_result and meta_result.result_set:
        m_type = meta_result.result_set[0][0]
        cur_val = meta_result.result_set[0][1]
        
        if m_type in ['rate', 'volatility'] and cur_val is not None:
            source_delta_val = float(cur_val) * (args.delta / 100.0)
            print(f"[*] Metric Correction: Converting {args.delta}% relative shock to {round(source_delta_val, 4)} absolute point change (Source: {m_type})")

    # 5. Determine effective VIX (Event-Forward Estimation)
    #    The event itself may induce panic — we estimate VIX movement
    #    through graph propagation BEFORE running the main trace.
    if args.vix is not None:
        effective_vix = args.vix
        print(f"[*] VIX Override: Using user-specified VIX={effective_vix}")
    elif args.ticker.upper() == "VIX":
        effective_vix = base_vix * (1 + args.delta / 100.0)
        print(f"[*] VIX Direct Shock: {base_vix:.1f} → {effective_vix:.1f}")
    else:
        vix_delta = tracer.estimate_vix_impact(args.ticker, source_delta_val)
        if abs(vix_delta) > 0.01:
            effective_vix = max(10.0, base_vix + vix_delta)
            print(f"[*] VIX Forward Estimate: {base_vix:.1f} → {effective_vix:.1f} (Event-induced delta: {vix_delta:+.2f})")
        else:
            effective_vix = base_vix

    # 6. Run main trace with event-adjusted VIX
    impacts = tracer.trace_impact(
        args.ticker, source_delta_val, current_vix=effective_vix,
        target_ticker=args.target, source_delta_pct=args.delta
    )
    
    # ── MODE: Target-focused impact evaluation ──
    if args.target:
        target_upper = args.target.strip().upper()
        source_upper = args.ticker.strip().upper()
        
        # Filter to only impacts that reach the target node
        target_impacts = [imp for imp in impacts if (imp['to'] or '').strip().upper() == target_upper]
        
        print("\n" + "=" * 20 + f" TARGET IMPACT: {target_upper} " + "=" * 20)
        
        if not target_impacts:
            print(f"[!] No propagation path found from {source_upper} to {target_upper}.")
        else:
            # Show all paths reaching the target
            print(f"\n  Propagation paths from {source_upper} to {target_upper}:")
            print(f"  {'─' * 56}")
            for i, imp in enumerate(target_impacts, 1):
                impact_val = imp['step_impact']
                color = "\033[91m" if impact_val < 0 else "\033[92m" if impact_val > 0 else "\033[0m"
                print(f"  Path {i}: {imp['path']}")
                print(f"          Type: {imp['type']} | Depth: {imp['depth']} | Edge: {imp.get('edge_id', 'N/A')}")
                print(f"          Logic: {imp['logic']}")
                print(f"          Impact: {color}{impact_val:>+7.4f}%\033[0m")
                print()
            
            # Aggregate: Sum all path impacts (Additive Risk)
            agg_val = sum(imp['step_impact'] for imp in target_impacts)
            agg_color = "\033[91m" if agg_val < 0 else "\033[92m" if agg_val > 0 else "\033[0m"
            
            # Find the strongest contributing path for context
            dominant_path = max(target_impacts, key=lambda x: abs(x['step_impact']))
            
            print(f"  {'─' * 56}")
            print(f"  Paths Found : {len(target_impacts)}")
            print(f"  Strongest Path: {dominant_path['path']}")
            print(f"  TOTAL COMBINED IMPACT on {target_upper}: {agg_color}{agg_val:>+7.4f}%\033[0m")
            
            # If the target is also in the portfolio, show the portfolio weight context
            if target_upper in portfolio:
                weight = portfolio[target_upper]['weight']
                weighted = agg_val * weight
                print(f"  Portfolio Weight: {weight*100:>5.1f}% | Weighted PNL Contribution: {weighted:>+7.4f}%")
        
        print("=" * (42 + len(target_upper)))
    
    # ── MODE: Full portfolio summary (default) ──
    else:
        print("\n" + "="*20 + " PORTFOLIO IMPACT SUMMARY " + "="*20)
        
        # We use an 'Additive' approach for parallel paths from the same source event
        # to capture the cumulative effect of different transmission channels (e.g. Davis Double Play).
        summary_impacts = {asset.upper(): 0.0 for asset in portfolio_assets}
        
        # [FIX] Normalize source ticker check
        source_ticker_upper = args.ticker.strip().upper()
        if source_ticker_upper in summary_impacts:
            summary_impacts[source_ticker_upper] = source_delta_val
        
        for imp in impacts:
            target = (imp['to'] or "").strip().upper()
            if target in summary_impacts:
                # Additive aggregation
                summary_impacts[target] += imp['step_impact']
        
        # Group assets by denomination for multi-currency display
        denom_groups = {}
        for asset in portfolio_assets:
            denom = portfolio[asset].get('denomination', 'USD')
            denom_groups.setdefault(denom, []).append(asset)
        
        multi_currency = len(denom_groups) > 1
        total_portfolio_impact = 0.0
        
        for denom in sorted(denom_groups.keys(), key=lambda d: (d != 'USD', d)):
            assets_in_slot = denom_groups[denom]
            
            if multi_currency:
                print(f"\n  [{denom} Slot]")
                print(f"  {'-' * 64}")
            
            slot_weighted_sum = 0.0
            for asset in assets_in_slot:
                total_imp = summary_impacts.get(asset, 0)
                weight = portfolio[asset]['weight']
                weighted_imp = total_imp * weight
                total_portfolio_impact += weighted_imp
                slot_weighted_sum += weighted_imp
                
                # Color coding for terminal output
                color = "\033[91m" if total_imp < -5 else "\033[93m" if total_imp < 0 else "\033[92m" if total_imp > 0 else "\033[0m"
                print(f"{asset:<5} | Weight: {weight*100:>5.1f}% | Absolute Impact: {color}{total_imp:>7.2f}%\033[0m | Weighted PNL: {weighted_imp:>7.2f}%")
            
            if multi_currency:
                slot_color = "\033[91m" if slot_weighted_sum < 0 else "\033[92m" if slot_weighted_sum > 0 else "\033[0m"
                print(f"  [{denom} Subtotal PNL: {slot_color}{slot_weighted_sum:>+7.2f}%\033[0m]")
        
        print("-" * 66)
        port_color = "\033[91m" if total_portfolio_impact < -5 else "\033[93m" if total_portfolio_impact < 0 else "\033[92m" if total_portfolio_impact > 0 else "\033[0m"
        print(f"ESTIMATED TOTAL PORTFOLIO NAV SHOCK: {port_color}{total_portfolio_impact:>7.2f}%\033[0m")
        print("=" * 66)
