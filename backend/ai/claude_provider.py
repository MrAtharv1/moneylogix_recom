"""
claude_provider.py — Claude API-backed AI provider.

Uses Anthropic's claude-sonnet-4-6 model for natural-language explanations.
Falls back to MockProvider on ANY API failure — network errors, auth errors,
rate limits, malformed responses — none of these ever surface as 500 errors.

Switch to this provider by setting in .env:
    AI_PROVIDER=claude
    ANTHROPIC_API_KEY=sk-ant-...

Design note on prompt engineering:
  The system prompts use absolute prohibitions ("NEVER say X") rather than
  soft guidance ("try to avoid X"). This is intentional — SEBI compliance
  requires that no AI output can be construed as investment advice. A weak
  prompt risks the model slipping in a "you might want to consider..." which
  could constitute unlicensed financial advice.
"""

import logging
import anthropic

from ai.base_provider import AIProvider

logger = logging.getLogger(__name__)


# =============================================================================
# SYSTEM PROMPTS
# =============================================================================
# These are injected as the "system" role in every Claude API call.
# They define the persona, hard constraints, and output format.
# Keeping them as module-level constants makes them easy to version/test.

LIFECYCLE_SYSTEM_PROMPT = """You explain options strategy mechanics to retail traders in India.

ABSOLUTE RULES — violating any of these makes the response unusable:
1. Use ONLY numbers from the data provided. Never estimate or invent figures.
2. Max 3 sentences total. No exceptions. Do not split a thought across 4 sentences.
3. Plain English. If you use a term like "implied volatility", define it inline
   in the same sentence, e.g. "implied volatility (the market's expectation of
   future price swings)".
4. NEVER say: "you should", "I recommend", "consider", "you might want to",
   "it would be wise", "I suggest", or any directive language whatsoever.
5. Always explain WHY mechanically — state the cause and its mechanical effect.
   Example: "IV dropped → short option premiums compress → theta decay accelerates"
6. Distinguish price moves from volatility moves. They affect strategies differently:
   - Price move: affects delta (directional exposure)
   - IV move: affects vega (volatility exposure) and overall premium levels
7. End with one factual observation. Never a suggestion or call to action.
8. If the data shows no significant changes, respond with exactly: ""

You are a mechanics explainer, not an advisor. Your output is displayed in a
live trading dashboard. A SEBI-registered broker is responsible for this platform."""


COPILOT_SYSTEM_PROMPT = """You give exactly one factual sentence about how changing an
options leg affects the strategy's risk metrics.

ABSOLUTE RULES:
1. ONE sentence only. Period. No follow-up. No context. One sentence.
2. The sentence must contain at least one specific number from the metrics provided.
3. Describe what changed factually. Do not say what the trader should do.
4. Forbidden words: should, avoid, better, worse, recommend, consider, suggest,
   might want, could help, advisable.
5. Even if the metrics change is tiny (e.g., 0.001 delta), still state it factually.
6. If leg_before equals leg_after exactly, respond with exactly: ""

This output appears inline in a strategy builder UI after a 300ms debounce.
It is a factual readout, not advice."""


class ClaudeProvider(AIProvider):
    """
    Production AI provider that calls the Anthropic Claude API.

    Instantiation reads ANTHROPIC_API_KEY from settings. The anthropic client
    handles retries internally; we add one outer try/except that catches
    everything and falls back to MockProvider.
    """

    def __init__(self):
        from config import settings
        # anthropic.Anthropic() will raise if the key is clearly malformed,
        # but we catch that in each method, not here, so __init__ stays fast.
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        # Always pin the model string — never use "latest" in production.
        # This ensures deterministic behaviour across deployments.
        self.model = "claude-3-5-sonnet-20240620"

    # -------------------------------------------------------------------------
    # LIFECYCLE EXPLAINER
    # -------------------------------------------------------------------------

    def explain_lifecycle_change(
        self,
        diff: dict,
        strategy_type: str,
        entry_state: dict,
        current_state: dict
    ) -> str:
        """
        Ask Claude to explain what changed in the strategy and why.

        We pass the raw diff dict and both states as structured data.
        Claude is instructed (via system prompt) to only use numbers from
        these inputs — never to hallucinate figures.

        Token budget: 150 max_tokens
          At ~4 chars/token, 150 tokens ≈ ~600 chars ≈ 3 average sentences.
          This enforces the 3-sentence contract at the API level, not just
          in the prompt.
        """
        # Early exit: don't spend an API call if there's nothing to explain
        if not diff.get("has_changes"):
            return ""

        try:
            # ------------------------------------------------------------------
            # Build the user message.
            # We give Claude the strategy type (so it knows the payoff structure),
            # the entry state (so it can compute what changed relative to entry),
            # the current state (current market values), and the pre-computed diff
            # (so it doesn't have to calculate — just narrate).
            # ------------------------------------------------------------------
            prompt = f"""Strategy type: {strategy_type}

State at entry (when trade was placed):
  - Implied volatility: {entry_state.get('iv', 'N/A')}
  - Underlying spot price: ₹{entry_state.get('spot', 'N/A'):,}
  - Portfolio delta: {entry_state.get('portfolio_delta', 'N/A')}
  - Days to expiry: {entry_state.get('days_to_expiry', 'N/A')}
  - Unrealised P&L: ₹{entry_state.get('pnl', 0):,}

Current state (now):
  - Implied volatility: {current_state.get('iv', 'N/A')}
  - Underlying spot price: ₹{current_state.get('spot', 'N/A'):,}
  - Portfolio delta: {current_state.get('portfolio_delta', 'N/A')}
  - Days to expiry: {current_state.get('days_to_expiry', 'N/A')}
  - Unrealised P&L: ₹{current_state.get('pnl', 0):,}

Pre-computed changes (health diff): {diff}

Explain mechanically what happened to this {strategy_type} and why these changes occurred."""

            response = self.client.messages.create(
                model=self.model,
                max_tokens=150,          # Hard cap: enforces 3-sentence limit
                system=LIFECYCLE_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )

            # response.content is a list of content blocks; we want the text block.
            # In practice for this use case there will always be exactly one text block.
            text = response.content[0].text.strip()

            # If Claude returns the literal string "" (as instructed for no-change),
            # treat it as empty — don't send quotes to the frontend
            return "" if text in ('""', "''", "") else text

        except Exception as e:
            # Log the failure but NEVER let it propagate.
            # The WebSocket loop must not crash because of an AI failure.
            logger.warning(
                f"Claude API failed for lifecycle explanation: {type(e).__name__}: {e}. "
                f"Falling back to MockProvider."
            )
            from ai.mock_provider import MockProvider
            return MockProvider().explain_lifecycle_change(
                diff, strategy_type, entry_state, current_state
            )

    # -------------------------------------------------------------------------
    # COPILOT LEG HINT
    # -------------------------------------------------------------------------

    def copilot_leg_hint(
        self,
        leg_before: dict,
        leg_after: dict,
        metrics_before: dict,
        metrics_after: dict
    ) -> str:
        """
        Ask Claude for one sentence about how a leg edit affected the metrics.

        Token budget: 80 max_tokens
          One sentence is typically 20-30 tokens. 80 gives comfortable headroom
          without risk of verbose output.

        We pre-extract the most important metrics into the prompt rather than
        dumping the entire metrics dict. This:
          1. Reduces tokens (cheaper, faster)
          2. Focuses Claude on what matters (delta, theta, max profit)
          3. Reduces risk of Claude hallucinating from irrelevant data
        """
        # If the leg didn't change at all, no hint needed
        if leg_before == leg_after:
            return ""

        try:
            # ------------------------------------------------------------------
            # Pre-extract the key metrics for the prompt.
            # We pull from the nested structure: metrics["portfolio_greeks"]["net_delta"]
            # Using None as sentinel so Claude can see "N/A" rather than "0"
            # when data is genuinely missing.
            # ------------------------------------------------------------------
            greeks_before = metrics_before.get("portfolio_greeks", {})
            greeks_after  = metrics_after.get("portfolio_greeks", {})
            risk_before   = metrics_before.get("risk_metrics", {})
            risk_after    = metrics_after.get("risk_metrics", {})

            prompt = f"""Leg before edit: {leg_before}
Leg after edit:  {leg_after}

Metrics before edit:
  - Net delta (directional exposure):  {greeks_before.get('net_delta', 'N/A')}
  - Net theta (daily time decay, ₹):   {greeks_before.get('net_theta', 'N/A')}
  - Max profit (₹):                    {risk_before.get('max_profit', 'N/A')}
  - Max loss (₹):                      {risk_before.get('max_loss', 'N/A')}

Metrics after edit:
  - Net delta:   {greeks_after.get('net_delta', 'N/A')}
  - Net theta:   {greeks_after.get('net_theta', 'N/A')}
  - Max profit:  {risk_after.get('max_profit', 'N/A')}
  - Max loss:    {risk_after.get('max_loss', 'N/A')}

One factual sentence about how this specific leg change affected the metrics."""

            response = self.client.messages.create(
                model=self.model,
                max_tokens=80,
                system=COPILOT_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )

            text = response.content[0].text.strip()
            return "" if text in ('""', "''", "") else text

        except Exception as e:
            logger.warning(
                f"Claude API failed for copilot hint: {type(e).__name__}: {e}. "
                f"Falling back to MockProvider."
            )
            from ai.mock_provider import MockProvider
            return MockProvider().copilot_leg_hint(
                leg_before, leg_after, metrics_before, metrics_after
            )