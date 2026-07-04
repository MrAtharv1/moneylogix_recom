# """
# base_provider.py — Abstract interface for all AI providers.

# Design philosophy:
#   The AI layer has exactly ONE job: translate numbers the quant engine
#   already computed into plain English. It never generates financial numbers,
#   never gives advice, never says "you should".

#   By coding to this abstract interface, the rest of the system is completely
#   decoupled from whichever AI backend is active. Swapping from mock → Claude
#   (or Claude → Gemini) requires changing exactly ONE value in .env — zero code
#   changes elsewhere.

#   Dependency inversion at its simplest: high-level modules (explainer, copilot)
#   depend on this abstraction; low-level modules (ClaudeProvider, MockProvider)
#   implement it.
# """

# from abc import ABC, abstractmethod


# class AIProvider(ABC):
#     """
#     Abstract base class that every AI provider must implement.

#     Two concrete implementations exist:
#       - MockProvider  : template-based, no API key needed, used during dev/testing
#       - ClaudeProvider: calls Anthropic API, falls back to Mock on any failure

#     The contract for both methods is strict:
#       - Never raise exceptions — return "" on any failure
#       - Never invent numbers — only use values from the input dicts
#       - Never give advice — factual narration only
#     """

#     @abstractmethod
#     def explain_lifecycle_change(
#         self,
#         diff: dict,
#         strategy_type: str,
#         entry_state: dict,   # {iv, spot, pnl, portfolio_delta, days_to_expiry} at trade entry
#         current_state: dict  # same keys, current market values
#     ) -> str:
#         """
#         Explain WHAT changed in the strategy and WHY, mechanically.

#         Called by the WebSocket health monitor when health_monitor.compute_health_diff()
#         detects a meaningful shift (e.g., IV moved >2pp, underlying moved >1%).

#         Input:
#           diff          — HealthDiff dict: {"has_changes": bool, "iv": {...}, "price": {...}, ...}
#           strategy_type — e.g. "iron_condor", "long_straddle", "bull_put_spread"
#           entry_state   — market snapshot at the moment the trader entered the position
#           current_state — same structure, but live/current values

#         Output:
#           A string of at most 3 plain-English sentences.
#           "" if nothing meaningful changed or on any failure.

#         CONTRACT (implementations must enforce ALL of these):
#           ✓ Max 3 sentences — no exceptions
#           ✓ Use ONLY numbers from the input dicts — never estimate or invent
#           ✓ Plain English — define any jargon inline (e.g., "implied volatility (IV), 
#             the market's expectation of future price swings")
#           ✗ NEVER say: "you should", "I recommend", "consider", "you might want to"
#           ✓ Always distinguish price moves from volatility moves — they have
#             different mechanical effects on option strategies
#           ✓ Return "" on any failure — never raise
#         """
#         ...

#     @abstractmethod
#     def copilot_leg_hint(
#         self,
#         leg_before: dict,    # leg dict before the user's edit
#         leg_after: dict,     # leg dict after the user's edit
#         metrics_before: dict, # full metrics response before the edit
#         metrics_after: dict  # full metrics response after the edit
#     ) -> str:
#         """
#         Give ONE factual sentence about how editing a leg affected the strategy metrics.

#         Called by POST /copilot/hint after a 300ms debounce from the frontend.
#         The debounce prevents spamming the AI on every keystroke.

#         Input:
#           leg_before/after    — {"strike": int, "side": "buy"/"sell", "option_type": "CE"/"PE", ...}
#           metrics_before/after — full strategy metrics dict (includes portfolio_greeks, risk_metrics)

#         Output:
#           Exactly ONE sentence containing specific numbers from the metrics.
#           "" if metrics are identical (no meaningful change) or on failure.

#         CONTRACT:
#           ✓ Exactly ONE sentence — no more, no less
#           ✓ Must include at least one specific number from metrics_before or metrics_after
#           ✓ Factual only: "reduces delta by 0.08" NOT "you should reduce delta"
#           ✗ Forbidden words: should, recommend, consider, suggest, avoid, better, worse
#           ✓ Return "" if no meaningful change or on failure
#         """
#         ...


# def get_provider() -> AIProvider:
#     """
#     Factory function — the only import other modules need from this file.

#     Reads AI_PROVIDER from config (which reads from .env) and returns
#     the appropriate provider instance. All callers remain provider-agnostic.

#     Usage (in explainer.py, copilot.py):
#         from ai.base_provider import get_provider
#         provider = get_provider()  # returns Mock or Claude transparently

#     Why instantiate fresh each call?
#       Keeps provider stateless and avoids stale config if settings change
#       at runtime (e.g., during testing). For production, providers are cheap
#       to instantiate — no persistent connections are held.
#     """
#     from config import settings

#     if settings.AI_PROVIDER == "claude":
#         # Only import ClaudeProvider when actually needed — keeps startup
#         # fast and avoids ImportError if anthropic package isn't installed
#         from ai.claude_provider import ClaudeProvider
#         return ClaudeProvider()
#     #other hf apis
#     elif settings.AI_PROVIDER == "huggingface":
#         from ai.hf_provider import HuggingFaceProvider
#         return HuggingFaceProvider()
#     # Default: mock provider works with no API key, no network access
#     from ai.mock_provider import MockProvider
#     return MockProvider()

"""
base_provider.py — Abstract interface for all AI providers.
"""
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

class AIProvider(ABC):
    @abstractmethod
    async def explain_lifecycle_change(
        self, diff: dict, strategy_type: str, entry_state: dict, current_state: dict
    ) -> str:
        ...

    @abstractmethod
    async def copilot_leg_hint(
        self, leg_before: dict, leg_after: dict, metrics_before: dict, metrics_after: dict
    ) -> str:
        ...

# Global singleton instance
_PROVIDER_INSTANCE = None

def init_provider():
    """Called once at startup to instantiate the provider, avoiding import overhead on every tick."""
    global _PROVIDER_INSTANCE
    if _PROVIDER_INSTANCE is not None:
        return

    from config import settings
    if settings.AI_PROVIDER == "claude":
        from ai.claude_provider import ClaudeProvider
        _PROVIDER_INSTANCE = ClaudeProvider()
    elif settings.AI_PROVIDER == "huggingface":
        from ai.hf_provider import HuggingFaceProvider
        _PROVIDER_INSTANCE = HuggingFaceProvider()
    else:
        from ai.mock_provider import MockProvider
        _PROVIDER_INSTANCE = MockProvider()
        
    logger.info(f"Initialized AI Provider: {_PROVIDER_INSTANCE.__class__.__name__}")

def get_provider() -> AIProvider:
    global _PROVIDER_INSTANCE
    if _PROVIDER_INSTANCE is None:
        init_provider()
    return _PROVIDER_INSTANCE