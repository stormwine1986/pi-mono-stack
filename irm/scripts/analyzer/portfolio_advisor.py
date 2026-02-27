import argparse
import json

class KellyAdvisor:
    def __init__(self, kelly_fraction=0.5):
        """
        :param kelly_fraction: 0.5 for Half-Kelly, 0.25 for Quarter-Kelly.
                               Essential for long-term investments to avoid ruin.
        """
        self.kelly_fraction = kelly_fraction
        
        # Base long-term assumptions for assets (b = CAGR / Max Drawdown)
        # Ideally this comes from the database/schema directly. 
        # Here we mock it for demonstration.
        # Base long-term assumptions for assets (b = Expected 3-5Yr Upside / Expected Max Drawdown)
        # In a realistic environment, these come from expert estimates or historical distributions.
        self.base_assumptions = {
            "QQQM": {"base_win_rate": 0.70, "upside": 0.40, "max_dd": 0.20},  # b = 2.0
            "NVDA": {"base_win_rate": 0.65, "upside": 0.80, "max_dd": 0.40},  # b = 2.0
            "PLTR": {"base_win_rate": 0.60, "upside": 1.20, "max_dd": 0.50},  # b = 2.4
            "GOLD": {"base_win_rate": 0.60, "upside": 0.20, "max_dd": 0.10},  # b = 2.0
            "BTC":  {"base_win_rate": 0.55, "upside": 1.50, "max_dd": 0.60},  # b = 2.5
        }

    def _calculate_b(self, asset):
        """Calculate Long-term payoff ratio 'b' (Upside / Max Drawdown)"""
        assumptions = self.base_assumptions.get(asset, {"base_win_rate": 0.5, "upside": 0.2, "max_dd": 0.2})
        if assumptions["max_dd"] == 0:
            return 1.0
        return assumptions["upside"] / assumptions["max_dd"]

    def evaluate_position(self, asset, current_weight, impact_score, penalty_multiplier=0.01):
        """
        Evaluate optimal position size based on ontology impact score.
        :param asset: Ticker symbol
        :param current_weight: Current portfolio weight (0.0 to 1.0)
        :param impact_score: Impact score output from tracer.py (e.g. -19.01 for QQQM)
        :param penalty_multiplier: How much 1 point of impact score drops the win rate.
        """
        assumptions = self.base_assumptions.get(asset, {"base_win_rate": 0.5, "upside": 0.2, "max_dd": 0.2})
        base_p = assumptions["base_win_rate"]
        b = self._calculate_b(asset)

        # 1. Update Bayesian Probability based on Impact Score
        # Impact represents expected NAV shock magnitude. 
        # Asymmetric adjustment: Negative impacts destroy probability faster than positive impacts build it.
        if impact_score < 0:
            probability_adj = impact_score * 0.005  # e.g., -100% impact -> -0.5 to win rate
        else:
            probability_adj = impact_score * 0.002  # e.g., +100% impact -> +0.2 to win rate
            
        new_p = max(0.01, min(0.99, base_p + probability_adj)) # bounded between 1% and 99%
        new_q = 1.0 - new_p

        # 2. Raw Kelly Formula: f* = (bp - q) / b = p - (1-p)/b
        raw_kelly = new_p - (new_q / b) if b > 0 else 0
        
        # Math constraint: Kelly can be negative (meaning short the asset or hold 0)
        raw_kelly = max(0.0, raw_kelly)

        # 3. Apply Fractional Kelly for survival
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
    parser.add_argument("--impacts", type=str, required=True, help="JSON string of asset impacts. e.g. '{\"QQQM\": -19.01, \"NVDA\": -8.21}'")
    parser.add_argument("--weights", type=str, required=True, help="JSON string of current weights. e.g. '{\"QQQM\": 0.35, \"NVDA\": 0.25}'")
    parser.add_argument("--fraction", type=float, default=0.5, help="Kelly fraction (default 0.5 Half-Kelly)")
    
    args = parser.parse_args()
    
    try:
        impacts = json.loads(args.impacts)
        weights = json.loads(args.weights)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON inputs: {e}")
        exit(1)
        
    advisor = KellyAdvisor(kelly_fraction=args.fraction)
    
    print("\n" + "="*20 + " KELLY CRITERION POSITION ADVISOR " + "="*20)
    print(f"Mode: {args.fraction}-Kelly")
    print("-" * 68)
    print(f"{'Asset':<6} | {'Impact':<8} | {'WinRate':<7} | {'Curr Wt':<8} | {'Rec Wt':<8} | {'ACTION':<10}")
    print("-" * 68)
    
    for asset, impact in impacts.items():
        curr_weight = weights.get(asset, 0)
        res = advisor.evaluate_position(asset, curr_weight, impact)
        
        action_col = "\033[91m" if res['action'] in ['REDUCE', 'LIQUIDATE'] else "\033[92m" if res['action'] == 'ADD' else "\033[0m"
        
        # Format the weight display properly
        curr_w_str = f"{res['current_weight']*100:.1f}%"
        rec_w_str = f"{res['recommended_weight']*100:.1f}%"
        
        print(f"{asset:<6} | {res['impact_score']:>7.2f}% | {res['original_P_win']:>3.2f}->{res['new_P_win']:<4.2f} | {curr_w_str:<8} | {rec_w_str:<8} | {action_col}{res['action']:<10}\033[0m")
        
        if res['action'] in ['REDUCE', 'LIQUIDATE']:
             print(f"  > [Advice] {asset} probability of compounding severely damaged by impact ({res['impact_score']}%). Target size reduced by {-res['suggested_delta']*100:.1f}%.")
        elif res['action'] == 'ADD':
             print(f"  > [Advice] {asset} fundamental outlook improved (Impact: +{res['impact_score']}%). Target size increased by {res['suggested_delta']*100:.1f}%.")
    
    print("=" * 68)
