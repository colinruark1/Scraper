"""Investment analysis — turn a property + its area stats into investment
metrics and a 0-100 opportunity score that flags high-value targets.

Metrics (from the scraping guide's "Investment Information" section):
  * cap rate / gross yield = (annual rent / price) * 100
  * value vs market       = how far below area median $/sqft this listing sits
  * price drop            = discount from the original list price (motivation)
  * DOM leverage          = how stale vs the area (negotiation room)

The opportunity score rewards: undervalued + high yield + motivated seller +
serves 2-3BR. Tune WEIGHTS to your buy box.
"""
from __future__ import annotations

import math

from .models import Property, MarketStats

WEIGHTS = {
    "value_vs_market": 0.30,   # buying below comparable $/sqft
    "yield": 0.30,             # rental income vs price
    "motivation": 0.20,        # price drops + days on market (negotiation room)
    "bedroom_focus": 0.20,     # matches your 2-3BR business
}

# Operating-expense ratio used to turn gross yield into a rough NET cap rate.
EXPENSE_RATIO = 0.40


def _norm(value: float, soft_cap: float) -> float:
    if value <= 0:
        return 0.0
    return 1.0 - math.exp(-value / soft_cap)


def score_property(p: Property, market: MarketStats | None) -> Property:
    # --- cap rate / yield -------------------------------------------------
    if p.monthly_rent and p.price:
        p.gross_yield = round(p.monthly_rent * 12 / p.price * 100, 2)
        # Net cap rate ~ gross yield after operating expenses.
        p.cap_rate = round(p.gross_yield * (1 - EXPENSE_RATIO), 2)
    yield_component = _norm(p.gross_yield or 0, soft_cap=8)  # ~8% gross -> strong

    # --- value vs market ($/sqft below area median is a deal) -------------
    value_component = 0.0
    if market and market.median_ppsf and p.price_per_sqft:
        p.value_vs_market = round(
            100 * (market.median_ppsf - p.price_per_sqft) / market.median_ppsf, 1
        )
        value_component = _norm(max(0.0, p.value_vs_market), soft_cap=15)

    # --- seller motivation: price drop + stale listing -------------------
    drop_signal = _norm(max(0.0, p.price_drop_pct or 0), soft_cap=8)
    dom_signal = 0.0
    if market and market.median_dom and p.days_on_market:
        excess = p.days_on_market - market.median_dom
        dom_signal = _norm(max(0.0, excess), soft_cap=45)
    motivation_component = 0.6 * drop_signal + 0.4 * dom_signal

    bedroom_component = 1.0 if p.bedroom_match else 0.0

    breakdown = {
        "value_vs_market": round(value_component, 3),
        "yield": round(yield_component, 3),
        "motivation": round(motivation_component, 3),
        "bedroom_focus": round(bedroom_component, 3),
    }
    total = sum(WEIGHTS[k] * breakdown[k] for k in WEIGHTS)
    p.score_breakdown = breakdown
    p.opportunity_score = round(100 * total, 1)
    return p


def score_properties(properties: list[Property], stats: dict[str, MarketStats]):
    from .market import _area_key

    for p in properties:
        score_property(p, stats.get(_area_key(p)))
    properties.sort(key=lambda x: x.opportunity_score, reverse=True)
    return properties
