import argparse
import json
import os
from urllib.parse import urlparse
from falkordb import FalkorDB

class KellyAdvisor:
    def __init__(self, kelly_fraction=0.5, graph_name="Graph-001"):
        """
        :param kelly_fraction: 0.5 for Half-Kelly, 0.25 for Quarter-Kelly.
                               Essential for long-term investments to avoid ruin.
        """
        self.kelly_fraction = kelly_fraction
        self.graph_name = graph_name
        
        # Assumptions are now stored in ontology graph under :Investable nodes.

    def fetch_current_weights(self, owner="Admin"):
        """Fetch current weights directly from FalkorDB [:HOLDS] edges."""
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        parsed = urlparse(redis_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 6379
        
        try:
            db = FalkorDB(host=host, port=port)
            graph = db.select_graph(self.graph_name)
            cypher = f"MATCH (p:Portfolio {{owner: '{owner}'}})-[r:HOLDS]->(a:Investable) RETURN a.ticker, r.weight_pct"
            result = graph.query(cypher)
            
            weights = {}
            if result and result.result_set:
                for row in result.result_set:
                    weights[row[0]] = float(row[1] or 0.0)
            return weights
        except Exception as e:
            print(f"[!] Warning: Failed to fetch weights from DB: {e}")
            return {}

    def fetch_assumptions(self, tickers):
        """Fetch base assumptions for a list of tickers from :Investable nodes."""
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        parsed = urlparse(redis_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 6379
        
        try:
            db = FalkorDB(host=host, port=port)
            graph = db.select_graph(self.graph_name)
            cypher_list = json.dumps(list(tickers))
            cypher = f"MATCH (a:Investable) WHERE a.ticker IN {cypher_list} RETURN a.ticker, a.base_win_rate, a.expected_upside, a.expected_max_dd"
            result = graph.query(cypher)
            
            assumptions = {}
            if result and result.result_set:
                for row in result.result_set:
                    assumptions[row[0]] = {
                        "base_win_rate": float(row[1]) if row[1] is not None else 0.55,
                        "upside": float(row[2]) if row[2] is not None else 0.30,
                        "max_dd": float(row[3]) if row[3] is not None else 0.20
                    }
            return assumptions
        except Exception as e:
            print(f"[!] Warning: Failed to fetch assumptions from DB: {e}")
            return {}

    def evaluate_position(self, asset, current_weight, impact_score, asset_assumptions):
        """
        Evaluate optimal position size based on ontology impact score.
        """
        base_p = asset_assumptions.get("base_win_rate", 0.55)
        upside = asset_assumptions.get("upside", 0.30)
        max_dd = asset_assumptions.get("max_dd", 0.20)
        
        b = upside / max_dd if max_dd > 0 else 1.0

        # 1. Update Bayesian Probability based on Impact Score
        if impact_score < 0:
            probability_adj = impact_score * 0.005  # e.g., -100% impact -> -0.5 to win rate
        else:
            probability_adj = impact_score * 0.002  # e.g., +100% impact -> +0.2 to win rate
            
        new_p = max(0.01, min(0.99, base_p + probability_adj)) 
        new_q = 1.0 - new_p

        # 2. Raw Kelly Formula: f* = (bp - q) / b
        raw_kelly = new_p - (new_q / b) if b > 0 else 0
        raw_kelly = max(0.0, raw_kelly)

        # 3. Apply Fractional Kelly
        recommended_weight = raw_kelly * self.kelly_fraction

        # 4. Generate Actionable Suggestion
        weight_diff = recommended_weight - current_weight
        action = "HOLD"
        if weight_diff > 0.05:
            action = "ADD"
        elif weight_diff < -0.05:
            action = "REDUCE"
            if recommended_weight <= 0.01:
                action = "LIQUIDATE"

        return {
            "asset": asset,
            "impact_score": round(impact_score, 2),
            "original_P_win": base_p,
            "new_P_win": round(new_p, 4),
            "b_ratio": round(b, 2),
            "raw_full_kelly_weight": round(raw_kelly, 4),
            "recommended_weight": round(recommended_weight, 4),
            "current_weight": round(current_weight, 4),
            "action": action,
            "suggested_delta": round(weight_diff, 4)
        }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IRM Kelly Position Advisor")
    parser.add_argument("--impacts", type=str, required=True, help="JSON impacts. e.g. '{\"QQQM\": -19.01}'")
    parser.add_argument("--weights", type=str, help="Optional current weights JSON. If omitted, fetched from DB.")
    parser.add_argument("--owner", default="Admin", help="Portfolio owner for weight fetching")
    parser.add_argument("--fraction", type=float, default=0.5, help="Kelly fraction (default 0.5)")
    
    args = parser.parse_args()
    
    try:
        impacts = json.loads(args.impacts)
    except json.JSONDecodeError as e:
        print(f"Error parsing impacts JSON: {e}")
        exit(1)
        
    advisor = KellyAdvisor(kelly_fraction=args.fraction)
    
    # Auto-fetch weights if not provided
    if args.weights:
        weights = json.loads(args.weights)
    else:
        weights = advisor.fetch_current_weights(owner=args.owner)
        if not weights:
            print(f"[!] No active holdings found for {args.owner}. Please provide --weights manually.")
            # We don't exit, just continue with 0 weights if needed
    
    print("\n" + "="*20 + " KELLY CRITERION POSITION ADVISOR " + "="*20)
    print(f"Mode: {args.fraction}-Kelly | Owner: {args.owner}")
    print("-" * 75)
    print(f"{'Asset':<6} | {'Impact':<8} | {'WinRate':<7} | {'Curr Wt':<8} | {'Rec Wt':<8} | {'ACTION':<10}")
    print("-" * 75)
    
    # Process all assets in impacts, or all assets in weights
    all_tickers = set(impacts.keys()) | set(weights.keys())
    db_assumptions = advisor.fetch_assumptions(all_tickers)
    
    for asset in sorted(all_tickers):
        impact = impacts.get(asset, 0.0) # Default 0 impact if not specified
        curr_weight = weights.get(asset, 0.0)
        asset_assumptions = db_assumptions.get(asset, {"base_win_rate": 0.55, "upside": 0.30, "max_dd": 0.20})
        
        res = advisor.evaluate_position(asset, curr_weight, impact, asset_assumptions)
        
        # Color coding Actions (ANSI codes)
        color = ""
        if res['action'] in ['REDUCE', 'LIQUIDATE']: color = "\033[91m"
        elif res['action'] == 'ADD': color = "\033[92m"
        reset = "\033[0m"
        
        curr_w_str = f"{res['current_weight']*100:>5.1f}%"
        rec_w_str = f"{res['recommended_weight']*100:>5.1f}%"
        
        print(f"{asset:<6} | {res['impact_score']:>7.2f}% | {res['original_P_win']:>3.2f}->{res['new_P_win']:<4.2f} | {curr_w_str:<8} | {rec_w_str:<8} | {color}{res['action']:<10}{reset}")
    
    print("=" * 75 + "\n")
