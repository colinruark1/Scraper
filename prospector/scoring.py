"""Turn raw firm data into a 0-100 'loyal & passionate' score.

There is no field anywhere that literally says "loyal" or "passionate." So we
build a composite from measurable proxies, each normalized to 0-1 and then
weighted. Tune the WEIGHTS to match what you care about most.
"""
from __future__ import annotations

import math
import re
from datetime import datetime, timezone

from .models import Firm

# ---- weights (must roughly sum to 1.0) ------------------------------------
WEIGHTS = {
    "reviews_ratings": 0.35,   # engagement + satisfaction
    "tenant_language": 0.30,   # loyalty/passion language in review text
    "longevity": 0.20,         # how long they've been operating (proxy)
    "bedroom_focus": 0.15,     # do they actually serve 2-3BR / family units
}

# Phrases that signal a loyal, emotionally-invested tenant base.
LOYALTY_PHRASES = [
    "years", "renewed", "renew", "renewing", "long term", "long-term",
    "feels like home", "felt like home", "like family", "second home",
    "stayed for", "been here", "lived here", "highly recommend",
    "go above and beyond", "went above and beyond", "responsive", "caring",
    "passionate", "always there", "never had a problem", "wouldn't leave",
    "would not leave", "best landlord", "best management", "loyal", "love living",
]

# Signals that the firm serves 2-3 bedroom / family-sized units.
BEDROOM_PHRASES = [
    "2 bedroom", "2-bedroom", "two bedroom", "2 br", "2br",
    "3 bedroom", "3-bedroom", "three bedroom", "3 br", "3br",
    "multi-bedroom", "family", "townhome", "townhouse", "spacious",
]


def _norm(value: float, soft_cap: float) -> float:
    """Diminishing-returns normalizer: 0 -> 0, soft_cap -> ~0.63, grows to 1."""
    if value <= 0:
        return 0.0
    return 1.0 - math.exp(-value / soft_cap)


def _all_text(firm: Firm) -> str:
    parts = [firm.name, " ".join(firm.categories)]
    parts += [r.text for r in firm.reviews if r.text]
    return " ".join(parts).lower()


def _phrase_hits(text: str, phrases: list[str]) -> int:
    return sum(len(re.findall(re.escape(p), text)) for p in phrases)


def _years_since(iso_date: str | None) -> float:
    if not iso_date:
        return 0.0
    try:
        dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max(0.0, (datetime.now(timezone.utc) - dt).days / 365.25)


def score_firm(firm: Firm) -> Firm:
    text = _all_text(firm)

    # 1. reviews + ratings: blend satisfaction (rating/5) with volume.
    rating_component = (firm.rating or 0) / 5.0
    volume_component = _norm(firm.review_count, soft_cap=40)
    reviews_ratings = 0.6 * rating_component + 0.4 * volume_component

    # 2. tenant-language: loyalty phrases per review, normalized.
    n_reviews = max(1, len(firm.reviews))
    loyalty_density = _phrase_hits(text, LOYALTY_PHRASES) / n_reviews
    tenant_language = _norm(loyalty_density, soft_cap=1.5)

    # 3. longevity: years since earliest known review (proxy for tenure).
    longevity = _norm(_years_since(firm.earliest_review), soft_cap=6)

    # 4. bedroom focus: do they mention 2-3BR / family units at all?
    bedroom_hits = _phrase_hits(text, BEDROOM_PHRASES)
    firm.bedroom_match = bedroom_hits > 0
    bedroom_focus = _norm(bedroom_hits, soft_cap=3)

    breakdown = {
        "reviews_ratings": round(reviews_ratings, 3),
        "tenant_language": round(tenant_language, 3),
        "longevity": round(longevity, 3),
        "bedroom_focus": round(bedroom_focus, 3),
    }
    total = sum(WEIGHTS[k] * breakdown[k] for k in WEIGHTS)

    firm.score_breakdown = breakdown
    firm.loyalty_score = round(100 * total, 1)
    return firm
