#!/usr/bin/env python3
"""CLI entry point. Runs the scrape+score pipeline and writes prospects.db,
plus a CSV you can open in Excel.

Usage:
    python run.py                       # use SEARCH_AREAS from .env
    python run.py "Harrisburg PA" "Erie PA"
    python run.py --csv prospects.csv
"""
from __future__ import annotations

import argparse
import csv
import logging
import os
import sys

from dotenv import load_dotenv

from prospector.pipeline import run


def main() -> int:
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="PA real-estate firm prospector")
    parser.add_argument("areas", nargs="*", help="Areas to search, e.g. 'Erie PA'")
    parser.add_argument("--csv", default="prospects.csv", help="CSV output path")
    parser.add_argument("--db", default="prospects.db", help="SQLite output path")
    args = parser.parse_args()

    areas = args.areas or [
        a.strip()
        for a in os.getenv("SEARCH_AREAS", os.getenv("SEARCH_LOCATION", "Pennsylvania")).split(",")
        if a.strip()
    ]
    print(f"Searching {len(areas)} area(s): {', '.join(areas)}\n")

    firms = run(areas, db_path=args.db)
    if not firms:
        print(
            "\nNo firms found. Most likely no source is configured yet.\n"
            "Copy .env.example to .env and add a Google Places and/or Yelp key,\n"
            "or drop a data/listings.csv file. Then re-run."
        )
        return 1

    _write_csv(firms, args.csv)
    print(f"\nTop prospects (full ranked list in {args.csv} and the dashboard):\n")
    for i, f in enumerate(firms[:10], 1):
        flag = " [2-3BR]" if f.bedroom_match else ""
        print(f"{i:2}. {f.loyalty_score:5.1f}  {f.name}{flag}")
    print("\nRun the dashboard with:  python app.py")
    return 0


def _write_csv(firms, path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "rank", "loyalty_score", "name", "2-3BR_match", "rating",
            "review_count", "address", "phone", "website", "sources",
            "reviews_ratings", "tenant_language", "longevity", "bedroom_focus",
        ])
        for i, fm in enumerate(firms, 1):
            b = fm.score_breakdown
            w.writerow([
                i, fm.loyalty_score, fm.name, "yes" if fm.bedroom_match else "no",
                fm.rating or "", fm.review_count, fm.address or "", fm.phone or "",
                fm.website or "", fm.source,
                b.get("reviews_ratings", ""), b.get("tenant_language", ""),
                b.get("longevity", ""), b.get("bedroom_focus", ""),
            ])


if __name__ == "__main__":
    sys.exit(main())
