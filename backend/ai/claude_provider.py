import logging
from anthropic import AsyncAnthropic
from ai.base_provider import AIProvider

logger = logging.getLogger(__name__)

LIFECYCLE_SYSTEM_PROMPT = """You explain options strategy mechanics to retail traders in India.
ABSOLUTE RULES:
1. Use ONLY numbers from the data provided. Never estimate or invent figures.
2. Max 3 sentences total.
3. Plain English. Define jargon inline.
4. NEVER say: "you should", "I recommend", "consider", "you might want to", etc.
5. Always explain WHY mechanically.
6. Distinguish price moves from volatility moves.
7. End with one factual observation. Never a suggestion.
8. If the data shows no significant changes, respond with exactly: ""
You are a mechanics explainer, not an advisor."""

COPILOT_SYSTEM_PROMPT = """You give exactly one factual sentence about how changing an
options leg affects the strategy's risk metrics.
ABSOLUTE RULES:
1. ONE sentence only.
2. Must contain at least one specific number from the metrics provided.
3. Do not say what the trader should do.
4. Forbidden words: should, avoid, better, worse, recommend, consider, suggest.
5. If leg_before equals leg_after exactly, respond with exactly: """""

class ClaudeProvider(AIProvider):
    def __init__(self):
        from config import settings
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-3-5-sonnet-20240620"

    async def explain_lifecycle_change(self, diff, strategy_type, entry_state, current_state):
        if not diff.get("has_changes"):
            return ""
        try:
            def safe_fmt(value, default="N/A"):
                return default if value is None else value

            prompt = f"Strategy type: {strategy_type}\nState at entry:\n  - IV: {safe_fmt(entry_state.get('iv'))}\n  - Spot: ₹{safe_fmt(entry_state.get('spot'), 0):,}\n  - Delta: {safe_fmt(entry_state.get('portfolio_delta'))}\n  - DTE: {safe_fmt(entry_state.get('days_to_expiry'))}\n  - P&L: ₹{safe_fmt(entry_state.get('pnl'), 0):,}\n\nCurrent state:\n  - IV: {safe_fmt(current_state.get('iv'))}\n  - Spot: ₹{safe_fmt(current_state.get('spot'), 0):,}\n  - Delta: {safe_fmt(current_state.get('portfolio_delta'))}\n  - DTE: {safe_fmt(current_state.get('days_to_expiry'))}\n  - P&L: ₹{safe_fmt(current_state.get('pnl'), 0):,}\n\nChanges: {diff}\n\nExplain mechanically what happened and why."
            
            response = await self.client.messages.create(
                model=self.model, max_tokens=150, system=LIFECYCLE_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )
            text = response.content[0].text.strip()
            return "" if text in ('""', "''", "") else text
        except Exception as e:
            logger.warning(f"Claude API failed: {e}. Falling back to mock.")
            from ai.mock_provider import MockProvider
            return await MockProvider().explain_lifecycle_change(diff, strategy_type, entry_state, current_state)

    async def copilot_leg_hint(self, leg_before, leg_after, metrics_before, metrics_after):
        if leg_before == leg_after:
            return ""
        if not metrics_after:
            from ai.mock_provider import MockProvider
            return await MockProvider().copilot_leg_hint(leg_before, leg_after, metrics_before, metrics_after)
        try:
            gb, ga = metrics_before.get("portfolio_greeks", {}), metrics_after.get("portfolio_greeks", {})
            rb, ra = metrics_before.get("risk_metrics", {}), metrics_after.get("risk_metrics", {})
            prompt = f"Leg before: {leg_before}\nLeg after: {leg_after}\nMetrics before:\n  - Delta: {gb.get('net_delta', 'N/A')}\n  - Max profit: {rb.get('max_profit', 'N/A')}\nMetrics after:\n  - Delta: {ga.get('net_delta', 'N/A')}\n  - Max profit: {ra.get('max_profit', 'N/A')}\nOne factual sentence."
            
            response = await self.client.messages.create(
                model=self.model, max_tokens=80, system=COPILOT_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )
            text = response.content[0].text.strip()
            return "" if text in ('""', "''", "") else text
        except Exception as e:
            logger.warning(f"Claude copilot failed: {e}. Falling back to mock.")
            from ai.mock_provider import MockProvider
            return await MockProvider().copilot_leg_hint(leg_before, leg_after, metrics_before, metrics_after)