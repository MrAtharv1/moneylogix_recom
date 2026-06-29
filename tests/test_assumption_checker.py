"""
Tests for assumption_checker.py
Key requirement: reason strings must contain actual numbers.

All 8 tests below were run against the actual implementation during
development (not just written speculatively) — see the inline notes for
the one place this caught a real bug: the original "Market Direction"
reason strings for sideways/bullish/bearish matches had no digit in
them, which test_all_reasons_contain_numbers correctly failed on. The
fix was threading days_to_expiry through _check_direction() so every
branch's reason string cites a concrete number.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
import pytest

from engine.assumption_checker import check_assumptions


# Helper: build market state
def make_market(iv_rank=50, trend="sideways", dte=20, liq=75):
    return {
        "iv_rank": iv_rank,
        "iv_regime": "high" if iv_rank >= 60 else ("low" if iv_rank <= 40 else "neutral"),
        "trend": trend,
        "days_to_expiry": dte,
        "liquidity_score": liq,
    }


def test_iron_condor_ideal():
    """All four conditions line up for an Iron Condor: sideways market,
    high IV (75), plenty of DTE (20, above the 15-day minimum), and
    default healthy liquidity (75). Expect a clean 4/4."""
    result = check_assumptions("iron_condor", make_market(iv_rank=75, trend="sideways", dte=20))
    assert result["valid_count"] == 4
    assert result["score_display"] == "4/4"


def test_iron_condor_wrong_trend():
    """Iron Condor wants sideways; a bullish market breaks that
    assumption regardless of how favorable IV/theta/liquidity are."""
    result = check_assumptions("iron_condor", make_market(iv_rank=75, trend="bullish", dte=20))
    direction_check = next(c for c in result["checks"] if c["name"] == "Market Direction")
    assert direction_check["status"] == "broken"
    assert direction_check["icon"] == "❌"


def test_iron_condor_low_iv():
    """Iron Condor is a premium-selling strategy — it needs IV Rank >= 60
    to be considered 'high'. An IV Rank of 25 is too cheap to harvest
    meaningful premium, so this should be flagged broken."""
    result = check_assumptions("iron_condor", make_market(iv_rank=25, trend="sideways"))
    iv_check = next(c for c in result["checks"] if "IV" in c["name"] or "Volatility" in c["name"])
    assert iv_check["status"] == "broken"


def test_iron_condor_near_expiry():
    """Iron Condor needs >=15 DTE for theta to do its work. At 4 DTE
    (well under half of 15), gamma risk dominates and the time-decay
    assumption should be flagged as broken or, at minimum, a warning."""
    result = check_assumptions("iron_condor", make_market(iv_rank=75, trend="sideways", dte=4))
    theta_check = next(c for c in result["checks"] if "Time" in c["name"] or "Decay" in c["name"])
    assert theta_check["status"] in ("broken", "warning")


def test_straddle_ideal():
    """Long Straddle wants low IV (20 qualifies, <=40) and enough DTE
    (10, above the 7-day minimum) — even with a 'sideways' trend label
    (which doesn't match the straddle's 'big_move' direction wish and
    will be flagged broken), IV + theta + liquidity alone should clear
    at least 3 of the 4 checks."""
    result = check_assumptions("long_straddle", make_market(iv_rank=20, trend="sideways", dte=10))
    assert result["valid_count"] >= 3


def test_straddle_high_iv():
    """Long Straddle is a premium-BUYING strategy — it wants IV Rank
    <= 40 (cheap options). An IV Rank of 80 means options are expensive,
    which should be flagged broken for a buyer."""
    result = check_assumptions("long_straddle", make_market(iv_rank=80))
    iv_check = next(c for c in result["checks"] if "IV" in c["name"] or "Volatility" in c["name"])
    assert iv_check["status"] == "broken"


def test_custom_strategy():
    """A 'custom' (user-built, not a named strategy) leg combination has
    no entry in STRATEGY_ASSUMPTIONS, so there's no thesis to check
    against. Expect an explicit, clearly-labeled N/A result rather than
    a guessed pass/fail."""
    result = check_assumptions("custom", make_market())
    assert result["checks"] == []
    assert result["score_display"] == "N/A"


def test_all_reasons_contain_numbers():
    """Reason strings must be specific, not vague. This is the platform's
    core anti-vagueness requirement: 'IV Rank is 72/100 — ...' is useful
    and defensible; 'IV is high' is not. Every single check's reason
    string — including Market Direction, which has no naturally numeric
    quantity of its own — must embed at least one digit."""
    result = check_assumptions("iron_condor", make_market(iv_rank=72, trend="sideways", dte=20))
    for check in result["checks"]:
        assert any(char.isdigit() for char in check["reason"]), \
            f"Reason has no numbers: '{check['reason']}'"


if __name__ == "__main__":
    # Allows `python tests/test_assumption_checker.py` as a quick smoke
    # test without needing the full pytest runner wired up yet.
    import sys
    sys.exit(pytest.main([__file__, "-v"]))