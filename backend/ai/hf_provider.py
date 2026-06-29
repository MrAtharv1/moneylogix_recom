"""
hf_provider.py — Hugging Face Inference API provider.
Uses a free, open-source model (Llama-3-8B-Instruct) via the HF Serverless API.
"""

import os
import logging
from huggingface_hub import InferenceClient
from ai.base_provider import AIProvider

# Import the system prompts to maintain absolute structural alignment with Claude
from ai.claude_provider import LIFECYCLE_SYSTEM_PROMPT, COPILOT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

class HuggingFaceProvider(AIProvider):
    def __init__(self):
        from config import settings
        
        # Audit Fix: Read from config.py first, fall back directly to os.getenv 
        # to ensure it works even if config.py hasn't explicitly declared the property.
        api_key = getattr(settings, "HUGGINGFACE_API_KEY", "") or os.getenv("HUGGINGFACE_API_KEY", "")

        print(f"\n🚀 SUCCESS: HuggingFace Provider Initialized with Token Length: {len(api_key)}\n")
        
        if not api_key:
            logger.warning("HUGGINGFACE_API_KEY not found in configuration or environment variables.")

        # Initialize the free Serverless Inference Client
        self.client = InferenceClient(
            model="meta-llama/Meta-Llama-3-8B-Instruct",
            token=api_key
        )

    def explain_lifecycle_change(self, diff: dict, strategy_type: str, entry_state: dict, current_state: dict) -> str:
        if not diff.get("has_changes"):
            return ""
            
        try:
            prompt = f"""Strategy type: {strategy_type}
Entry state: {entry_state}
Current state: {current_state}
Health diff: {diff}

Explain mechanically what happened to this strategy and why."""

            messages = [
                {"role": "system", "content": LIFECYCLE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]
            
            response = self.client.chat_completion(
                messages=messages,
                max_tokens=150,
                temperature=0.3  # Low temperature preserves deterministic financial reasoning
            )
            
            text = response.choices[0].message.content.strip()
            return "" if text in ('""', "''", "") else text
            
        except Exception as e:
            logger.warning(f"HuggingFace API failed for lifecycle: {e}. Cascading fallback to mock engine.")
            from ai.mock_provider import MockProvider
            return MockProvider().explain_lifecycle_change(diff, strategy_type, entry_state, current_state)

    def copilot_leg_hint(self, leg_before: dict, leg_after: dict, metrics_before: dict, metrics_after: dict) -> str:
        # if leg_before == leg_after:
        #     return ""
            
        try:
            prompt = f"""Leg before: {leg_before}
Leg after: {leg_after}
Metrics before: {metrics_before.get("portfolio_greeks", {})}
Metrics after: {metrics_after.get("portfolio_greeks", {})}

One factual sentence about how this leg change affected the metrics."""

            messages = [
                {"role": "system", "content": COPILOT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]
            
            response = self.client.chat_completion(
                messages=messages,
                max_tokens=80,
                temperature=0.1
            )
            
            text = response.choices[0].message.content.strip()
            return "" if text in ('""', "''", "") else text
            
        except Exception as e:
            logger.warning(f"HuggingFace API failed for copilot hint: {e}. Cascading fallback to mock engine.")
            from ai.mock_provider import MockProvider
            return MockProvider().copilot_leg_hint(leg_before, leg_after, metrics_before, metrics_after)