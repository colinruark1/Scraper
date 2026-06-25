"""Google Places source — uses the official Places API (New).

Flow per area: Text Search ("property management" / "apartments" in <area>)
-> for each result, Place Details to pull reviews. This is the supported,
ToS-safe path: no HTML scraping, no bot-blocking to fight.

Docs: https://developers.google.com/maps/documentation/places/web-service/overview
"""
from __future__ import annotations

import logging
import os

import requests

from ..models import Firm, Review
from .base import Source

log = logging.getLogger(__name__)

TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
DETAILS_URL = "https://places.googleapis.com/v1/places/{place_id}"

# Queries aimed at firms that manage/lease multi-bedroom apartments.
QUERIES = [
    "apartment property management company",
    "apartment rentals 2 bedroom",
    "residential property management",
]


class GooglePlacesSource(Source):
    name = "google"

    def __init__(self, api_key: str | None = None, max_per_query: int = 20):
        self.api_key = api_key or os.getenv("GOOGLE_PLACES_API_KEY", "")
        self.max_per_query = max_per_query

    def available(self) -> bool:
        return bool(self.api_key)

    def search(self, area: str) -> list[Firm]:
        if not self.available():
            log.warning("Google Places: no API key, skipping.")
            return []
        firms: dict[str, Firm] = {}
        for query in QUERIES:
            try:
                self._run_query(f"{query} in {area}", firms)
            except requests.RequestException as e:
                log.warning("Google Places query failed (%s): %s", query, e)
        return list(firms.values())

    def _run_query(self, text_query: str, firms: dict[str, Firm]) -> None:
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": (
                "places.id,places.displayName,places.formattedAddress,"
                "places.rating,places.userRatingCount,places.websiteUri,"
                "places.nationalPhoneNumber,places.types"
            ),
        }
        body = {"textQuery": text_query, "maxResultCount": self.max_per_query}
        resp = requests.post(TEXT_SEARCH_URL, headers=headers, json=body, timeout=30)
        resp.raise_for_status()
        for place in resp.json().get("places", []):
            pid = place.get("id")
            if not pid or pid in firms:
                continue
            firm = Firm(
                name=place.get("displayName", {}).get("text", "Unknown"),
                source="google",
                source_id=pid,
                address=place.get("formattedAddress"),
                phone=place.get("nationalPhoneNumber"),
                website=place.get("websiteUri"),
                rating=place.get("rating"),
                review_count=place.get("userRatingCount", 0) or 0,
                categories=place.get("types", []),
            )
            self._enrich_reviews(pid, firm)
            firms[pid] = firm

    def _enrich_reviews(self, place_id: str, firm: Firm) -> None:
        headers = {
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "reviews",
        }
        try:
            resp = requests.get(
                DETAILS_URL.format(place_id=place_id), headers=headers, timeout=30
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            log.debug("Google details failed for %s: %s", place_id, e)
            return
        reviews = resp.json().get("reviews", []) or []
        times = []
        for r in reviews:
            txt = (r.get("text") or {}).get("text", "")
            when = r.get("publishTime")
            if when:
                times.append(when)
            firm.reviews.append(Review(text=txt, rating=r.get("rating"), time=when))
        if times:
            firm.earliest_review = min(times)
