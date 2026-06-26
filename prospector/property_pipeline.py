"""Property pipeline: load listings -> build market stats -> score
opportunities -> persist. The counterpart to pipeline.py (which handles firms)."""
from __future__ import annotations

import logging

from .investment import score_properties
from .market import build_market_stats
from .sources.properties import load_properties
from .storage import save_properties, save_market

log = logging.getLogger(__name__)


def run_properties(csv_path: str | None = None, db_path: str = "prospects.db"):
    props = load_properties(csv_path)
    if not props:
        log.info("No property data loaded — skipping market/investment analysis.")
        return [], {}

    stats = build_market_stats(props)
    score_properties(props, stats)
    save_properties(props, db_path)
    save_market(stats, db_path)
    log.info(
        "Analyzed %d listings across %d market area(s).", len(props), len(stats)
    )
    return props, stats
