import logging
from ai.base_provider import get_provider

logger = logging.getLogger(__name__)

async def explain_health_change(diff: dict, strategy_type: str, entry_state: dict, current_state: dict) -> str:
    if not diff.get("has_changes"):
        return ""
    try:
        provider = get_provider()
        result = await provider.explain_lifecycle_change(diff, strategy_type, entry_state, current_state)
        return result if isinstance(result, str) else ""
    except Exception as e:
        logger.error(f"explainer.explain_health_change failed: {e}")
        return ""