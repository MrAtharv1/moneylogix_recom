"""
copilot.py — Public API for the inline leg-edit copilot.

This is the ONLY module the FastAPI route imports when it needs an inline hint.
The route is POST /copilot/hint, called after a 300ms debounce from the frontend
whenever the user edits a leg in the strategy builder.

Call site (in main.py):
    from ai.copilot import get_leg_hint

    @app.post("/copilot/hint")
    async def copilot_hint(request: CopilotHintRequest):
        hint = get_leg_hint(
            leg_before=request.leg_before,
            leg_after=request.leg_after,
            metrics_before=request.metrics_before,
            metrics_after=request.metrics_after
        )
        return {"hint": hint}

Why the 300ms debounce?
  Users typically type a new strike number digit by digit: 19, 192, 1925, 19250.
  Without debouncing, each keystroke fires an AI call. The debounce collapses
  that into a single call once the user pauses. This module is stateless —
  the debounce lives entirely in the frontend.

This module mirrors the structure of explainer.py:
  - Fast path check (legs identical → return "")
  - Delegate to provider
  - Double try/except for full error isolation
  - Always returns str, never raises
"""

import logging
from ai.base_provider import get_provider

logger = logging.getLogger(__name__)


def get_leg_hint(
    leg_before: dict,
    leg_after: dict,
    metrics_before: dict,
    metrics_after: dict
) -> str:
    """
    Returns one factual sentence about how the leg edit affected the metrics.

    Args:
        leg_before    : Leg dict before the user's edit.
                        Keys: strike (int), side ("buy"/"sell"),
                              option_type ("CE"/"PE"), lots (int), expiry (str)

        leg_after     : Same structure, after the user's edit.
                        May differ in any subset of keys.

        metrics_before: Full strategy metrics dict before the edit.
                        Nested: {"portfolio_greeks": {"net_delta", "net_theta", ...},
                                 "risk_metrics": {"max_profit", "max_loss", ...}, ...}

        metrics_after : Same structure, recomputed after the edit.

    Returns:
        str : Exactly one sentence with specific numbers from the metrics.
              "" if:
                - leg_before == leg_after (no edit happened)
                - No meaningful metric change to report
                - Any error occurs

    Never raises. The route handler catches any remaining exceptions at its level.
    """
    # ------------------------------------------------------------------
    # Fast path: identical legs mean no edit, no hint needed.
    # This check is duplicated in each provider implementation, but doing
    # it here too avoids even instantiating the provider on a no-op call,
    # which matters during rapid frontend state transitions.
    # ------------------------------------------------------------------
    if leg_before == leg_after:
        return ""

    try:
        provider = get_provider()
        result = provider.copilot_leg_hint(
            leg_before, leg_after, metrics_before, metrics_after
        )
        # Ensure we always return a string, never None
        return result if isinstance(result, str) else ""

    except Exception as e:
        # This outer catch handles get_provider() failures (config errors,
        # import failures). Provider-level failures are caught inside each
        # provider's own try/except.
        logger.error(
            f"copilot.get_leg_hint failed completely "
            f"(provider init or unexpected error): {e}"
        )
        return ""