# """
# mock_provider.py — Template-based AI provider that requires no API key.

# Used during development, CI testing, and as fallback when Claude API fails.
# Every response is generated from the ACTUAL input values — not hardcoded strings.
# This means the mock is testable: you can assert specific numbers appear in output.

# Design note:
#   A naive mock might return "IV changed significantly" — useless for testing.
#   This mock returns "Implied volatility rose 4.2 percentage points to 18.0%"
#   which verifies the template logic is correctly extracting numbers from dicts.

# How it works:
#   1. Inspect the diff/leg dicts for what changed
#   2. Build one sentence per significant change
#   3. Combine into a max-3-sentence response
#   4. Every sentence contains at least one real number from the input
# """

# """mock_provider.py — Template-based AI provider that requires no API key."""
# import logging
# from ai.base_provider import AIProvider

# logger = logging.getLogger(__name__)

# class MockProvider(AIProvider):
#     _IV_IMPACT = {
#         ("iron_condor", "up"): "For an Iron Condor, higher implied volatility expands the short option premiums, increasing the probability that the underlying tests your short strikes.",
#         ("iron_condor", "down"): "For an Iron Condor, lower implied volatility means the short premium you collected decays faster in your favour, reducing the risk of breach at your short strikes.",
#         ("long_straddle", "up"): "For a Long Straddle, higher implied volatility inflates your existing long option costs — a larger underlying move is now needed to overcome the higher premium paid.",
#         ("long_straddle", "down"): "For a Long Straddle, the implied volatility drop has reduced both legs' market value, requiring a larger underlying move to reach your breakeven.",
#         ("bull_put_spread", "up"): "For a Bull Put Spread, higher implied volatility raises the value of your short put faster than your long put hedge, increasing net exposure.",
#         ("bull_put_spread", "down"): "For a Bull Put Spread, lower implied volatility benefits your net short-premium position as put values decay toward expiry.",
#         ("bear_put_spread", "up"): "For a Bear Put Spread, higher implied volatility makes the long put more expensive, increasing the cost of entry.",
#         ("bear_put_spread", "down"): "For a Bear Put Spread, lower implied volatility reduces the cost of the long put, improving the risk/reward profile.",
#     }

#     def explain_lifecycle_change(self, diff, strategy_type, entry_state, current_state):
#         if not diff.get("has_changes"):
#             return ""
#         sentences = []
#         iv_diff = diff.get("iv")
#         if iv_diff and iv_diff.get("change") is not None:
#             change_pp = abs(iv_diff["change"]) * 100
#             from_pct = iv_diff["from"] * 100
#             to_pct = iv_diff["to"] * 100
#             direction = iv_diff.get("direction", "up")
#             word = "risen" if direction == "up" else "fallen"
#             sentences.append(
#                 f"Implied volatility (the market's expectation of future price swings) has "
#                 f"{word} {change_pp:.1f} percentage points since entry "
#                 f"(was {from_pct:.1f}%, now {to_pct:.1f}%)."
#             )
#             impact_key = (strategy_type.lower().replace(" ", "_"), direction)
#             impact = self._IV_IMPACT.get(impact_key)
#             if impact:
#                 sentences.append(impact)

#         price_diff = diff.get("price")
#         if price_diff and price_diff.get("pct") is not None:
#             pct = price_diff["pct"]
#             sentences.append(
#                 f"The underlying has moved {'down' if pct < 0 else 'up'} {abs(pct):.1f}% since entry "
#                 f"(from ₹{price_diff['from']:,.0f} to ₹{price_diff['to']:,.0f})."
#             )

#         pnl_diff = diff.get("pnl")
#         if pnl_diff and pnl_diff.get("change") is not None:
#             change = pnl_diff["change"]
#             if abs(change) > 0:
#                 label = "loss" if change < 0 else "gain"
#                 sentences.append(f"This has resulted in an unrealised {label} of ₹{abs(change):,.0f}.")

#         if diff.get("dte_warning"):
#             dte = current_state.get("days_to_expiry", "")
#             sentences.append(
#                 f"With {dte} days to expiry, gamma risk is elevated — small price moves "
#                 f"can cause larger-than-expected changes in option value."
#             )

#         # FIXED: use "delta" key (not "portfolio_delta")
#         delta_diff = diff.get("delta")
#         if delta_diff and delta_diff.get("change") is not None:
#             change = delta_diff["change"]
#             if abs(change) >= 0.05:
#                 word = "increased" if change > 0 else "decreased"
#                 sentences.append(
#                     f"Net portfolio delta has {word} by {abs(change):.2f} "
#                     f"(now {delta_diff['to']:.2f}), reflecting greater directional sensitivity."
#                 )

#         if not sentences:
#             return ""
#         return " ".join(sentences[:3])

#     def copilot_leg_hint(self, leg_before, leg_after, metrics_before, metrics_after):
#         if leg_before == leg_after:
#             return ""
#         changes = []
#         if leg_before.get("strike") != leg_after.get("strike"):
#             changes.append(f"strike from {leg_before['strike']} to {leg_after['strike']}")
#         if leg_before.get("option_type") != leg_after.get("option_type"):
#             changes.append(f"option type from {leg_before.get('option_type')} to {leg_after.get('option_type')}")
#         if leg_before.get("side") != leg_after.get("side"):
#             changes.append(f"side from {leg_before.get('side')} to {leg_after.get('side')}")
#         if leg_before.get("quantity") != leg_after.get("quantity"):
#             changes.append(f"quantity from {leg_before.get('quantity')} to {leg_after.get('quantity')}")
#         if not changes:
#             return ""
#         return f"Leg edit changed {', '.join(changes)}."

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
        
        if not sentences: return ""
        return " ".join(sentences[:3])

    async def copilot_leg_hint(self, leg_before, leg_after, metrics_before, metrics_after):
        if leg_before == leg_after: return ""
        return "Leg edit changed strategy metrics."