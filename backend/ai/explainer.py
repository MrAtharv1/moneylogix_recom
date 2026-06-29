"""
explainer.py — Public API for the lifecycle health-change explainer.

This is the ONLY module the WebSocket health monitor imports from when it
needs an AI explanation. It never imports mock_provider or claude_provider
directly — the provider is resolved at call time by get_provider().

Call site (in main.py WebSocket loop):
    from ai.explainer import explain_health_change

    if health_monitor.should_trigger_explanation(diff):
        explanation = explain_health_change(
            diff=diff,
            strategy_type=entry["strategy_type"],
            entry_state=entry["entry_state"],
            current_state=current_state
        )
        payload["explanation"] = explanation

Design principles:
  - This module is a thin wrapper: it validates the fast path (no changes →
    return "" without touching the provider) and delegates everything else.
  - Double try/except: the provider already catches its own errors, but we
    add an outer catch so even an unexpected error in get_provider() itself
    (e.g., misconfigured .env) doesn't crash the WebSocket loop.
  - Returns "" on ALL failures — the WebSocket loop must never crash because
    of an AI layer problem.
"""

import logging
from ai.base_provider import get_provider

logger = logging.getLogger(__name__)


def explain_health_change(
    diff: dict,
    strategy_type: str,
    entry_state: dict,
    current_state: dict
) -> str:
    """
    Returns a plain-English explanation of what changed in the strategy and why.

    Args:
        diff          : HealthDiff dict produced by health_monitor.compute_health_diff().
                        Must contain at least {"has_changes": bool}.
                        May also contain keys: "iv", "price", "pnl", "dte_warning",
                        "portfolio_delta", each with from/to/change subdicts.

        strategy_type : Identifies the payoff structure so the AI can explain
                        the type-specific mechanical impact.
                        Examples: "iron_condor", "long_straddle", "bull_put_spread"

        entry_state   : Market snapshot at the moment the trade was entered.
                        Keys: iv (float), spot (float), pnl (float),
                              portfolio_delta (float), days_to_expiry (int)

        current_state : Same structure as entry_state, but with current values.

    Returns:
        str  : Up to 3 plain-English sentences. Empty string "" if:
                 - diff has no meaningful changes (has_changes=False)
                 - AI provider returns nothing noteworthy
                 - Any error occurs at any level

    Never raises. The WebSocket loop relies on this guarantee.
    """
    # ------------------------------------------------------------------
    # Fast path: if the health monitor says nothing changed, skip the
    # provider entirely. This avoids unnecessary API calls or template
    # processing for the majority of polling cycles where nothing moves.
    # ------------------------------------------------------------------
    if not diff.get("has_changes"):
        return ""

    try:
        # get_provider() reads AI_PROVIDER from config and returns
        # the appropriate MockProvider or ClaudeProvider instance.
        provider = get_provider()
        result = provider.explain_lifecycle_change(
            diff, strategy_type, entry_state, current_state
        )
        # Ensure we always return a string, never None
        return result if isinstance(result, str) else ""

    except Exception as e:
        # This outer catch handles failures in get_provider() itself,
        # e.g., if config is broken or imports fail. The providers'
        # own try/except blocks handle API-level failures.
        logger.error(
            f"explainer.explain_health_change failed completely "
            f"(provider init or unexpected error): {e}"
        )
        return ""