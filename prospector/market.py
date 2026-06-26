"""Market analysis — aggregate a set of properties into per-area stats.

Implements the "Market Analysis" section of the scraping guide: median price,
price per sqft, days-on-market, plus rental yield and average price drop. We
aggregate by ZIP (the guide's unit for comps/yield), falling back to city.
These stats also feed the investment scorer's market-relative signals.
"""
from __future__ import annotations

from statistics import median

from .models import Property, MarketStats


def _area_key(p: Property) -> str:
    return (p.zip or p.city or p.state or "unknown").strip()


def _median(values: list[float]) -> float | None:
    vals = [v for v in values if v is not None]
    return round(median(vals), 2) if vals else None


def build_market_stats(properties: list[Property]) -> dict[str, MarketStats]:
    """Return {area_key: MarketStats}. Yields require monthly_rent + price."""
    groups: dict[str, list[Property]] = {}
    for p in properties:
        groups.setdefault(_area_key(p), []).append(p)

    stats: dict[str, MarketStats] = {}
    for area, props in groups.items():
        yields = [
            (p.monthly_rent * 12 / p.price * 100)
            for p in props
            if p.monthly_rent and p.price
        ]
        drops = [p.price_drop_pct for p in props if p.price_drop_pct is not None]
        stats[area] = MarketStats(
            area=area,
            n_listings=len(props),
            median_price=_median([p.price for p in props]),
            median_ppsf=_median([p.price_per_sqft for p in props]),
            median_dom=_median([p.days_on_market for p in props]),
            median_yield=round(median(yields), 2) if yields else None,
            avg_price_drop=round(sum(drops) / len(drops), 1) if drops else None,
        )
    return stats
