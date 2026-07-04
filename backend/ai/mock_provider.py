"""
mock_provider.py — Template-based AI provider that requires no API key.
"""
import logging
from ai.base_provider import AIProvider

logger = logging.getLogger(__name__)

class MockProvider(AIProvider):
    _IV_IMPACT = {
        ("iron_condor", "up"): "For an Iron Condor, higher implied volatility expands the short option premiums...",
        ("iron_condor", "down"): "For an Iron Condor, lower implied volatility means the short premium you collected decays faster...",
        ("long_straddle", "up"): "For a Long Straddle, higher implied volatility inflates your existing long option costs — a larger underlying move is now needed to overcome the higher premium paid.",
        ("long_straddle", "down"): "For a Long Straddle, the implied volatility drop has reduced both legs' market value, requiring a larger underlying move to reach your breakeven.",
        ("bull_put_spread", "up"): "For a Bull Put Spread, higher implied volatility raises the value of your short put faster than your long put hedge, increasing net exposure.",
        ("bull_put_spread", "down"): "For a Bull Put Spread, lower implied volatility benefits your net short-premium position as put values decay toward expiry.",
        ("bear_put_spread", "up"): "For a Bear Put Spread, higher implied volatility makes the long put more expensive, increasing the cost of entry.",
        ("bear_put_spread", "down"): "For a Bear Put Spread, lower implied volatility reduces the cost of the long put, improving the risk/reward profile.",
    }

    async def explain_lifecycle_change(self, diff, strategy_type, entry_state, current_state):
        if not diff.get("has_changes"):
            return ""
        sentences = []
        iv_diff = diff.get("iv")
        if iv_diff and iv_diff.get("change") is not None:
            sentences.append(f"Implied volatility has {'risen' if iv_diff.get('direction', 'up') == 'up' else 'fallen'} {abs(iv_diff['change']) * 100:.1f} percentage points.")
        if not sentences:
            return ""
        return " ".join(sentences[:3])

    async def copilot_leg_hint(self, leg_before, leg_after, metrics_before, metrics_after):
        if leg_before == leg_after:
            return ""
        return "Leg edit changed strategy metrics."

    # ─── NEW: Dynamic IV Recommendation for the Recommender Panel ──────────
    def get_iv_recommendation(self, strategy_type: str, iv_rank: float, days_to_expiry: int) -> str:
        """
        Returns a dynamic, strategy‑specific IV explanation.
        Different messages for Conservative, Moderate, Aggressive.
        """
        IV_PROFILES = {
            "bull_put_spread":   {"range": (50, 100), "action": "selling premium"},
            "iron_condor":       {"range": (60, 100), "action": "selling premium"},
            "bull_call_spread":  {"range": (20, 70),  "action": "moderate volatility"},
            "bear_put_spread":   {"range": (20, 70),  "action": "moderate volatility"},
            "long_straddle":     {"range": (0, 40),   "action": "buying volatility"},
            "long_strangle":     {"range": (0, 45),   "action": "buying volatility"},
            "covered_call":      {"range": (50, 100), "action": "selling premium"},
        }

        profile = IV_PROFILES.get(strategy_type, {"range": (0, 100), "action": "trading"})
        low, high = profile["range"]
        action = profile["action"]

        if low <= iv_rank <= high:
            return f"IV Rank {iv_rank:.0f}/100 is in the ideal range of {low}–{high} for {action}. This is a favorable entry point."
        elif iv_rank < low:
            return f"IV Rank {iv_rank:.0f}/100 is below the ideal range of {low}–{high} for {action}. Options are cheap – consider waiting if you're selling premium."
        else:
            return f"IV Rank {iv_rank:.0f}/100 is above the ideal range of {low}–{high} for {action}. Options are expensive – good for selling, bad for buying."