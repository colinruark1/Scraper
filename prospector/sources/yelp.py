"""Yelp source — uses the official Yelp Fusion API.

Business Search to find firms, then the Reviews endpoint for sentiment text.
Note: Yelp's free tier returns up to 3 review excerpts per business, which is
enough for the tenant-language signal. ToS-safe, no scraping.

Docs: https://docs.developer.yelp.com/docs/fusion-intro
"""
from __future__ import annotations

import logging
import os

import requests

from ..models import Firm, Review
from .base import Source

log = logging.getLogger(__name__)

SEARCH_URL = "https://api.yelp.com/v3/businesses/search"
REVIEWS_URL = "https://api.yelp.com/v3/businesses/{id}/reviews"

# Yelp categories most likely to hold our targets.
CATEGORIES = "apartments,propertymgmt,realestateagents"


class YelpSource(Source):
    name = "yelp"

    def __init__(self, api_key: str | None = None, limit: int = 25):
        self.api_key = api_key or os.getenv("YELP_API_KEY", "")
        self.limit = limit

    def available(self) -> bool:
        return bool(self.api_key)

    @property
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"}

    def search(self, area: str) -> list[Firm]:
        if not self.available():
            log.warning("Yelp: no API key, skipping.")
            return []
        params = {
            "location": area,
            "categories": CATEGORIES,
            "limit": min(self.limit, 50),
            "sort_by": "review_count",
        }
        try:
            resp = requests.get(
                SEARCH_URL, headers=self._headers, params=params, timeout=30
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            log.warning("Yelp search failed for %s: %s", area, e)
            return []

        firms = []
        for biz in resp.json().get("businesses", []):
            firm = Firm(
                name=biz.get("name", "Unknown"),
                source="yelp",
                source_id=biz.get("id", ""),
                address=", ".join(biz.get("location", {}).get("display_address", [])),
                phone=biz.get("display_phone"),
                website=biz.get("url"),
                rating=biz.get("rating"),
                review_count=biz.get("review_count", 0) or 0,
                categories=[c["title"] for c in biz.get("categories", [])],
            )
            self._enrich_reviews(firm)
            firms.append(firm)
        return firms

    def _enrich_reviews(self, firm: Firm) -> None:
        try:
            resp = requests.get(
                REVIEWS_URL.format(id=firm.source_id),
                headers=self._headers,
                params={"limit": 20, "sort_by": "yelp_sort"},
                timeout=30,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            log.debug("Yelp reviews failed for %s: %s", firm.name, e)
            return
        times = []
        for r in resp.json().get("reviews", []):
            when = r.get("time_created")
            if when:
                times.append(when)
            firm.reviews.append(
                Review(text=r.get("text", ""), rating=r.get("rating"), time=when)
            )
        if times:
            firm.earliest_review = min(times)
