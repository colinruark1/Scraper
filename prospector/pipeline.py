"""Orchestration: gather firms from every available source across every area,
de-duplicate, score, and persist."""
from __future__ import annotations

import logging
import re

from .models import Firm
from .scoring import score_firm
from .sources import GooglePlacesSource, YelpSource, ListingsSource
from .storage import save_firms

log = logging.getLogger(__name__)


def _dedup_key(firm: Firm) -> str:
    """Same firm across sources -> same key. Normalize name + first address
    token (street number) so 'ABC Realty' on Google and Yelp collapse."""
    name = re.sub(r"[^a-z0-9]+", "", firm.name.lower())
    street = ""
    if firm.address:
        m = re.match(r"\s*(\d+)", firm.address)
        street = m.group(1) if m else ""
    return f"{name}|{street}"


def collect(areas: list[str], sources=None) -> list[Firm]:
    if sources is None:
        sources = [GooglePlacesSource(), YelpSource(), ListingsSource()]

    active = [s for s in sources if s.available()]
    if not active:
        log.warning(
            "No sources are configured. Add API keys to .env (Google/Yelp) "
            "or a data/listings.csv file. See .env.example."
        )
    else:
        log.info("Active sources: %s", ", ".join(s.name for s in active))

    pool: dict[str, Firm] = {}
    listings_loaded = False
    for area in areas:
        for src in active:
            # The listings CSV is area-agnostic; only load it once.
            if src.name == "listings":
                if listings_loaded:
                    continue
                listings_loaded = True
            try:
                found = src.search(area)
            except Exception as e:  # noqa: BLE001 - never let one source kill the run
                log.warning("%s failed on %s: %s", src.name, area, e)
                continue
            log.info("%-9s %-22s -> %d firms", src.name, area, len(found))
            for firm in found:
                key = _dedup_key(firm)
                if key in pool:
                    pool[key].merge(firm)
                else:
                    pool[key] = firm
    return list(pool.values())


def run(areas: list[str], db_path: str = "prospects.db") -> list[Firm]:
    firms = collect(areas)
    for firm in firms:
        score_firm(firm)
    firms.sort(key=lambda f: f.loyalty_score, reverse=True)
    save_firms(firms, db_path)
    log.info("Scored and saved %d firms.", len(firms))
    return firms
