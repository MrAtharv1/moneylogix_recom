# """
# engine — Lifecycle engine for MoneyLogix Strategy Builder.

# This package is the orchestration layer that sits between the raw quant/
# math modules and the FastAPI endpoints. It answers four questions about
# an options strategy over its lifetime:

#   1. What are its metrics right now?      -> strategy_builder
#   2. Does the market still fit its thesis? -> assumption_checker
#   3. What's changed since entry?           -> health_monitor
#   4. What if I adjusted it?                 -> adjustment_simulator
#   5. (persistence for #3)                   -> snapshot

# Re-exporting the main entry point of each submodule here means callers
# (FastAPI route handlers, the WebSocket handler, tests) can write:

#     from engine import build_strategy_metrics, check_assumptions

# instead of reaching into each submodule individually:

#     from engine.strategy_builder import build_strategy_metrics
#     from engine.assumption_checker import check_assumptions

# Both import styles keep working — this file only adds the shorter one,
# it doesn't remove the direct submodule path. Internal helper functions
# (the underscore-prefixed ones, like _enrich_leg_with_iv) are deliberately
# NOT re-exported here: they're implementation details shared between
# strategy_builder and adjustment_simulator, not part of the package's
# public contract, so callers should keep importing those directly from
# strategy_builder if they ever need them (as adjustment_simulator itself
# does).
# """

# from engine.strategy_builder import build_strategy_metrics
# from engine.assumption_checker import check_assumptions, STRATEGY_ASSUMPTIONS
# from engine.health_monitor import (
#     compute_health_diff,
#     should_trigger_explanation,
#     CHANGE_THRESHOLDS,
# )
# from engine.adjustment_simulator import simulate_adjustment
# from engine.snapshot import (
#     create_strategy_snapshot,
#     get_entry_state,
#     log_health_event,
#     get_health_history,
# )

# __all__ = [
#     "build_strategy_metrics",
#     "check_assumptions",
#     "STRATEGY_ASSUMPTIONS",
#     "compute_health_diff",
#     "should_trigger_explanation",
#     "CHANGE_THRESHOLDS",
#     "simulate_adjustment",
#     "create_strategy_snapshot",
#     "get_entry_state",
#     "log_health_event",
#     "get_health_history",
# ]