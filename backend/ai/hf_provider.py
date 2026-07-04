import os
import logging
from huggingface_hub import AsyncInferenceClient
from ai.base_provider import AIProvider
from ai.claude_provider import LIFECYCLE_SYSTEM_PROMPT, COPILOT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

class HuggingFaceProvider(AIProvider):
    def __init__(self):
        from config import settings
        api_key = getattr(settings, "HUGGINGFACE_API_KEY", "") or os.getenv("HUGGINGFACE_API_KEY", "")
        if not api_key:
            logger.warning("HUGGINGFACE_API_KEY not found.")

        self.client = AsyncInferenceClient(
            model="meta-llama/Meta-Llama-3-8B-Instruct",
            token=api_key
        )

    async def explain_lifecycle_change(self, diff: dict, strategy_type: str, entry_state: dict, current_state: dict) -> str:
        if not diff.get("has_changes"):
            return ""
            
        try:
            prompt = f"Strategy type: {strategy_type}\nEntry state: {entry_state}\nCurrent state: {current_state}\nHealth diff: {diff}\n\nExplain mechanically what happened to this strategy and why."
            messages = [{"role": "system", "content": LIFECYCLE_SYSTEM_PROMPT}, {"role": "user", "content": prompt}]
            
            response = await self.client.chat_completion(messages=messages, max_tokens=150, temperature=0.3)
            text = response.choices[0].message.content.strip()
            return "" if text in ('""', "''", "") else text
            
        except Exception as e:
            logger.warning(f"HuggingFace API failed for lifecycle: {e}. Cascading fallback to mock engine.")
            from ai.mock_provider import MockProvider
            return await MockProvider().explain_lifecycle_change(diff, strategy_type, entry_state, current_state)

    async def copilot_leg_hint(self, leg_before: dict, leg_after: dict, metrics_before: dict, metrics_after: dict) -> str:
        try:
            prompt = f"Leg before: {leg_before}\nLeg after: {leg_after}\nMetrics before: {metrics_before.get('portfolio_greeks', {})}\nMetrics after: {metrics_after.get('portfolio_greeks', {})}\n\nOne factual sentence about how this leg change affected the metrics."
            messages = [{"role": "system", "content": COPILOT_SYSTEM_PROMPT}, {"role": "user", "content": prompt}]
            
            response = await self.client.chat_completion(messages=messages, max_tokens=80, temperature=0.1)
            text = response.choices[0].message.content.strip()
            return "" if text in ('""', "''", "") else text
            
        except Exception as e:
            logger.warning(f"HuggingFace API failed for copilot hint: {e}. Cascading fallback to mock engine.")
            from ai.mock_provider import MockProvider
            return await MockProvider().copilot_leg_hint(leg_before, leg_after, metrics_before, metrics_after)