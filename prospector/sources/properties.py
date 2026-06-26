"""Property/listing source — ToS-safe ingest of the data the scraping guide
describes (price, beds/baths, sqft, DOM, price history, rent).

The guide recommends Zillow / Realtor.com / Redfin, all of which prohibit
scraping, and points licensed pros at MLS/RETS APIs as the authoritative
alternative. This tool follows that: it ingests listing data you obtain
legitimately (an MLS/RETS export, an official partner/API feed, a licensed data
provider, or your own records) from a CSV, then does the valuable part —
market analysis and investment scoring — on top.

Expected CSV columns (header row, case-insensitive; extras ignored):
    listing_id, address, city, state, zip, price, bedrooms, bathrooms, sqft,
    days_on_market, monthly_rent, property_type, listing_url, owner_firm,
    price_history

`price_history` is optional, formatted as semicolon-separated date:price pairs
oldest-first, e.g.  2024-01-15:329000;2024-04-02:309000;2024-06-01:299000

Drop the file at data/properties.csv (or set PROPERTIES_CSV).
"""
from __future__ import annotations

import csv
import logging
import os

from ..models import Property

log = logging.getLogger(__name__)

DEFAULT_PATH = "data/properties.csv"


def _f(val: str):
    val = (val or "").strip().replace(",", "").replace("$", "")
    if not val:
        return None
    try:
        return float(val)
    except ValueError:
        return None


def _parse_history(raw: str) -> list[tuple]:
    out = []
    for chunk in (raw or "").split(";"):
        chunk = chunk.strip()
        if not chunk or ":" not in chunk:
            continue
        date, _, price = chunk.rpartition(":")
        p = _f(price)
        if p is not None:
            out.append((date.strip(), p))
    return out


def load_properties(path: str | None = None) -> list[Property]:
    path = path or os.getenv("PROPERTIES_CSV", DEFAULT_PATH)
    if not os.path.exists(path):
        log.warning("No properties CSV at %s — see data/properties.sample.csv", path)
        return []

    props: list[Property] = []
    try:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            cols = {c.lower(): c for c in (reader.fieldnames or [])}
            g = lambda row, k: (row.get(cols.get(k, ""), "") or "").strip()
            for i, row in enumerate(reader):
                addr = g(row, "address")
                lid = g(row, "listing_id") or addr or f"row-{i}"
                p = Property(
                    listing_id=lid,
                    source="properties_csv",
                    address=addr or None,
                    city=g(row, "city") or None,
                    state=g(row, "state") or None,
                    zip=g(row, "zip") or None,
                    price=_f(g(row, "price")),
                    bedrooms=_f(g(row, "bedrooms")),
                    bathrooms=_f(g(row, "bathrooms")),
                    sqft=_f(g(row, "sqft")),
                    days_on_market=int(_f(g(row, "days_on_market")) or 0) or None,
                    monthly_rent=_f(g(row, "monthly_rent")),
                    property_type=g(row, "property_type") or None,
                    listing_url=g(row, "listing_url") or None,
                    owner_firm=g(row, "owner_firm") or None,
                    price_history=_parse_history(g(row, "price_history")),
                )
                p.compute_basics()
                props.append(p)
    except (OSError, csv.Error) as e:
        log.warning("Properties CSV read failed: %s", e)
    return props
