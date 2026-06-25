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
