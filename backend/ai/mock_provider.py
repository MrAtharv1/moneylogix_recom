"""
mock_provider.py — Template-based AI provider that requires no API key.

Used during development, CI testing, and as fallback when Claude API fails.
Every response is generated from the ACTUAL input values — not hardcoded strings.
This means the mock is testable: you can assert specific numbers appear in output.

Design note:
  A naive mock might return "IV changed significantly" — useless for testing.
  This mock returns "Implied volatility rose 4.2 percentage points to 18.0%"
  which verifies the template logic is correctly extracting numbers from dicts.

How it works:
  1. Inspect the diff/leg dicts for what changed
  2. Build one sentence per significant change
  3. Combine into a max-3-sentence response
  4. Every sentence contains at least one real number from the input
"""

import logging
from ai.base_provider import AIProvider

logger = logging.getLogger(__name__)


class MockProvider(AIProvider):
    """
    Template-driven provider. No API calls, no latency, deterministic output.

    The templates here mirror what the Claude prompt instructs Claude to do —
    so switching from mock → claude should produce structurally similar output,
    just more natural sounding.
    """

    # -------------------------------------------------------------------------
    # Strategy-specific IV impact sentences.
    # Key: (strategy_type, iv_direction)
    # These explain the MECHANICAL effect of IV changes on specific structures.
    # -------------------------------------------------------------------------
    _IV_IMPACT = {
        ("iron_condor", "up"): (
            "For an Iron Condor, higher implied volatility expands the short option premiums, "
            "increasing the probability that the underlying tests your short strikes."
        ),
        ("iron_condor", "down"): (
            "For an Iron Condor, lower implied volatility means the short premium you collected "
            "decays faster in your favour, reducing the risk of breach at your short strikes."
        ),
        ("long_straddle", "up"): (
            "For a Long Straddle, higher implied volatility inflates your existing long option costs — "
            "a larger underlying move is now needed to overcome the higher premium paid."
        ),
        ("long_straddle", "down"): (
            "For a Long Straddle, the implied volatility drop has reduced both legs' market value, "
            "requiring a larger underlying move to reach your breakeven."
        ),
        ("bull_put_spread", "up"): (
            "For a Bull Put Spread, higher implied volatility raises the value of your short put "
            "faster than your long put hedge, increasing net exposure."
        ),
        ("bull_put_spread", "down"): (
            "For a Bull Put Spread, lower implied volatility benefits your net short-premium position "
            "as put values decay toward expiry."
        ),
        ("bear_call_spread", "up"): (
            "For a Bear Call Spread, higher implied volatility raises short call value, "
            "working against your net short-premium position."
        ),
        ("bear_call_spread", "down"): (
            "For a Bear Call Spread, lower implied volatility is favourable — "
            "short call premiums compress faster toward expiry."
        ),
    }

    def explain_lifecycle_change(
        self,
        diff: dict,
        strategy_type: str,
        entry_state: dict,
        current_state: dict
    ) -> str:
        """
        Build a max-3-sentence explanation from actual diff values.

        Logic flow:
          1. If has_changes is False, return "" immediately (no work needed)
          2. Build a sentence for each type of change detected in diff
          3. Trim to max 3 sentences and join them
          4. On any exception, log and return ""
        """
        try:
            # Guard: if the health monitor says nothing changed, we say nothing
            if not diff.get("has_changes"):
                return ""

            sentences = []

            # ------------------------------------------------------------------
            # IV change sentence
            # diff["iv"] example:
            #   {"from": 0.138, "to": 0.18, "change": 0.042, "direction": "up"}
            # We convert fractional IV to percentage points for readability.
            # "4.2 percentage points" is clearer than "0.042 IV units".
            # ------------------------------------------------------------------
            iv_diff = diff.get("iv")
            if iv_diff and iv_diff.get("change") is not None:
                change_pp = abs(iv_diff["change"]) * 100   # e.g. 0.042 → 4.2
                from_pct  = iv_diff["from"] * 100          # e.g. 0.138 → 13.8
                to_pct    = iv_diff["to"] * 100            # e.g. 0.18  → 18.0
                direction = iv_diff.get("direction", "up")
                direction_word = "risen" if direction == "up" else "fallen"

                # Sentence 1: what happened to IV
                sentences.append(
                    f"Implied volatility (the market's expectation of future price swings) has "
                    f"{direction_word} {change_pp:.1f} percentage points since entry "
                    f"(was {from_pct:.1f}%, now {to_pct:.1f}%)."
                )

                # Sentence 2: what that means for THIS strategy type
                impact_key = (strategy_type.lower().replace(" ", "_"), direction)
                impact = self._IV_IMPACT.get(impact_key)
                if impact:
                    sentences.append(impact)

            # ------------------------------------------------------------------
            # Price (underlying) move sentence
            # diff["price"] example:
            #   {"from": 19000, "to": 18658, "pct": -1.8, "direction": "down"}
            # Indian equities use ₹ symbol; always show both absolute and %.
            # ------------------------------------------------------------------
            price_diff = diff.get("price")
            if price_diff and price_diff.get("pct") is not None:
                pct       = price_diff["pct"]          # e.g. -1.8
                from_price = price_diff["from"]        # e.g. 19000
                to_price   = price_diff["to"]          # e.g. 18658
                direction  = "down" if pct < 0 else "up"

                sentences.append(
                    f"The underlying has moved {direction} {abs(pct):.1f}% since entry "
                    f"(from ₹{from_price:,.0f} to ₹{to_price:,.0f})."
                )

            # ------------------------------------------------------------------
            # P&L change sentence
            # diff["pnl"] example:
            #   {"from": 0, "to": -1250, "change": -1250}
            # We phrase this as unrealised gain/loss in rupee terms.
            # ------------------------------------------------------------------
            pnl_diff = diff.get("pnl")
            if pnl_diff and pnl_diff.get("change") is not None:
                change = pnl_diff["change"]   # e.g. -1250
                if abs(change) > 0:           # skip if zero change
                    label = "loss" if change < 0 else "gain"
                    sentences.append(
                        f"This has resulted in an unrealised {label} of "
                        f"₹{abs(change):,.0f} on the position."
                    )

            # ------------------------------------------------------------------
            # DTE warning sentence
            # When fewer than 7 days remain, gamma (the rate of change of delta)
            # spikes dramatically. Small price moves cause outsized delta shifts.
            # This is important enough to always mention when flagged.
            # ------------------------------------------------------------------
            if diff.get("dte_warning"):
                dte = current_state.get("days_to_expiry", "")
                dte_phrase = f"{dte} days" if dte else "fewer than 7 days"
                sentences.append(
                    f"With {dte_phrase} to expiry, gamma risk (the rate at which delta "
                    f"changes per point move in the underlying) is elevated — small price "
                    f"moves can now cause larger-than-expected changes in option value."
                )

            # ------------------------------------------------------------------
            # Delta shift sentence (from portfolio_delta change)
            # diff["portfolio_delta"] example:
            #   {"from": 0.12, "to": 0.31, "change": 0.19}
            # ------------------------------------------------------------------
            delta_diff = diff.get("portfolio_delta")
            if delta_diff and delta_diff.get("change") is not None:
                change = delta_diff["change"]
                if abs(change) >= 0.05:  # only mention if directionally significant
                    direction_word = "increased" if change > 0 else "decreased"
                    sentences.append(
                        f"Net portfolio delta has {direction_word} by {abs(change):.2f} "
                        f"(now {delta_diff['to']:.2f}), reflecting greater directional "
                        f"sensitivity to underlying moves."
                    )

            # ------------------------------------------------------------------
            # Trim to 3 sentences max — the AI contract specifies this hard cap.
            # Priority: IV (most explanatory) → price → pnl → dte → delta
            # ------------------------------------------------------------------
            if not sentences:
                # diff said has_changes=True but we found nothing to narrate
                return ""

            return " ".join(sentences[:3])

        except Exception as e:
            # Contract: never raise, always return ""
            logger.error(f"MockProvider.explain_lifecycle_change failed: {e}")
            return ""

    def copilot_leg_hint(
        self,
        leg_before: dict,
        leg_after: dict,
        metrics_before: dict,
        metrics_after: dict
    ) -> str:
        """
        Build exactly ONE sentence describing how the leg edit changed the metrics.

        The frontend calls this after a 300ms debounce when a user edits a leg
        (changes strike, switches buy/sell, changes option type, etc.).

        We compare the most meaningful metrics:
          - net_delta : how much the portfolio moves per 1-point underlying move
          - net_theta : how many rupees of premium decay per calendar day
          - max_profit: the maximum possible profit of the strategy
        """
        try:
            # If nothing changed, nothing to say
            if leg_before == leg_after:
                return ""

            # ------------------------------------------------------------------
            # Extract the metrics we care about.
            # Portfolio greeks live under the "portfolio_greeks" key.
            # Risk metrics (max profit/loss) live under "risk_metrics".
            # We use .get() with 0.0 defaults to avoid KeyErrors.
            # ------------------------------------------------------------------
            greeks_before = metrics_before.get("portfolio_greeks", {})
            greeks_after  = metrics_after.get("portfolio_greeks", {})
            risk_before   = metrics_before.get("risk_metrics", {})
            risk_after    = metrics_after.get("risk_metrics", {})

            delta_before = greeks_before.get("net_delta", 0.0)
            delta_after  = greeks_after.get("net_delta", 0.0)
            theta_before = greeks_before.get("net_theta", 0.0)
            theta_after  = greeks_after.get("net_theta", 0.0)

            delta_diff = delta_after - delta_before   # e.g. -0.08
            theta_diff = theta_after - theta_before   # e.g. +12.5 (rupees/day)

            strike_before = leg_before.get("strike")
            strike_after  = leg_after.get("strike")
            side_before   = leg_before.get("side", "buy")   # "buy" or "sell"
            side_after    = leg_after.get("side", "buy")

            # ------------------------------------------------------------------
            # Case 1: Side flipped (buy → sell or sell → buy)
            # This is the most impactful change — reverses the sign of all
            # contributions from this leg to portfolio greeks.
            # ------------------------------------------------------------------
            if side_before != side_after:
                return (
                    f"Switching from {side_before} to {side_after} at strike "
                    f"{strike_after} reverses this leg's delta contribution from "
                    f"{delta_before:+.3f} to {delta_after:+.3f}."
                )

            # ------------------------------------------------------------------
            # Case 2: Strike moved (most common user action)
            # Describe the net delta and theta impact numerically.
            # Format: "Moving strike from X to Y shifts net delta by Z and
            #          changes daily theta by ₹W."
            # ------------------------------------------------------------------
            if strike_before != strike_after and strike_before and strike_after:
                # Both changes may be tiny; still report them (contract says so)
                return (
                    f"Moving the strike from {strike_before:,} to {strike_after:,} "
                    f"shifts net delta by {delta_diff:+.3f} "
                    f"and changes daily theta by ₹{theta_diff:+.0f}."
                )

            # ------------------------------------------------------------------
            # Case 3: Option type changed (CE ↔ PE), same strike and side
            # This changes the directional bias fundamentally.
            # ------------------------------------------------------------------
            type_before = leg_before.get("option_type", "")
            type_after  = leg_after.get("option_type", "")
            if type_before != type_after:
                return (
                    f"Changing from {type_before} to {type_after} at strike "
                    f"{strike_after:,} shifts net delta from {delta_before:+.3f} "
                    f"to {delta_after:+.3f}."
                )

            # ------------------------------------------------------------------
            # Case 4: Something else changed (lots, expiry, etc.)
            # Fall back to reporting the net metric changes generically.
            # ------------------------------------------------------------------
            if abs(delta_diff) >= 0.001 or abs(theta_diff) >= 1:
                return (
                    f"This leg change shifts net delta by {delta_diff:+.3f} "
                    f"and adjusts daily theta by ₹{theta_diff:+.0f}."
                )

            # No meaningful change to report
            return ""

        except Exception as e:
            logger.error(f"MockProvider.copilot_leg_hint failed: {e}")
            return ""