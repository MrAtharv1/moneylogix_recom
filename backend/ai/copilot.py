import logging
from ai.base_provider import get_provider

logger = logging.getLogger(__name__)

async def get_leg_hint(leg_before: dict, leg_after: dict, metrics_before: dict, metrics_after: dict) -> str:
    if leg_before == leg_after:
        return ""
    try:
        provider = get_provider()
        result = await provider.copilot_leg_hint(leg_before, leg_after, metrics_before, metrics_after)
        return result if isinstance(result, str) else ""
    except Exception as e:
        logger.error(f"copilot.get_leg_hint failed: {e}")
        return ""