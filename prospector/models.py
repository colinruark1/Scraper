"""Core data model for a prospective acquisition target (a real estate firm)."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Review:
    text: str
    rating: Optional[float] = None
    time: Optional[str] = None  # ISO date string when available


@dataclass
class Firm:
    """One firm gathered from a source. Sources fill what they can; the rest
    stays None/empty and the scorer handles missing data gracefully."""

    name: str
    source: str                       # "google", "yelp", "listings"
    source_id: str                    # stable id within that source (for de-dup)
    address: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    rating: Optional[float] = None    # average star rating
    review_count: int = 0
    earliest_review: Optional[str] = None  # ISO date — longevity proxy
    categories: list[str] = field(default_factory=list)
    reviews: list[Review] = field(default_factory=list)

    # Filled in by the scorer:
    loyalty_score: float = 0.0
    bedroom_match: bool = False
    score_breakdown: dict = field(default_factory=dict)

    def merge(self, other: "Firm") -> None:
        """Fold another source's record for the same firm into this one."""
        self.review_count = max(self.review_count, other.review_count)
        self.reviews.extend(other.reviews)
        self.categories = sorted(set(self.categories) | set(other.categories))
        for attr in ("address", "phone", "website", "rating", "earliest_review"):
            if getattr(self, attr) in (None, "", 0) and getattr(other, attr):
                setattr(self, attr, getattr(other, attr))
        self.source = ",".join(sorted(set(self.source.split(",") + [other.source])))

    def to_dict(self) -> dict:
        d = asdict(self)
        d["reviews"] = [asdict(r) for r in self.reviews]
        return d


@dataclass
class Property:
    """A single listing / asset, modeled on the fields the scraping guide
    lists (price, beds/baths, sqft, $/sqft, DOM, price history, rent...).

    Investment fields (cap_rate, yield, opportunity_score) are computed later
    by the investment module; market-relative fields need area stats too."""

    listing_id: str
    source: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    price: Optional[float] = None
    bedrooms: Optional[float] = None
    bathrooms: Optional[float] = None
    sqft: Optional[float] = None
    days_on_market: Optional[int] = None
    monthly_rent: Optional[float] = None     # actual or estimated market rent
    property_type: Optional[str] = None
    listing_url: Optional[str] = None
    owner_firm: Optional[str] = None          # links a listing back to a Firm
    # date -> price pairs, oldest first (price history / trend)
    price_history: list[tuple] = field(default_factory=list)

    # ---- computed (investment.py) ----
    price_per_sqft: Optional[float] = None
    cap_rate: Optional[float] = None          # (annual rent / price) * 100
    gross_yield: Optional[float] = None       # same basis; kept explicit
    price_drop_pct: Optional[float] = None     # discount vs first listed price
    value_vs_market: Optional[float] = None    # % below(+)/above(-) area $/sqft
    opportunity_score: float = 0.0
    bedroom_match: bool = False
    score_breakdown: dict = field(default_factory=dict)

    def compute_basics(self) -> None:
        if self.price and self.sqft:
            self.price_per_sqft = round(self.price / self.sqft, 2)
        try:
            self.bedroom_match = self.bedrooms is not None and 2 <= float(self.bedrooms) <= 3
        except (TypeError, ValueError):
            self.bedroom_match = False
        if self.price_history:
            first = self.price_history[0][1]
            if first and self.price and first > 0:
                self.price_drop_pct = round(100 * (first - self.price) / first, 1)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MarketStats:
    """Aggregated view of one area (a zip, or a named market)."""

    area: str
    n_listings: int = 0
    median_price: Optional[float] = None
    median_ppsf: Optional[float] = None        # median price per sqft
    median_dom: Optional[float] = None          # median days on market
    median_yield: Optional[float] = None        # median gross rental yield
    avg_price_drop: Optional[float] = None      # avg discount across listings

    def to_dict(self) -> dict:
        return asdict(self)
