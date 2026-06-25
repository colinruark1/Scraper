"""Listings source — the ToS-safe answer to "what about Zillow / Apartments.com?"

Both of those sites PROHIBIT scraping in their Terms of Service and actively
block bots. Scraping them puts your firm at real legal and reputational risk,
so this tool does NOT do that. Instead it ingests listing/bedroom data you can
obtain legitimately and merges it in to sharpen the 2-3BR signal:

  * a CSV you export from a service you license, an MLS/IDX feed, a data
    broker, or your own internal records;
  * Apartments.com / Zillow both offer official partner data feeds and APIs for
    business use — use those and dump the result to CSV.

Expected CSV columns (header row, case-insensitive; extras ignored):
    name, address, phone, website, bedrooms, source_id

Drop the file at data/listings.csv (or pass a path) and it gets folded into
the firm pool, with bedroom counts feeding the bedroom-focus score.
"""
from __future__ import annotations

import csv
import logging
import os

from ..models import Firm, Review
from .base import Source

log = logging.getLogger(__name__)

DEFAULT_PATH = "data/listings.csv"


class ListingsSource(Source):
    name = "listings"

    def __init__(self, path: str | None = None):
        self.path = path or os.getenv("LISTINGS_CSV", DEFAULT_PATH)

    def available(self) -> bool:
        return os.path.exists(self.path)

    def search(self, area: str) -> list[Firm]:
        # CSV is area-agnostic; we load it once (on the first area) and rely on
        # the pipeline's de-dup to avoid re-adding it for later areas.
        if not self.available():
            return []
        firms = []
        try:
            with open(self.path, newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                cols = {c.lower(): c for c in (reader.fieldnames or [])}
                for row in reader:
                    g = lambda k: (row.get(cols.get(k, ""), "") or "").strip()
                    name = g("name")
                    if not name:
                        continue
                    bedrooms = g("bedrooms")
                    # Encode bedroom count as a synthetic review so the existing
                    # bedroom-focus scorer picks it up uniformly.
                    note = f"{bedrooms} bedroom unit" if bedrooms else ""
                    firms.append(
                        Firm(
                            name=name,
                            source="listings",
                            source_id=g("source_id") or name.lower(),
                            address=g("address") or None,
                            phone=g("phone") or None,
                            website=g("website") or None,
                            categories=["listing"],
                            reviews=[Review(text=note)] if note else [],
                        )
                    )
        except (OSError, csv.Error) as e:
            log.warning("Listings CSV read failed: %s", e)
        return firms
